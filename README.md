CouchPotato Server
=====

CouchPotato (CP) is an automatic NZB and torrent downloader. You can keep a "movies I want"-list and it will search for NZBs/torrents of these movies every X hours.
Once a movie is found, it will send it to SABnzbd or download the torrent to a specified directory.


## Running from Source

CouchPotatoServer can be run from source. This will use *git* as updater, so make sure that is installed also.

Windows, see [the CP forum](http://couchpota.to/forum/showthread.php?tid=14) for more details:

* Install [Python 2.7](http://www.python.org/download/releases/2.7.3/)
* Then install [PyWin32 2.7](http://sourceforge.net/projects/pywin32/files/pywin32/Build%20217/) and [GIT](http://git-scm.com/)
* If you come and ask on the forums 'why directory selection no work?', I will kill a kitten, also this is because you need PyWin32
* Open up `Git Bash` (or CMD) and go to the folder you want to install CP. Something like Program Files.
* Run `git clone https://github.com/RuudBurger/CouchPotatoServer.git`.
* You can now start CP via `CouchPotatoServer\CouchPotato.py` to start
* Open your browser and go to: `http://localhost:5050/`

OSx:

* If you're on Leopard (10.5) install Python 2.6+: [Python 2.6.5](http://www.python.org/download/releases/2.6.5/)
* Install [GIT](http://git-scm.com/)
* Open up `Terminal`
* Go to your App folder `cd /Applications`
* Run `git clone https://github.com/RuudBurger/CouchPotatoServer.git`
* Then do `python CouchPotatoServer/CouchPotato.py`
* Open your browser and go to: `http://localhost:5050/`

Linux (ubuntu / debian):

* Install [GIT](http://git-scm.com/) with `apt-get install git-core`
* 'cd' to the folder of your choosing.
* Run `git clone https://github.com/RuudBurger/CouchPotatoServer.git`
* Then do `python CouchPotatoServer/CouchPotato.py` to start
* To run on boot copy the init script. `sudo cp CouchPotatoServer/init/ubuntu /etc/init.d/couchpotato`
* Change the paths inside the init script. `sudo nano /etc/init.d/couchpotato`
* Make it executable. `sudo chmod +x /etc/init.d/couchpotato`
* Add it to defaults. `sudo update-rc.d couchpotato defaults`
* Open your browser and go to: `http://localhost:5050/`
