CouchPotato
=====

CouchPotato (CP) is an automatic NZB and torrent downloader. You can keep a "movies I want"-list and it will search for NZBs/torrents of these movies every X hours.
Once a movie is found, it will send it to SABnzbd or download the torrent to a specified directory.


## Running from Source

CouchPotatoServer can be run from source. This will use *git* as updater, so make sure that is installed.

Windows, see [the CP forum](http://couchpota.to/forum/showthread.php?tid=14) for more details:

* Install [Python 2.7](http://www.python.org/download/releases/2.7.3/)
* Then install [PyWin32 2.7](http://sourceforge.net/projects/pywin32/files/pywin32/Build%20217/) and [GIT](http://git-scm.com/)
* If you come and ask on the forums 'why directory selection no work?', I will kill a kitten, also this is because you need PyWin32
* Open up `Git Bash` (or CMD) and go to the folder you want to install CP. Something like Program Files.
* Run `git clone https://github.com/RuudBurger/CouchPotatoServer.git`.
* You can now start CP via `CouchPotatoServer\CouchPotato.py` to start
* Your browser should open up, but if it doesn't go to `http://localhost:5050/`

OS X:

* If you're on Leopard (10.5) install Python 2.6+: [Python 2.6.5](http://www.python.org/download/releases/2.6.5/)
* Install [GIT](http://git-scm.com/)
* Open up `Terminal`
* Go to your App folder `cd /Applications`
* Run `git clone https://github.com/RuudBurger/CouchPotatoServer.git`
* Then do `python CouchPotatoServer/CouchPotato.py`
* Your browser should open up, but if it doesn't go to `http://localhost:5050/`

Linux (Ubuntu / Debian):

* Install [GIT](http://git-scm.com/) with `apt-get install git-core`
* 'cd' to the folder of your choosing.
* Run `git clone https://github.com/RuudBurger/CouchPotatoServer.git`
* Then do `python CouchPotatoServer/CouchPotato.py` to start
* To run on boot copy the init script `sudo cp CouchPotatoServer/init/ubuntu /etc/init.d/couchpotato`
* Change the paths inside the init script `sudo nano /etc/init.d/couchpotato`
* Make it executable `sudo chmod +x /etc/init.d/couchpotato`
* Add it to defaults `sudo update-rc.d couchpotato defaults`
* Open your browser and go to `http://localhost:5050/`


FreeBSD :

* Update your ports tree `sudo portsnap fetch update`
* Install Python 2.6+ [lang/python](http://www.freshports.org/lang/python) with `cd /usr/ports/lang/python; sudo make install clean`
* Install port [databases/py-sqlite3](http://www.freshports.org/databases/py-sqlite3) with `cd /usr/ports/databases/py-sqlite3; sudo make install clean`
* Add a symlink to 'python2' `sudo ln -s /usr/local/bin/python /usr/local/bin/python2`
* Install port [ftp/libcurl](http://www.freshports.org/ftp/libcurl) with `cd /usr/ports/ftp/fpc-libcurl; sudo make install clean`
* Install port [ftp/curl](http://www.freshports.org/ftp/bcurl), deselect 'Asynchronous DNS resolution via c-ares' when prompted as part of config `cd /usr/ports/ftp/fpc-libcurl; sudo make install clean`
* Install port [textproc/docbook-xml-450](http://www.freshports.org/textproc/docbook-xml-450) with `cd /usr/ports/textproc/docbook-xml-450; sudo make install clean`
* Install port [GIT](http://git-scm.com/) with `cd /usr/ports/devel/git; sudo make install clean`
* 'cd' to the folder of your choosing.
* Run `git clone https://github.com/RuudBurger/CouchPotatoServer.git`
* Then run `sudo python CouchPotatoServer/CouchPotato.py` to start for the first time
* To run on boot copy the init script. `sudo cp CouchPotatoServer/init/freebsd /etc/rc.d/couchpotato`
* Change the paths inside the init script. `sudo vim /etc/rc.d/couchpotato`
* Make init script executable. `sudo chmod +x /etc/rc.d/couchpotato`
* Add init to startup. `sudo echo 'couchpotato_enable="YES"' >> /etc/rc.conf`
* Open your browser and go to: `http://server:5050/`
