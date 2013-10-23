
#MODULESDIR=/usr/lib/($PYTHONVERSION)/site-packages

install:
	# Add here commands to install the package into debian/python-xmpp
	[ -d $(MODULESDIR)/xmpp ] || mkdir $(MODULESDIR)/xmpp
	install -m 0644 xmpp/*py $(MODULESDIR)/xmpp
