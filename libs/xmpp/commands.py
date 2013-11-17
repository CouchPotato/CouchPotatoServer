## $Id: commands.py,v 1.17 2007/08/28 09:54:15 normanr Exp $

## Ad-Hoc Command manager
## Mike Albon (c) 5th January 2005

##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU General Public License as published by
##   the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU General Public License for more details.


"""This module is a ad-hoc command processor for xmpppy. It uses the plug-in mechanism like most of the core library. It depends on a DISCO browser manager.

There are 3 classes here, a command processor Commands like the Browser, and a command template plugin Command, and an example command.

To use this module:
    
    Instansiate the module with the parent transport and disco browser manager as parameters.
    'Plug in' commands using the command template.
    The command feature must be added to existing disco replies where neccessary.
    
What it supplies:
    
    Automatic command registration with the disco browser manager.
    Automatic listing of commands in the public command list.
    A means of handling requests, by redirection though the command manager.
"""

from protocol import *
from client import PlugIn

class Commands(PlugIn):
    """Commands is an ancestor of PlugIn and can be attached to any session.
    
    The commands class provides a lookup and browse mechnism. It follows the same priciple of the Browser class, for Service Discovery to provide the list of commands, it adds the 'list' disco type to your existing disco handler function. 
    
    How it works:
        The commands are added into the existing Browser on the correct nodes. When the command list is built the supplied discovery handler function needs to have a 'list' option in type. This then gets enumerated, all results returned as None are ignored.
        The command executed is then called using it's Execute method. All session management is handled by the command itself.
    """
    def __init__(self, browser):
        """Initialises class and sets up local variables"""
        PlugIn.__init__(self)
        DBG_LINE='commands'
        self._exported_methods=[]
        self._handlers={'':{}}
        self._browser = browser

    def plugin(self, owner):
        """Makes handlers within the session"""
        # Plug into the session and the disco manager
        # We only need get and set, results are not needed by a service provider, only a service user.
        owner.RegisterHandler('iq',self._CommandHandler,typ='set',ns=NS_COMMANDS)
        owner.RegisterHandler('iq',self._CommandHandler,typ='get',ns=NS_COMMANDS)
        self._browser.setDiscoHandler(self._DiscoHandler,node=NS_COMMANDS,jid='')
        
    def plugout(self):
        """Removes handlers from the session"""
        # unPlug from the session and the disco manager
        self._owner.UnregisterHandler('iq',self._CommandHandler,ns=NS_COMMANDS)
        for jid in self._handlers:
            self._browser.delDiscoHandler(self._DiscoHandler,node=NS_COMMANDS)

    def _CommandHandler(self,conn,request):
        """The internal method to process the routing of command execution requests"""
        # This is the command handler itself.
        # We must:
        #   Pass on command execution to command handler
        #   (Do we need to keep session details here, or can that be done in the command?)
        jid = str(request.getTo())
        try:
            node = request.getTagAttr('command','node')
        except:
            conn.send(Error(request,ERR_BAD_REQUEST))
            raise NodeProcessed
        if self._handlers.has_key(jid):
            if self._handlers[jid].has_key(node):
                self._handlers[jid][node]['execute'](conn,request)
            else:
                conn.send(Error(request,ERR_ITEM_NOT_FOUND))
                raise NodeProcessed
        elif self._handlers[''].has_key(node):
                self._handlers[''][node]['execute'](conn,request)
        else:
            conn.send(Error(request,ERR_ITEM_NOT_FOUND))
            raise NodeProcessed

    def _DiscoHandler(self,conn,request,typ):
        """The internal method to process service discovery requests"""
        # This is the disco manager handler.
        if typ == 'items':
            # We must:
            #    Generate a list of commands and return the list
            #    * This handler does not handle individual commands disco requests.
            # Pseudo:
            #   Enumerate the 'item' disco of each command for the specified jid
            #   Build responce and send
            #   To make this code easy to write we add an 'list' disco type, it returns a tuple or 'none' if not advertised
            list = []
            items = []
            jid = str(request.getTo())
            # Get specific jid based results
            if self._handlers.has_key(jid):
                for each in self._handlers[jid].keys():
                    items.append((jid,each))
            else:
                # Get generic results
                for each in self._handlers[''].keys():
                    items.append(('',each))
            if items != []:
                for each in items:
                    i = self._handlers[each[0]][each[1]]['disco'](conn,request,'list')
                    if i != None:
                        list.append(Node(tag='item',attrs={'jid':i[0],'node':i[1],'name':i[2]}))
                iq = request.buildReply('result')
                if request.getQuerynode(): iq.setQuerynode(request.getQuerynode())
                iq.setQueryPayload(list)
                conn.send(iq)
            else:
                conn.send(Error(request,ERR_ITEM_NOT_FOUND))
            raise NodeProcessed
        elif typ == 'info':
            return {'ids':[{'category':'automation','type':'command-list'}],'features':[]}

    def addCommand(self,name,cmddisco,cmdexecute,jid=''):
        """The method to call if adding a new command to the session, the requred parameters of cmddisco and cmdexecute are the methods to enable that command to be executed"""
        # This command takes a command object and the name of the command for registration
        # We must:
        #   Add item into disco
        #   Add item into command list
        if not self._handlers.has_key(jid):
            self._handlers[jid]={}
            self._browser.setDiscoHandler(self._DiscoHandler,node=NS_COMMANDS,jid=jid)
        if self._handlers[jid].has_key(name):
            raise NameError,'Command Exists'
        else:
            self._handlers[jid][name]={'disco':cmddisco,'execute':cmdexecute}
        # Need to add disco stuff here
        self._browser.setDiscoHandler(cmddisco,node=name,jid=jid)

    def delCommand(self,name,jid=''):
        """Removed command from the session"""
        # This command takes a command object and the name used for registration
        # We must:
        #   Remove item from disco
        #   Remove item from command list
        if not self._handlers.has_key(jid):
            raise NameError,'Jid not found'
        if not self._handlers[jid].has_key(name):
            raise NameError, 'Command not found'
        else:
            #Do disco removal here
            command = self.getCommand(name,jid)['disco']
            del self._handlers[jid][name]
            self._browser.delDiscoHandler(command,node=name,jid=jid)

    def getCommand(self,name,jid=''):
        """Returns the command tuple"""
        # This gets the command object with name
        # We must:
        #   Return item that matches this name
        if not self._handlers.has_key(jid):
            raise NameError,'Jid not found'
        elif not self._handlers[jid].has_key(name):
            raise NameError,'Command not found'
        else:
            return self._handlers[jid][name]

class Command_Handler_Prototype(PlugIn):
    """This is a prototype command handler, as each command uses a disco method 
       and execute method you can implement it any way you like, however this is 
       my first attempt at making a generic handler that you can hang process 
       stages on too. There is an example command below.

    The parameters are as follows:
    name : the name of the command within the jabber environment
    description : the natural language description
    discofeatures : the features supported by the command
    initial : the initial command in the from of {'execute':commandname}
    
    All stages set the 'actions' dictionary for each session to represent the possible options available.
    """
    name = 'examplecommand'
    count = 0
    description = 'an example command'
    discofeatures = [NS_COMMANDS,NS_DATA]
    # This is the command template
    def __init__(self,jid=''):
        """Set up the class"""
        PlugIn.__init__(self)
        DBG_LINE='command'
        self.sessioncount = 0
        self.sessions = {}
        # Disco information for command list pre-formatted as a tuple
        self.discoinfo = {'ids':[{'category':'automation','type':'command-node','name':self.description}],'features': self.discofeatures}
        self._jid = jid

    def plugin(self,owner):
        """Plug command into the commands class"""
        # The owner in this instance is the Command Processor
        self._commands = owner
        self._owner = owner._owner
        self._commands.addCommand(self.name,self._DiscoHandler,self.Execute,jid=self._jid)

    def plugout(self):
        """Remove command from the commands class"""
        self._commands.delCommand(self.name,self._jid)

    def getSessionID(self):
        """Returns an id for the command session"""
        self.count = self.count+1
        return 'cmd-%s-%d'%(self.name,self.count)

    def Execute(self,conn,request):
        """The method that handles all the commands, and routes them to the correct method for that stage."""
        # New request or old?
        try:
            session = request.getTagAttr('command','sessionid')
        except:
            session = None
        try:
            action = request.getTagAttr('command','action')
        except:
            action = None
        if action == None: action = 'execute'
        # Check session is in session list
        if self.sessions.has_key(session):
            if self.sessions[session]['jid']==request.getFrom():
                # Check action is vaild
                if self.sessions[session]['actions'].has_key(action):
                    # Execute next action
                    self.sessions[session]['actions'][action](conn,request)
                else:
                    # Stage not presented as an option
                    self._owner.send(Error(request,ERR_BAD_REQUEST))
                    raise NodeProcessed
            else:
                # Jid and session don't match. Go away imposter
                self._owner.send(Error(request,ERR_BAD_REQUEST))
                raise NodeProcessed
        elif session != None:
            # Not on this sessionid you won't.
            self._owner.send(Error(request,ERR_BAD_REQUEST))
            raise NodeProcessed
        else:
            # New session
            self.initial[action](conn,request)

    def _DiscoHandler(self,conn,request,type):
        """The handler for discovery events"""
        if type == 'list':
            return (request.getTo(),self.name,self.description)
        elif type == 'items':
            return []
        elif type == 'info':
            return self.discoinfo

class TestCommand(Command_Handler_Prototype):
    """ Example class. You should read source if you wish to understate how it works. 
        Generally, it presents a "master" that giudes user through to calculate something.
    """
    name = 'testcommand'
    description = 'a noddy example command'
    def __init__(self,jid=''):
        """ Init internal constants. """
        Command_Handler_Prototype.__init__(self,jid)
        self.initial = {'execute':self.cmdFirstStage}
    
    def cmdFirstStage(self,conn,request):
        """ Determine """
        # This is the only place this should be repeated as all other stages should have SessionIDs
        try:
            session = request.getTagAttr('command','sessionid')
        except:
            session = None
        if session == None:
            session = self.getSessionID()
            self.sessions[session]={'jid':request.getFrom(),'actions':{'cancel':self.cmdCancel,'next':self.cmdSecondStage,'execute':self.cmdSecondStage},'data':{'type':None}}
        # As this is the first stage we only send a form
        reply = request.buildReply('result')
        form = DataForm(title='Select type of operation',data=['Use the combobox to select the type of calculation you would like to do, then click Next',DataField(name='calctype',desc='Calculation Type',value=self.sessions[session]['data']['type'],options=[['circlediameter','Calculate the Diameter of a circle'],['circlearea','Calculate the area of a circle']],typ='list-single',required=1)])
        replypayload = [Node('actions',attrs={'execute':'next'},payload=[Node('next')]),form]
        reply.addChild(name='command',namespace=NS_COMMANDS,attrs={'node':request.getTagAttr('command','node'),'sessionid':session,'status':'executing'},payload=replypayload)
        self._owner.send(reply)
        raise NodeProcessed

    def cmdSecondStage(self,conn,request):
        form = DataForm(node = request.getTag(name='command').getTag(name='x',namespace=NS_DATA))
        self.sessions[request.getTagAttr('command','sessionid')]['data']['type']=form.getField('calctype').getValue()
        self.sessions[request.getTagAttr('command','sessionid')]['actions']={'cancel':self.cmdCancel,None:self.cmdThirdStage,'previous':self.cmdFirstStage,'execute':self.cmdThirdStage,'next':self.cmdThirdStage}
        # The form generation is split out to another method as it may be called by cmdThirdStage
        self.cmdSecondStageReply(conn,request)

    def cmdSecondStageReply(self,conn,request):
        reply = request.buildReply('result')
        form = DataForm(title = 'Enter the radius', data=['Enter the radius of the circle (numbers only)',DataField(desc='Radius',name='radius',typ='text-single')])
        replypayload = [Node('actions',attrs={'execute':'complete'},payload=[Node('complete'),Node('prev')]),form]
        reply.addChild(name='command',namespace=NS_COMMANDS,attrs={'node':request.getTagAttr('command','node'),'sessionid':request.getTagAttr('command','sessionid'),'status':'executing'},payload=replypayload)
        self._owner.send(reply)
        raise NodeProcessed

    def cmdThirdStage(self,conn,request):
        form = DataForm(node = request.getTag(name='command').getTag(name='x',namespace=NS_DATA))
        try:
            num = float(form.getField('radius').getValue())
        except:
            self.cmdSecondStageReply(conn,request)
        from math import pi
        if self.sessions[request.getTagAttr('command','sessionid')]['data']['type'] == 'circlearea':
            result = (num**2)*pi
        else:
            result = num*2*pi
        reply = request.buildReply('result')
        form = DataForm(typ='result',data=[DataField(desc='result',name='result',value=result)])
        reply.addChild(name='command',namespace=NS_COMMANDS,attrs={'node':request.getTagAttr('command','node'),'sessionid':request.getTagAttr('command','sessionid'),'status':'completed'},payload=[form])
        self._owner.send(reply)
        raise NodeProcessed

    def cmdCancel(self,conn,request):
        reply = request.buildReply('result')
        reply.addChild(name='command',namespace=NS_COMMANDS,attrs={'node':request.getTagAttr('command','node'),'sessionid':request.getTagAttr('command','sessionid'),'status':'cancelled'})
        self._owner.send(reply)
        del self.sessions[request.getTagAttr('command','sessionid')]
