Dizimag addon for XBMC
======================

What is Dizimag addon for XBMC?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Dizimag <http://www.dizimag.com>`_ is a Turkish website for watching full episodes of both Turkish and English popular TV shows. This is a XBMC addon to watch TV shows presented in dizimag.com.

Currently addon is only tested with XBMC 11.0 Eden in Fedora 17.

How to install?
~~~~~~~~~~~~~~~

1. Getting the .zip file
************************

* To install stable versions use `Downloads section <https://github.com/gokceneraslan/Dizimag/downloads>`_ to download latest .zip file.


* To install git snapshots, first clone the repo using :

  :: 

    git clone git://github.com/gokceneraslan/Dizimag.git

  and then enter Dizimag directory and use:

  ::

    git archive HEAD -o $HOME/dizimag-addon.zip

  command to prepare a .zip addon file. 


2. Installing .zip file
**********************

Use "System -> Add-ons -> Install from zip file" path in XBMC to install the addon.


TODO:
~~~~~

* Implement getting & saving user login information, and member features.

* Implement a Caterogies menu just like the one in the website.

* Hide fake seasons of some show and fix occasional "No episodes found" error.

* Display the date of the next episode. (Another website like `epguides <epguides.com>`_ may be used)

* Add information (photos, summaries, cast etc.) about shows and episodes (maybe a context Info menu) (`TVDB python api <https://github.com/dbr/tvdb_api>`_ may be used) 


Done:
~~~~~

* Categorize Turkish and English TV show in the first menu. **(Done)**

* Find a way to hide fake episode entries and get rid of "Episode not found" error. **(Done)**

* Provide a way to choose between High/Low Resolution and Turkish/English subs. **(Done by bluesign)**

* Use iconImage and thumbnailImage of ListItems wisely. **(Done)**

* Show name of the episodes **(Done by bluesign)**
