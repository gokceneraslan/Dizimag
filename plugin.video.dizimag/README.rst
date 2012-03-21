Dizimag addon for XBMC
======================

What is Dizimag addon for XBMC?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

diozimag.com is a Turkish website for watching full episodes of both Turkish and English popular TV shows. This is a XBMC addon to watch TV shows presented in dizimag.com.

Currently addon is only tested with xbmc 11.0 (Eden) Beta 2 in Fedora 17.

How to install?
~~~~~~~~~~~~~~~

To install, first clone the repo using "git clone git://github.com/gokceneraslan/Dizimag.git" and then enter Dizimag directory and use "git archive HEAD -o $HOME/dizimag-addon.zip" command to prepare a .zip addon file. Then use "System -> Add-ons -> Install using zip file" path in XBMC to install the addon.

TODO:
~~~~~
* Implement getting and saving user login information.

* Categorize Turkish and English TV show in the first menu. (Done)

* Find a way to hide fake episode entries and get rid of "Episode not found" error. (Done)

* Provide a way to choose between High/Low Resolution and Turkish/English subs. (Done by bluesign)

* Use iconImage and thumbnailImage of ListItems wisely. (Done)

* Show name of the episodes (Done by bluesign)
