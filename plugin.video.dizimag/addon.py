# Licensed under the GNU General Public License, version 2.
# See the file http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt

import xbmc, xbmcaddon, xbmcgui, xbmcplugin
import urllib, urlparse, urllib2, HTMLParser, os, sys, re, xml.dom.minidom as md
from BeautifulSoup import BeautifulSoup as BS

#SHOWNAMES_URL = "http://i.dizimag.com/cache/d.js" # this does not provide info about the language of the tv show
SHOWNAMES_URL = "http://dizimag.com/_diziliste.asp"

TURKISHSHOW, ENGLISHSHOW = range(2)

SHOWFLV_URL = "http://www.dizimag.com/_list.asp?dil=%(lang)d&x=%(code)s&d.xml"
SHOW_URL = "http://www.dizimag.com/%(show)s"
SHOW_THUMBNAIL_URL = "http://i.dizimag.com/dizi/%(show)s.jpg"
SHOW_AVATAR_URL = "http://i.dizimag.com/dizi/%(show)s-avatar.jpg"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:10.0.1) Gecko/20100101 Firefox/10.0.1"

#Recently added episodes
RECENTLY_ADDED_EDISODES_URL = "http://dizimag.com/_yenie.asp?a=%(pageno)s"
RECENTLY_ADDED_EPISODES_PAGE_MAX = 4

#Backgrounds
#http://dizimag.com/_arkaplan.asp

#Subtitle translation percentage
#http://dizimag.com/_altyazi.asp

WATCH_SHOW_TR_SUB_HD_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-%(episode)s-bolum-720p-izle-dizi.html"
WATCH_SHOW_TR_SUB_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-%(episode)s-bolum-izle-dizi.html"
WATCH_SHOW_ENG_SUB_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-%(episode)s-bolum-subing-izle-dizi.html"
WATCH_SHOW_NO_SUB_URL = "http://www.dizimag.com/%(show)s-%(season)s-sezon-%(episode)s-bolum-nosub-izle-dizi.html"

# poor man's enum, hehe
# Be careful: Types are in the order of choice
WATCH_TYPE_TR_SUB_HD, WATCH_TYPE_TR_SUB, WATCH_TYPE_ENG_SUB, WATCH_TYPE_NO_SUB, = range(4)


SUBTITLE_NONE, SUBTITLE_TURKISH, SUBTITLE_ENGLISH, = range(3)

WATCH_URL = { 
              WATCH_TYPE_ENG_SUB:   (WATCH_SHOW_ENG_SUB_URL, SUBTITLE_ENGLISH, "Low resolution video with English subtitles"),  
              WATCH_TYPE_NO_SUB:    (WATCH_SHOW_NO_SUB_URL, SUBTITLE_NONE,    "Low resolution video"),
              WATCH_TYPE_TR_SUB_HD: (WATCH_SHOW_TR_SUB_HD_URL, SUBTITLE_TURKISH, "720p HD video"), 
              WATCH_TYPE_TR_SUB:    (WATCH_SHOW_TR_SUB_URL, SUBTITLE_TURKISH,     "Low resolution video with Turkish subtitles")
              } 

__plugin__ = 'Dizimag'
__author__ = 'Gokcen Eraslan <gokcen.eraslan@gmail.com>'
__url__ = 'http://code.google.com/p/plugin/'
__date__ = '03-14-2012'
__version__ = '0.5.3'
__settings__ = xbmcaddon.Addon(id = 'plugin.video.dizimag')

PLUGIN_ID = int(sys.argv[1])

turkish_fanart = os.path.join( __settings__.getAddonInfo( 'path' ), 'resources', 'media', 'turkish-fanart.jpg' )
english_fanart = os.path.join( __settings__.getAddonInfo( 'path' ), 'resources', 'media', 'english-fanart.jpg' )

playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
player = xbmc.Player(xbmc.PLAYER_CORE_MPLAYER)

def open_url(url):
    #print url
    try:
        req = urllib2.Request( url )
        req.add_header('User-Agent', USER_AGENT)
        content = urllib2.urlopen( req )
        data = content.read()
        content.close()
    except:
        print "URL (%s) not found..." % url
        return None

    return data

def get_show_names():

    listpage = open_url(SHOWNAMES_URL)

    if not listpage:
        xbmcgui.Dialog().ok("Error", 'Page not found (%s)...' % SHOWNAMES_URL)
        return
 
    shownames = re.findall(r'<a *?href="/([a-zA-Z0-9-]*?)" *?class="tdiz (.*?)">(.*?)</a>', listpage)
    shownames = [(x[0], TURKISHSHOW if x[1].lower() == "yerli" else ENGLISHSHOW, x[2].decode("iso-8859-9").encode("utf-8")) for x in shownames]

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
    for i in range(1, int(RECENTLY_ADDED_EPISODES_PAGE_MAX)+1):
        result.extend(parse_recently_added_page(open_url(RECENTLY_ADDED_EDISODES_URL % {"pageno": str(i)})))

    return result

def get_show_episode_info(showcode):
    showpage = open_url(SHOW_URL % {'show': showcode})

    if not showpage:
        xbmcgui.Dialog().ok("Error", 'Page not found (%s)...' % SHOW_URL % {'show': showcode})
        return

    episodes = parse_html_show_table(showpage)

    return sorted(episodes, cmp = lambda x,y: cmp(int(x[0])*1000+int(x[1]), int(y[0])*1000+int(y[1])), reverse=True)
 
def parse_show_rss(rss):
    try:
        tree = md.parseString(rss)
    except:
        try:
            # some rss files seem not well-formed, try to fix them
            tree = md.parseString(rss.replace('&', '&amp;'))
        except:
            return (None, None)

    video_urls = filter(lambda x: x, (x.getAttribute("url") for x in tree.getElementsByTagName("media:content")))
    # normalize URL's. Some URL's include spaces etc. convert them to %XX representation
    video_urls = map(lambda x: urllib.quote(x, safe="%/:=&?~#+!$,;'@()*[]"), video_urls)

    video_thumbnails = filter(lambda x: x, (x.getAttribute("url") for x in tree.getElementsByTagName("media:thumbnail")))

    return (video_urls, video_thumbnails)

def parse_html_get_season_info(tree):
    tree = BS(tree)
    divs = tree.body.findAll(lambda x: x.name == "div" and "dizi_list" in x.get("class", "").split())
    return [HTMLParser.HTMLParser().unescape(x.text) for x in divs]

def parse_html_show_table(tree):
    tree = BS(tree)
    show_elements = tree.body.findAll(lambda x: x.name == "td" and "blmin" in x.get("class", "").split())
    result = []

    for episode in show_elements:
        a_elements = episode.findAll("a")
        img_elements = episode.findAll("img")

        episode_season = episode["class"].split()[0].split("x")[0][1:]
        episode_no = episode["class"].split()[0].split("x")[1]

        if len(a_elements) > 2:
            episode_name = HTMLParser.HTMLParser().unescape(a_elements[2].text.encode("utf-8"))
        else:
            episode_name = u""

        episode_watch_types = []

        for img in img_elements:
            if "tlb_tr" in img.get("class", "").split(): #yes there is a mistake in dizimag's code tlb_tr <-> tlb_eng
                episode_watch_types.append(str(WATCH_TYPE_ENG_SUB))
            elif "tlb_nosub" in img.get("class", "").split():
                episode_watch_types.append(str(WATCH_TYPE_NO_SUB))
            elif "tlb_hd" in img.get("class", "").split():
                episode_watch_types.append(str(WATCH_TYPE_TR_SUB_HD))
            elif "tlb_eng" in img.get("class", "").split():
                episode_watch_types.append(str(WATCH_TYPE_TR_SUB))

        if not episode_watch_types:
            continue

        result.append([episode_season, episode_no, episode_name, "-".join(episode_watch_types)])

    return result

def parse_recently_added_page(tree):
    tree = BS(tree)
    episodes = tree.findAll('a')
    result = []

    for episode in episodes:
        showre = re.match(r"/(.*?)-([0-9]+?)-sezon-([0-9]+?)-bolum-.*?\.html", episode.get("href", ""))
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

def get_show_video_urls(showcode, season, episode, watch_type = WATCH_TYPE_TR_SUB_HD):

    def get_show(t):

        showpage = open_url(WATCH_URL[t][0] % {'show': showcode, 'season': season, 'episode': episode})

        if not showpage:
            return

        lowres = re.search(r'dusuk="(.*?)";', showpage)
        highres = re.search(r'yuksek="(.*?)";', showpage)

        if lowres:
            lowres = lowres.group(1)
        if highres:
            highres = highres.group(1)

        if not (highres or lowres):
            return

        rss = open_url(SHOWFLV_URL % {'code': highres, 'lang': WATCH_URL[watch_type][1]})

        if not rss:
            rss = open_url(SHOWFLV_URL % {'code': lowres, 'lang': WATCH_URL[watch_type][1]})
            if not rss:
                return

        video_urls, video_thumbnails = parse_show_rss(rss)
        if not video_urls:
            return

        return video_urls, video_thumbnails


    show = get_show(watch_type)

    if not show or not show[0]:
        print "This episode is not available in format: '%s'" % WATCH_URL[watch_type][2]

        for fallback in sorted(WATCH_URL.keys()):
            if fallback == watch_type:
                continue # tried before

            show = get_show(fallback)
            if show and show[0]:
                break

            else:
                print "This episode is not available in format: '%s'" % WATCH_URL[fallback][2]

        else:
            print "This episode is not available in any format."
            return

    return show


#### PLUGIN STUFF ####

def display_main_menu():
    create_list_item("Recently added TV Shows", create_xbmc_url(action="showRecentlyAdded"), totalItems = 3)
    create_list_item("Turkish TV Shows", create_xbmc_url(action="showNames", language=TURKISHSHOW), fanart = turkish_fanart, totalItems = 3)
    create_list_item("English TV Shows", create_xbmc_url(action="showNames", language=ENGLISHSHOW), fanart = english_fanart, totalItems = 3)

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
        create_list_item("%s - S%sE%s" % (name.decode("utf-8"), season, episodeno), create_xbmc_url(action="showEpisodes", name=name, showcode=code, season=season, autoplayepisode=episodeno, language=ENGLISHSHOW), iconImage=iconimage, thumbnailImage = thumbimage, totalItems = l, folder = False)

    xbmcplugin.endOfDirectory(PLUGIN_ID, cacheToDisc = True)

def display_show_names_menu(params):
    lang = params["language"][0]

    shownames = [ x for x in get_show_names() if str(x[1]) == lang]
    showlen = len(shownames)

    for code, langcode, name in shownames:
        if str(langcode) == lang:
            fanart = turkish_fanart if int(lang) == TURKISHSHOW else english_fanart
            thumbimage = get_show_thumbnail_url(code)
            iconimage = get_show_avatar_url(code)
            create_list_item(name, create_xbmc_url(action="showSeasons", name=name, showcode=code, language=lang), fanart = fanart, iconImage=iconimage, thumbnailImage=thumbimage, totalItems = showlen)

    xbmcplugin.endOfDirectory(PLUGIN_ID, cacheToDisc = True)

def display_show_seasons_menu(params):
    name = params["name"][0]
    code = params["showcode"][0]
    lang = params["language"][0]

    thumbimage = get_show_thumbnail_url(code)
    iconimage = get_show_avatar_url(code)
    fanart = turkish_fanart if int(lang) == TURKISHSHOW else english_fanart

    season_info = get_show_season_info(code)
    season_info = sorted(season_info, key=lambda x: int(x.split(".")[0]), reverse = True)

    if not season_info:
        xbmcgui.Dialog().ok("Error", "No seasons found...")
        return

    seasonStringWidth = len(max(season_info, key=lambda x: int(x.split(".")[0])))

    for s in season_info:
        create_list_item("%s - %s" % (name.decode("utf-8"), s), create_xbmc_url(action="showEpisodes", name=name, showcode=code, season=s.split(".")[0], language=lang), iconImage = iconimage, thumbnailImage = thumbimage, fanart = fanart, totalItems = len(season_info))

    xbmcplugin.endOfDirectory(PLUGIN_ID, cacheToDisc = True)
   
def display_show_episodes_menu(params):
    name = params["name"][0]
    code = params["showcode"][0]
    season = params["season"][0]
    lang = params["language"][0]
    autoplayepisode = params.get("autoplayepisode",[None])[0]
    
    epinfo = get_show_episode_info(code)

    if not epinfo:
        xbmcgui.Dialog().ok("Error", "No episodes found for this season.")
        return

    # autoplayepisode parameter provides a way to quickly play recently added episodes
    if autoplayepisode:
        eplist = [x for x in epinfo if x[0] == season and x[1] == autoplayepisode]
        if not eplist:
            xbmcgui.Dialog().ok("Error", "Selected episode not found.")
            return
        
        #TODO: find a clever way of jumping to display_show URL
        params = urlparse.parse_qs(urllib.urlencode({"name": name, "showcode": code, "season": season, "episode": autoplayepisode, "watchtypes": eplist[0][3]}))
        display_show(params)
        return

    thumbimage = get_show_thumbnail_url(code)
    iconimage = get_show_avatar_url(code)
    fanart = turkish_fanart if int(lang) == TURKISHSHOW else english_fanart

    eplist = sorted(list(set(((int(x[1]),x[2],x[3]) for x in epinfo if x[0] == season))), reverse = True)

    if not eplist:
        xbmcgui.Dialog().ok("Error", "No episodes found for this season.")
        return

    lenEpList = len(eplist)
    episodeStringWidth =  len(str(max(eplist, key=lambda x: x[0])[0]))

    for epno, epname, epwatchtypes in eplist:
        epno = str(epno)
        epname = "(%s)" % epname if epname else ""

        create_list_item("%s - S%sE%s %s" % (name, season, epno.zfill(episodeStringWidth), epname), create_xbmc_url(action="showVideo", name=name, showcode=code, season=season, episode=epno, watchtypes=epwatchtypes), folder = False, thumbnailImage = thumbimage, fanart = fanart, iconImage = iconimage, totalItems = lenEpList)

    xbmcplugin.endOfDirectory(PLUGIN_ID, cacheToDisc = True)

def display_show(params):
    name = params["name"][0]
    code = params["showcode"][0]
    season = params["season"][0]
    episode = params["episode"][0]
    watchtypes = [int(x) for x in params["watchtypes"][0].split("-")]

    if len(watchtypes) > 1:
        selected_quality= xbmcgui.Dialog().select("Quality", [ WATCH_URL[key][2] for key in sorted(watchtypes) ])

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


    video_urls, video_thumbnails = urls
    if video_thumbnails:
        iconImage = video_thumbnails[0]

    """
    for i, video in enumerate(video_urls):
        create_list_item("Part %s" % (i+1), video, iconImage = iconImage, thumbnailImage = thumb, folder = False)
    xbmcplugin.endOfDirectory(PLUGIN_ID)
    """

    playlist.clear()
    for i, video in enumerate(video_urls):
        listitem = xbmcgui.ListItem('%s S%sE%s Part %s' % (name, season, episode, (i+1)))
        listitem.setInfo('video', {'Title': name})
        playlist.add(url=video, listitem=listitem)

    player.play(playlist)

def create_xbmc_url(**parameters):
    return "%s?%s" % (sys.argv[0], urllib.urlencode(parameters))

def create_list_item(name, url, iconImage = "", thumbnailImage = "", folder = True, fanart = None, totalItems = 0):
    if folder and not iconImage:
        iconImage = "DefaultFolder.png"
    elif not folder and not iconImage:
        iconImage = "DefaultVideo.png"

    l = xbmcgui.ListItem(name, iconImage = iconImage, thumbnailImage = thumbnailImage)
    l.setInfo( type = "Video", infoLabels = { "Title": name } ) 

    if not fanart:
        l.setProperty('fanart_image',__settings__.getAddonInfo('fanart'))
    else:
        l.setProperty('fanart_image', fanart)

    xbmcplugin.addDirectoryItem(handle=PLUGIN_ID, url = url, listitem = l, isFolder = folder, totalItems = totalItems)


ACTION_HANDLERS = { "showEpisodes"     : display_show_episodes_menu,
                    "showSeasons"      : display_show_seasons_menu,
                    "showNames"        : display_show_names_menu,
                    "showRecentlyAdded": display_recently_added_menu,
                    "showVideo"        : display_show }

params = urlparse.parse_qs(sys.argv[2][1:])

if len(params) == 0:
    display_main_menu()
else:
    ACTION_HANDLERS[params['action'][0]](params)
