# Licensed under the GNU General Public License, version 2.
# See the file http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

import urllib
import urlparse
import urllib2
import HTMLParser
import os
import sys
import re
import string
import base64
import gzip
import json
from StringIO import StringIO
from cookielib import CookieJar

import xml.dom.minidom as md

from BeautifulSoup import BeautifulSoup as BS

REMOTE_DBG = 0
# append pydev remote debugger
if REMOTE_DBG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    try:
        import pysrc.pydevd as pydevd
    # stdoutToServer and stderrToServer redirect stdout and stderr to eclipse console
        pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
    except ImportError:
        sys.stderr.write("Error: " +
            "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
        sys.exit(1)
        
__plugin__ = 'Dizimag'
__author__ = 'Gokcen Eraslan <gokcen.eraslan@gmail.com>'
__url__ = 'http://code.google.com/p/plugin/'
__date__ = '03-14-2012'
__version__ = '0.6'
__settings__ = xbmcaddon.Addon(id='plugin.video.dizimag')


#SHOWNAMES_URL = "http://i.dizimag.com/cache/d.js" # this does not provide info
                                            # about the language of the tv show

DOMAIN = "http://dizimag.com"
SHOWNAMES_URL = "http://www.dizi-mag.com/cache/d.js"

TURKISHSHOW, ENGLISHSHOW = range(2)

SHOW_URL = "http://www.dizimag.com/%(show)s"
SHOW_THUMBNAIL_URL = "http://i.dizimag.com/dizi/%(show)s.jpg"
SHOW_AVATAR_URL = "http://i.dizimag.com/dizi/%(show)s-avatar.jpg"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:10.0.1)"
" Gecko/20100101 Firefox/10.0.1"

#Recently added episodes
RECENTLY_ADDED_EDISODES_URL = \
                      "http://dizimag.com/servisler.asp?ser=yenie&a=%(pageno)s"

RECENTLY_ADDED_EPISODES_PAGE_MAX = 4

#Backgrounds
#http://dizimag.com/_arkaplan.asp

#Subtitle translation percentage
#http://dizimag.com/_altyazi.asp

WATCH_SHOW_TR_SUB_HD_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-"\
                           "%(episode)s-bolum-720p-izle-dizi.html"

WATCH_SHOW_TR_SUB_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-" \
                        "%(episode)s-bolum-izle-dizi.html"

WATCH_SHOW_ENG_SUB_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-" \
                         "%(episode)s-bolum-subing-izle-dizi.html"

WATCH_SHOW_NO_SUB_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-" \
                        "%(episode)s-bolum-nosub-izle-dizi.html"

# poor man's enum, hehe
# Be careful: Types are in the order of choice
WATCH_TYPE_TR_SUB_HD, WATCH_TYPE_TR_SUB, \
WATCH_TYPE_ENG_SUB, WATCH_TYPE_NO_SUB, = range(4)

SUBTITLE_NONE, SUBTITLE_TURKISH, SUBTITLE_ENGLISH, = range(3)

WATCH_URL = {
              WATCH_TYPE_ENG_SUB:   (WATCH_SHOW_ENG_SUB_URL, SUBTITLE_ENGLISH,
              "Low resolution video with English subtitles"),

              WATCH_TYPE_NO_SUB:    (WATCH_SHOW_NO_SUB_URL, SUBTITLE_NONE,
              "Low resolution video"),

              WATCH_TYPE_TR_SUB_HD: (WATCH_SHOW_TR_SUB_HD_URL,
              SUBTITLE_TURKISH, "720p HD video"),

              WATCH_TYPE_TR_SUB:    (WATCH_SHOW_TR_SUB_URL, SUBTITLE_TURKISH,
              "Low resolution video with Turkish subtitles")
              }

PLUGIN_ID = int(sys.argv[1])

turkish_fanart = os.path.join(__settings__.getAddonInfo('path'),
'resources', 'media', 'turkish-fanart.jpg')

english_fanart = os.path.join(__settings__.getAddonInfo('path'),
'resources', 'media', 'english-fanart.jpg')

playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
player = xbmc.Player(xbmc.PLAYER_CORE_MPLAYER)

cj = CookieJar()
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
opener.addheaders= [('User-Agent', USER_AGENT),('Accept-encoding', 'gzip'),('Referer', 'http://www.dizi-mag.com/')]
urllib2.install_opener(opener)


def decode_base64(alphabet, encoded):
    std_base64chars = \
             "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

    return base64.b64decode(encoded.translate(string.maketrans(alphabet, std_base64chars)))

def get_redirect(lnk):
    ## we should get nasty here since xbmc does not handle redirects
    req=urllib2.Request(lnk)
    req.add_header('Range','bytes=0-1')
    try:
        f=urllib2.urlopen(req)
    except urllib2.HTTPError, error:
        print error.read()
    return f.geturl()

class RedirectHandler(urllib2.HTTPRedirectHandler):     
    def http_error_301(self, req, fp, code, msg, headers):  
        result = urllib2.HTTPRedirectHandler.http_error_301( 
            self, req, fp, code, msg, headers)              
        result.status = code                                 
        return result                                       

    def http_error_302(self, req, fp, code, msg, headers):   
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)              
        result.status = code                                
        return result      

def open_url(url):
    content = urllib2.urlopen(url)
    if content.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(content.read())
        f = gzip.GzipFile(fileobj=buf)
        data = f.read()
    else:
        data = content.read()
    content.close()
    return data


def get_show_names():

    listpage = open_url(SHOWNAMES_URL)

    if not listpage:
        xbmcgui.Dialog().ok("Error", 'Page not found (%s)...' % SHOWNAMES_URL)
        return

    shownames=[]
    for data in re.findall("\[(.*?)\]",listpage):
        for row in re.findall("{.*?}",data):
            scrapes=re.findall("d:\s\"(.*?)\",\ss:\s\"(.*?)\"",row)
            shownames.append((scrapes[0][1],ENGLISHSHOW,scrapes[0][0]))

    return shownames


def get_show_thumbnail_url(showcode):
    return SHOW_THUMBNAIL_URL % {'show': showcode}


def get_show_avatar_url(showcode):
    return SHOW_AVATAR_URL % {'show': showcode}


def get_show_season_info(showcode):
    showpage = open_url(SHOW_URL % {'show': showcode})
    if showpage:
        return parse_html_get_season_info(showpage)


def get_recently_added_info():
    result = []
    for i in range(1, int(RECENTLY_ADDED_EPISODES_PAGE_MAX) + 1):
        result.extend(
        parse_recently_added_page(
        open_url(RECENTLY_ADDED_EDISODES_URL % {"pageno": str(i)})))

    return result


def get_show_episode_info(showcode,season):
    opener.addheaders.append(("X-Requested-With","XMLHttpRequest"))
    showpage = open_url(DOMAIN+"/service/?ser=sezon&d="+showcode[1:]+"&s="+season)
    opener.addheaders.pop()
    if not showpage:
        xbmcgui.Dialog().ok("Error", 'Page not found (%s)...'
                                            % SHOW_URL % {'show': showcode})
        return
    episodes = parse_html_show_table("<html><body>"+showpage+"</body></html>")
    return sorted(episodes,
    cmp=lambda x, y:
    cmp(int(x[0]) * 1000 + int(x[1]), int(y[0]) * 1000 + int(y[1])),reverse=True)


def parse_html_get_season_info(tree):
    tree = BS(tree)
    divs = tree.body.findAll(lambda x:
           x.name == "a" and "dizi_list" in x.get("class", "").split())

    return [HTMLParser.HTMLParser().unescape(x.text) for x in divs]


def parse_html_show_table(tree):
    tree = BS(tree)
    show_elements = tree.body.findAll(lambda x:
                    x.name == "td" and "blmin" in x.get("class", "").split())

    result = []

    for episode in show_elements:
        a_elements = episode.findAll("a")
        img_elements = episode.findAll("img")

        episode_season = episode["class"].split()[1].split("x")[0][1:]
        episode_no = episode["class"].split()[1].split("x")[1]

        if len(a_elements) > 1:
            episode_name = HTMLParser.HTMLParser().unescape(
                           a_elements[1].text.encode("utf-8"))
        else:
            episode_name = u""

        episode_watch_types = []

        for img in img_elements:
            if "tlb_tr" in img.get("class", "").split():
                #yes there is a mistake in dizimag's code tlb_tr <-> tlb_eng
                episode_watch_types.append(str(WATCH_TYPE_ENG_SUB))
            elif "tlb_nosub" in img.get("class", "").split():
                episode_watch_types.append(str(WATCH_TYPE_NO_SUB))
            elif "tlb_hd" in img.get("class", "").split():
                episode_watch_types.append(str(WATCH_TYPE_TR_SUB_HD))
            elif "tlb_eng" in img.get("class", "").split():
                episode_watch_types.append(str(WATCH_TYPE_TR_SUB))

        if not episode_watch_types:
            continue

        result.append([episode_season,
                       episode_no,
                       episode_name,
                       "-".join(episode_watch_types)])

    return result


def parse_recently_added_page(tree):
    tree = BS(tree)
    episodes = tree.findAll('a')
    result = []

    for episode in episodes:
        showre = re.match(r"/(.*?)-([0-9]+?)-sezon-([0-9]+?)-bolum-.*?\.html",
                          episode.get("href", ""))

        if showre and len(showre.groups()) == 3:
            showcode = showre.group(1)
            season = showre.group(2)
            no = showre.group(3)
            showname = episode.span.h1.text.encode("utf-8")
            #season = episode.span.contents[1].split()[0][:-1]
            #no = episode.span.contents[1].split()[2][:-1]
            result.append((showcode, showname, season, no))
        else:
            continue

    return result


def get_show_video_urls(showcode,
                        season,
                        episode,
                        watch_type=WATCH_TYPE_TR_SUB_HD):

    def scrape_facebook_vid(showpage,t):
        alphabet = re.search(r'670x3=\["(.*?)"\]', showpage) 
        
        if alphabet:
            alphabet = alphabet.group(1)

        if not alphabet:
            return

        alphabet=re.findall(r'670x3=\["(.*?)"\]',showpage)[0].replace("x","u00").decode("raw_unicode_escape","ignore").encode("ascii")
        

        encoded_parts = re.findall(r"jQuery\.mp4\.d\('(.*?)'\)", showpage)
        parts = [{"vid":get_redirect(decode_base64(alphabet, x)),"cookies":[]} for x in encoded_parts]

        return parts
    
    def scrape_mailru_vid(showpage,t):
        ru=re.findall('mail/(.*?)/_myvideo/(.*?)\&',showpage)
        if len(ru)==0:
            print "Error : Not a mail.ru video file"
            return []
        else:
            js= json.loads(open_url("http://api.video.mail.ru/videos/mail/"+ru[0][0]+"/_myvideo/"+ru[0][1]+".json"))
        parts=[]
        cookies={}
        for cookie in cj:
            if "mail.ru" in cookie.domain:
                cookies[cookie.name]=cookie.value

        if "hd" in js['videos'].keys() and t==0: parts.append({"vid":js['videos']['hd'],"cookies":cookies})
        if "sd" in js['videos'].keys() and not t==0: parts.append({"vid":js['videos']['sd'],"cookies":cookies})
        return parts
    
    def scrape_vk_vid(showpage,t):
        alphabet = re.search(r'670x3=\["(.*?)"\]', showpage) 
        
        if alphabet:
            alphabet = alphabet.group(1)

        if not alphabet:
            return

        alphabet=re.findall(r'670x3=\["(.*?)"\]',showpage)[0].replace("x","u00").decode("raw_unicode_escape","ignore").encode("ascii")
        

        encoded_parts = re.findall(r"jQuery\.mp4\.d\(\"(.*?)\"\)", showpage)
        pages = [decode_base64(alphabet, x) for x in encoded_parts]
        
        parts=[]
        for i, page in enumerate(pages):
            showpage=open_url(page)
            ## having sd videos in the playlist will cause problems on multiparted videos but, for now lets go this way
            regex = re.findall("url480=(.*?)&",showpage)
            if len(regex)>0 and not t==0: parts.append({"vid":regex[0],"cookies":[]})
            regex = re.findall("url360=(.*?)&",showpage)
            if len(regex)>0 and not t==0: parts.append({"vid":regex[0],"cookies":[]})
            regex = re.findall("url240=(.*?)&",showpage)
            if len(regex)>0 and not t==0: parts.append({"vid":regex[0],"cookies":[]})
            regex = re.findall("url720=(.*?)&",showpage)
            if len(regex)>0 and not t==1: parts.append({"vid":regex[0],"cookies":[]})
        
        return parts

    
    
    def get_show(t):

        showpage = open_url(WATCH_URL[t][0] % {'show': showcode,
                                               'season': season,
                                               'episode': episode})

        if not showpage:
            return
        
        sources=[("current server link","current servername")]
        current_server=re.findall('\"trigger\ssmall\syellowa\sawesome\">Kaynak:\s(.*?)<img', showpage)
        if len(current_server)>0 :
            alternate_servers=re.findall('\"trigger\ssmall\syellowa\sawesome\"(.*?)bubbleInfo',showpage,re.DOTALL)
            alternate_servers=re.findall('<a\shref=\"(.*?)\".*?gif>(.*?)</a>',alternate_servers[0],re.DOTALL)
            sources=[("current server link",current_server[0])]
            sources.extend(alternate_servers)
        
        if len(sources)==0:
            return
        elif len(sources)==1:
            index=0
        elif len(sources)>1:
            index=xbmcgui.Dialog().select("Source", [ unicode(x[1].decode("windows-1254")) for x in sources])
        
        if index>0:
            showpage = open_url(DOMAIN+sources[index][0])
        
        for scrape_func in [scrape_facebook_vid,scrape_mailru_vid,scrape_vk_vid]:
            parts=scrape_func(showpage,t)
            if len(parts)>0:
                break
        
        return parts
        


    show = get_show(watch_type)

    if not show:
        print "This episode is not available in format: '%s'" \
              % WATCH_URL[watch_type][2]

        for fallback in sorted(WATCH_URL.keys()):
            if fallback == watch_type:
                continue  # tried before
 
            show = get_show(fallback)
            if show:
                break
 
            else:
                print "This episode is not available in format: '%s'" \
                      % WATCH_URL[fallback][2]
 
        else:
            print "This episode is not available in any format."
            return

    return show


#### PLUGIN STUFF ####

def display_main_menu():
    create_list_item("Recently added TV Shows",
                     create_xbmc_url(action="showRecentlyAdded"),
                     totalItems=3)

    #create_list_item("Turkish TV Shows",
    #                 create_xbmc_url(action="showNames", language=TURKISHSHOW),
    #                 fanart=turkish_fanart,
    #                 totalItems=3)

    create_list_item("TV Shows",
                     create_xbmc_url(action="showNames", language=ENGLISHSHOW),
                     fanart=english_fanart,
                     totalItems=3)

    xbmcplugin.endOfDirectory(PLUGIN_ID)


def display_recently_added_menu(params):
    recents = get_recently_added_info()
    if not recents:
        xbmcgui.Dialog().ok("Error", "Recently added episodes not found.")
        return
    l = len(recents)

    for code, name, season, episodeno in recents:
        iconimage = get_show_avatar_url(code)
        thumbimage = get_show_thumbnail_url(code)

        create_list_item(
        "%s - S%sE%s" % (name.decode("utf-8"), season, episodeno),
        create_xbmc_url(action="showEpisodes",
                        name=name,
                        showcode=code,
                        season=season,
                        autoplayepisode=episodeno,
                        language=ENGLISHSHOW),
        iconImage=iconimage,
        thumbnailImage=thumbimage,
        totalItems=l,
        folder=False)

    # Switch to Thumbnail view
    xbmc.executebuiltin("Container.SetViewMode(500)")
    xbmcplugin.endOfDirectory(PLUGIN_ID, cacheToDisc=True)


def display_show_names_menu(params):
    lang = params["language"][0]

    shownames = [x for x in get_show_names() if str(x[1]) == lang]
    showlen = len(shownames)

    for code, langcode, name in shownames:
        if str(langcode) == lang:

            fanart = turkish_fanart \
                     if int(lang) == TURKISHSHOW \
                     else english_fanart

            thumbimage = get_show_thumbnail_url(code)
            iconimage = get_show_avatar_url(code)
            create_list_item(name,
                             create_xbmc_url(action="showSeasons",
                                             name=name,
                                             showcode=code,
                                             language=lang),
                             fanart=fanart,
                             iconImage=iconimage,
                             thumbnailImage=thumbimage,
                             totalItems=showlen)

    # Switch to Thumbnail view
    xbmc.executebuiltin("Container.SetViewMode(500)")
    xbmcplugin.endOfDirectory(PLUGIN_ID, cacheToDisc=True)


def display_show_seasons_menu(params):
    name = params["name"][0]
    code = params["showcode"][0]
    lang = params["language"][0]

    thumbimage = get_show_thumbnail_url(code)
    iconimage = get_show_avatar_url(code)
    fanart = turkish_fanart if int(lang) == TURKISHSHOW else english_fanart

    season_info = get_show_season_info(code)
    season_info = sorted(season_info,
                         key=lambda x: int(x.split(".")[0]),
                         reverse=True)

    if not season_info:
        xbmcgui.Dialog().ok("Error", "No seasons found...")
        return

    seasonStringWidth = len(max(season_info,
                                key=lambda x: int(x.split(".")[0])))

    for s in season_info:
        create_list_item("%s - %s" % (unicode(name.decode("windows-1254")), s),
                         create_xbmc_url(action="showEpisodes",
                                         name=name,
                                         showcode=code,
                                         season=s.split(".")[0],
                                         language=lang),
                         iconImage=iconimage,
                         thumbnailImage=thumbimage,
                         fanart=fanart,
                         totalItems=len(season_info))

    xbmcplugin.endOfDirectory(PLUGIN_ID, cacheToDisc=True)


def display_show_episodes_menu(params):
    name = params["name"][0]
    code = params["showcode"][0]
    season = params["season"][0]
    lang = params["language"][0]
    autoplayepisode = params.get("autoplayepisode", [None])[0]
        
    epinfo = get_show_episode_info(code,season)

    if not epinfo:
        xbmcgui.Dialog().ok("Error", "No episodes found for this season.")
        return

    # autoplayepisode parameter provides a way to quickly play
    # recently added episodes
    if autoplayepisode:
        eplist = [x for x in epinfo if x[0] == season \
                                   and x[1] == autoplayepisode]
        if not eplist:
            xbmcgui.Dialog().ok("Error", "Selected episode not found.")
            return

        #TODO: find a clever way of jumping to display_show URL
        params = urlparse.parse_qs(
                               urllib.urlencode({"name": name,
                                                 "showcode": code,
                                                 "season": season,
                                                 "episode": autoplayepisode,
                                                 "watchtypes": eplist[0][3]}))
        display_show(params)
        return

    thumbimage = get_show_thumbnail_url(code)
    iconimage = get_show_avatar_url(code)
    fanart = turkish_fanart if int(lang) == TURKISHSHOW else english_fanart

    eplist = sorted(
             list(set(((int(x[1]), x[2], x[3]) for x in epinfo
             if x[0] == season))),
             reverse=True)

    if not eplist:
        xbmcgui.Dialog().ok("Error", "No episodes found for this season.")
        return

    lenEpList = len(eplist)
    episodeStringWidth = len(str(max(eplist, key=lambda x: x[0])[0]))

    for epno, epname, epwatchtypes in eplist:
        epno = str(epno)
        epname = "(%s)" % epname if epname else ""

        create_list_item("%s - S%sE%s %s" % (name,
                                             season,
                                             epno.zfill(episodeStringWidth),
                                             epname),
                         create_xbmc_url(action="showVideo",
                                         name=name,
                                         showcode=code,
                                         season=season,
                                         episode=epno,
                                         watchtypes=epwatchtypes),
                         folder=False,
                         thumbnailImage=thumbimage,
                         fanart=fanart,
                         iconImage=iconimage,
                         totalItems=lenEpList)

    xbmcplugin.endOfDirectory(PLUGIN_ID, cacheToDisc=True)

def display_show(params):
    name = params["name"][0]
    code = params["showcode"][0]
    season = params["season"][0]
    episode = params["episode"][0]
    watchtypes = [int(x) for x in params["watchtypes"][0].split("-")]

    if len(watchtypes) > 1:
        selected_quality = xbmcgui.Dialog().select("Quality",
                           [WATCH_URL[key][2] for key in sorted(watchtypes)])

        if selected_quality == -1:
            return

    elif len(watchtypes) == 1:
        selected_quality = watchtypes[0]

    else:
        xbmcgui.Dialog().ok("Error", "Could not find an appropriate quality.")
        return

    urls = get_show_video_urls(code, season, episode, selected_quality)
    iconImage = thumb = get_show_thumbnail_url(code)

    if not urls:
        xbmcgui.Dialog().ok("Error", "Episode not found...")
        return

    video_urls = urls

    """
    for i, video in enumerate(video_urls):
        create_list_item("Part %s" % (i+1),
                         video,
                         iconImage=iconImage,
                         thumbnailImage=thumb,
                         folder=False)

    xbmcplugin.endOfDirectory(PLUGIN_ID)
    """

    playlist.clear()
    for i, video in enumerate(video_urls):
        listitem = xbmcgui.ListItem(
            '%s S%sE%s Part %s' % (name, season, episode, (i + 1)))

        listitem.setInfo('video', {'Title': name})
        playlist.add(url=video['vid']+"|Cookie="+urllib.urlencode(video["cookies"],True), listitem=listitem)
    print "playlist addedd: " + video['vid']+"|Cookie="+urllib.urlencode(video["cookies"],True)
    player.play(playlist)


def create_xbmc_url(**parameters):
    return "%s?%s" % (sys.argv[0], urllib.urlencode(parameters))


def create_list_item(name,
                     url,
                     iconImage="",
                     thumbnailImage="",
                     folder=True,
                     fanart=None,
                     totalItems=0):

    if folder and not iconImage:
        iconImage = "DefaultFolder.png"
    elif not folder and not iconImage:
        iconImage = "DefaultVideo.png"

    l = xbmcgui.ListItem(name,
                         iconImage=iconImage,
                         thumbnailImage=thumbnailImage)

    l.setInfo(type="Video", infoLabels={"Title": name})

    if not fanart:
        l.setProperty('fanart_image', __settings__.getAddonInfo('fanart'))
    else:
        l.setProperty('fanart_image', fanart)

    xbmcplugin.addDirectoryItem(handle=PLUGIN_ID,
                                url=url,
                                listitem=l,
                                isFolder=folder,
                                totalItems=totalItems)


ACTION_HANDLERS = {"showEpisodes": display_show_episodes_menu,
                   "showSeasons": display_show_seasons_menu,
                   "showNames": display_show_names_menu,
                   "showRecentlyAdded": display_recently_added_menu,
                   "showVideo": display_show}

params = urlparse.parse_qs(sys.argv[2][1:])

if len(params) == 0:
    display_main_menu()
else:
    ACTION_HANDLERS[params['action'][0]](params)
