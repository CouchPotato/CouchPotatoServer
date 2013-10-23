SleekXMPP
#########

SleekXMPP is an MIT licensed XMPP library for Python 2.6/3.1+,
and is featured in examples in
`XMPP: The Definitive Guide <http://oreilly.com/catalog/9780596521271>`_ 
by Kevin Smith, Remko Tronçon, and Peter Saint-Andre. If you've arrived
here from reading the Definitive Guide, please see the notes on updating
the examples to the latest version of SleekXMPP.

SleekXMPP's design goals and philosphy are:

**Low number of dependencies**
    Installing and using SleekXMPP should be as simple as possible, without
    having to deal with long dependency chains.

    As part of reducing the number of dependencies, some third party
    modules are included with SleekXMPP in the ``thirdparty`` directory.
    Imports from this module first try to import an existing installed
    version before loading the packaged version, when possible.

**Every XEP as a plugin**
    Following Python's "batteries included" approach, the goal is to
    provide support for all currently active XEPs (final and draft). Since
    adding XEP support is done through easy to create plugins, the hope is
    to also provide a solid base for implementing and creating experimental
    XEPs.

**Rewarding to work with**
    As much as possible, SleekXMPP should allow things to "just work" using
    sensible defaults and appropriate abstractions. XML can be ugly to work
    with, but it doesn't have to be that way.


Get the Code
------------

Get the latest stable version from PyPI::

    pip install sleekxmpp

The latest source code for SleekXMPP may be found on `Github
<http://github.com/fritzy/SleekXMPP>`_. Releases can be found in the
``master`` branch, while the latest development version is in the
``develop`` branch.

**Latest Release**
    - `1.1.10 <http://github.com/fritzy/SleekXMPP/zipball/1.1.10>`_

**Develop Releases**
    - `Latest Develop Version <http://github.com/fritzy/SleekXMPP/zipball/develop>`_


Installing DNSPython
---------------------
If you are using Python3 and wish to use dnspython, you will have to checkout and
install the ``python3`` branch::

    git clone http://github.com/rthalley/dnspython
    cd dnspython
    git checkout python3
    python3 setup.py install

Discussion
----------
A mailing list and XMPP chat room are available for discussing and getting
help with SleekXMPP.

**Mailing List**
    `SleekXMPP Discussion on Google Groups <http://groups.google.com/group/sleekxmpp-discussion>`_

**Chat**
    `sleek@conference.jabber.org <xmpp:sleek@conference.jabber.org?join>`_


Documentation and Testing
-------------------------
Documentation can be found both inline in the code, and as a Sphinx project in ``/docs``.
To generate the Sphinx documentation, follow the commands below. The HTML output will
be in ``docs/_build/html``::

    cd docs
    make html
    open _build/html/index.html

To run the test suite for SleekXMPP::

    python testall.py


The SleekXMPP Boilerplate
-------------------------
Projects using SleekXMPP tend to follow a basic pattern for setting up client/component
connections and configuration. Here is the gist of the boilerplate needed for a SleekXMPP
based project. See the documetation or examples directory for more detailed archetypes for
SleekXMPP projects::

    import logging

    from sleekxmpp import ClientXMPP
    from sleekxmpp.exceptions import IqError, IqTimeout


    class EchoBot(ClientXMPP):

        def __init__(self, jid, password):
            ClientXMPP.__init__(self, jid, password)

            self.add_event_handler("session_start", self.session_start)
            self.add_event_handler("message", self.message)

            # If you wanted more functionality, here's how to register plugins:
            # self.register_plugin('xep_0030') # Service Discovery
            # self.register_plugin('xep_0199') # XMPP Ping

            # Here's how to access plugins once you've registered them:
            # self['xep_0030'].add_feature('echo_demo')

            # If you are working with an OpenFire server, you will
            # need to use a different SSL version:
            # import ssl
            # self.ssl_version = ssl.PROTOCOL_SSLv3

        def session_start(self, event):
            self.send_presence()
            self.get_roster()

            # Most get_*/set_* methods from plugins use Iq stanzas, which
            # can generate IqError and IqTimeout exceptions
            #
            # try:
            #     self.get_roster()
            # except IqError as err:
            #     logging.error('There was an error getting the roster')
            #     logging.error(err.iq['error']['condition'])
            #     self.disconnect()
            # except IqTimeout:
            #     logging.error('Server is taking too long to respond')
            #     self.disconnect()

        def message(self, msg):
            if msg['type'] in ('chat', 'normal'):
                msg.reply("Thanks for sending\n%(body)s" % msg).send()


    if __name__ == '__main__':
        # Ideally use optparse or argparse to get JID, 
        # password, and log level.

        logging.basicConfig(level=logging.DEBUG,
                            format='%(levelname)-8s %(message)s')

        xmpp = EchoBot('somejid@example.com', 'use_getpass')
        xmpp.connect()
        xmpp.process(block=True)


Credits
-------
**Main Author:** Nathan Fritz
    `fritzy@netflint.net <xmpp:fritzy@netflint.net?message>`_, 
    `@fritzy <http://twitter.com/fritzy>`_

    Nathan is also the author of XMPPHP and `Seesmic-AS3-XMPP
    <http://code.google.com/p/seesmic-as3-xmpp/>`_, and a former member of 
    the XMPP Council.

**Co-Author:** Lance Stout
    `lancestout@gmail.com <xmpp:lancestout@gmail.com?message>`_, 
    `@lancestout <http://twitter.com/lancestout>`_

**Contributors:**
    - Brian Beggs (`macdiesel <http://github.com/macdiesel>`_)
    - Dann Martens (`dannmartens <http://github.com/dannmartens>`_)
    - Florent Le Coz (`louiz <http://github.com/louiz>`_)
    - Kevin Smith (`Kev <http://github.com/Kev>`_, http://kismith.co.uk)
    - Remko Tronçon (`remko <http://github.com/remko>`_, http://el-tramo.be)
    - Te-jé Rogers (`te-je <http://github.com/te-je>`_)
    - Thom Nichols (`tomstrummer <http://github.com/tomstrummer>`_)
