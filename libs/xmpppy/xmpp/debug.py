##   debug.py 
##
##   Copyright (C) 2003 Jacob Lundqvist
##
##   This program is free software; you can redistribute it and/or modify
##   it under the terms of the GNU Lesser General Public License as published
##   by the Free Software Foundation; either version 2, or (at your option)
##   any later version.
##
##   This program is distributed in the hope that it will be useful,
##   but WITHOUT ANY WARRANTY; without even the implied warranty of
##   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##   GNU Lesser General Public License for more details.

_version_ = '1.4.0'

"""\

Generic debug class

Other modules can always define extra debug flags for local usage, as long as
they make sure they append them to debug_flags

Also its always a good thing to prefix local flags with something, to reduce risk
of coliding flags. Nothing breaks if two flags would be identical, but it might 
activate unintended debugging.

flags can be numeric, but that makes analysing harder, on creation its
not obvious what is activated, and when flag_show is given, output isnt
really meaningfull.

This Debug class can either be initialized and used on app level, or used independantly
by the individual classes.

For samples of usage, see samples subdir in distro source, and selftest
in this code
    
"""



import sys
import traceback
import time
import os

import types

if os.environ.has_key('TERM'):
    colors_enabled=True
else:
    colors_enabled=False

color_none         = chr(27) + "[0m"
color_black        = chr(27) + "[30m"
color_red          = chr(27) + "[31m"
color_green        = chr(27) + "[32m"
color_brown        = chr(27) + "[33m"
color_blue         = chr(27) + "[34m"
color_magenta      = chr(27) + "[35m"
color_cyan         = chr(27) + "[36m"
color_light_gray   = chr(27) + "[37m"
color_dark_gray    = chr(27) + "[30;1m"
color_bright_red   = chr(27) + "[31;1m"
color_bright_green = chr(27) + "[32;1m"
color_yellow       = chr(27) + "[33;1m"
color_bright_blue  = chr(27) + "[34;1m"
color_purple       = chr(27) + "[35;1m"
color_bright_cyan  = chr(27) + "[36;1m"
color_white        = chr(27) + "[37;1m"


"""
Define your flags in yor modules like this:

from debug import *

DBG_INIT = 'init'                ; debug_flags.append( DBG_INIT )
DBG_CONNECTION = 'connection'    ; debug_flags.append( DBG_CONNECTION )

 The reason for having a double statement wis so we can validate params
 and catch all undefined debug flags
 
 This gives us control over all used flags, and makes it easier to allow
 global debugging in your code, just do something like
 
 foo = Debug( debug_flags )
 
 group flags, that is a flag in it self containing multiple flags should be
 defined without the debug_flags.append() sequence, since the parts are already
 in the list, also they must of course be defined after the flags they depend on ;)
 example:

DBG_MULTI = [ DBG_INIT, DBG_CONNECTION ]



  NoDebug
  -------
  To speed code up, typically for product releases or such
  use this class instead if you globaly want to disable debugging
"""


class NoDebug:
    def __init__( self, *args, **kwargs ):
        self.debug_flags = []
    def show( self,  *args, **kwargs):
        pass
    def Show( self,  *args, **kwargs):
        pass
    def is_active( self, flag ):
        pass
    colors={}
    def active_set( self, active_flags = None ):
        return 0
    

LINE_FEED = '\n'


class Debug:      
    def __init__( self,
                  #
                  # active_flags are those that will trigger output
                  #
                  active_flags = None,
                  #
                  # Log file should be file object or file namne
                  #
                  log_file = sys.stderr,
                  #
                  # prefix and sufix can either be set globaly or per call.
                  # personally I use this to color code debug statements
                  # with prefix = chr(27) + '[34m'
                  #      sufix = chr(27) + '[37;1m\n'
                  #
                  prefix = 'DEBUG: ',
                  sufix = '\n',
                  #
                  # If you want unix style timestamps, 
                  #  0 disables timestamps
                  #  1 before prefix, good when prefix is a string
                  #  2 after prefix, good when prefix is a color
                  #
                  time_stamp = 0,
                  #
                  # flag_show should normaly be of, but can be turned on to get a
                  # good view of what flags are actually used for calls,
                  # if it is not None, it should be a string
                  # flags for current call will be displayed 
                  # with flag_show as separator                  
                  # recomended values vould be '-' or ':', but any string goes
                  #
                  flag_show = None,
                  #
                  # If you dont want to validate flags on each call to
                  # show(), set this to 0
                  #
                  validate_flags = 1,
                  #
                  # If you dont want the welcome message, set to 0
                  # default is to show welcome if any flags are active
                  welcome = -1
                  ):
        
        self.debug_flags = []
        if welcome == -1:
            if active_flags and len(active_flags):
                welcome = 1
            else:
                welcome = 0
            
        self._remove_dupe_flags()
        if log_file:
            if type( log_file ) is type(''):
                try:
                    self._fh = open(log_file,'w')
                except:
                    print 'ERROR: can open %s for writing'
                    sys.exit(0)
            else: ## assume its a stream type object
                self._fh = log_file
        else:
            self._fh = sys.stdout
         
        if time_stamp not in (0,1,2):
            msg2 = '%s' % time_stamp
            raise 'Invalid time_stamp param', msg2
        self.prefix = prefix
        self.sufix = sufix
        self.time_stamp = time_stamp
        self.flag_show = None # must be initialised after possible welcome
        self.validate_flags = validate_flags

        self.active_set( active_flags )
        if welcome:
            self.show('')
            caller = sys._getframe(1) # used to get name of caller
            try:
                mod_name= ":%s" % caller.f_locals['__name__']
            except:
                mod_name = ""
            self.show('Debug created for %s%s' % (caller.f_code.co_filename,
                                                   mod_name ))
            self.show(' flags defined: %s' % ','.join( self.active ))
            
        if type(flag_show) in (type(''), type(None)):
            self.flag_show = flag_show
        else:
            msg2 = '%s' % type(flag_show )
            raise 'Invalid type for flag_show!', msg2


        


    def show( self, msg, flag = None, prefix = None, sufix = None,
              lf = 0 ):
        """
        flag can be of folowing types:
            None - this msg will always be shown if any debugging is on
            flag - will be shown if flag is active
            (flag1,flag2,,,) - will be shown if any of the given flags 
                               are active

        if prefix / sufix are not given, default ones from init will be used
        
        lf = -1 means strip linefeed if pressent
        lf = 1 means add linefeed if not pressent
        """
        
        if self.validate_flags:
            self._validate_flag( flag )
            
        if not self.is_active(flag):
            return
        if prefix:
            pre = prefix
        else:
            pre = self.prefix
        if sufix:
            suf = sufix
        else:
            suf = self.sufix

        if self.time_stamp == 2:
            output = '%s%s ' % ( pre,
                                 time.strftime('%b %d %H:%M:%S',
                                 time.localtime(time.time() )),
                                 )
        elif self.time_stamp == 1:
            output = '%s %s' % ( time.strftime('%b %d %H:%M:%S',
                                 time.localtime(time.time() )),
                                 pre,
                                 )
        else:
            output = pre
            
        if self.flag_show:
            if flag:
                output = '%s%s%s' % ( output, flag, self.flag_show )
            else:
                # this call uses the global default,
                # dont print "None", just show the separator
                output = '%s %s' % ( output, self.flag_show )

        output = '%s%s%s' % ( output, msg, suf )
        if lf:
            # strip/add lf if needed
            last_char = output[-1]
            if lf == 1 and last_char != LINE_FEED:
                output = output + LINE_FEED
            elif lf == -1 and last_char == LINE_FEED:
                output = output[:-1]
        try:
            self._fh.write( output )
        except:
            # unicode strikes again ;)
            s=u''
            for i in range(len(output)):
                if ord(output[i]) < 128:
                    c = output[i]
                else:
                    c = '?'
                s=s+c
            self._fh.write( '%s%s%s' % ( pre, s, suf ))
        self._fh.flush()
            
                
    def is_active( self, flag ):
        'If given flag(s) should generate output.'

        # try to abort early to quicken code
        if not self.active:
            return 0
        if not flag or flag in self.active:
            return 1
        else:
            # check for multi flag type:
            if type( flag ) in ( type(()), type([]) ):
                for s in flag:
                    if s in self.active:
                        return 1
        return 0

    
    def active_set( self, active_flags = None ):
        "returns 1 if any flags where actually set, otherwise 0."
        r = 0
        ok_flags = []
        if not active_flags:
            #no debuging at all
            self.active = []
        elif type( active_flags ) in ( types.TupleType, types.ListType ):
            flags = self._as_one_list( active_flags )
            for t in flags:
                if t not in self.debug_flags:
                    sys.stderr.write('Invalid debugflag given: %s\n' % t )
                ok_flags.append( t )
                
            self.active = ok_flags
            r = 1
        else:
            # assume comma string
            try:
                flags = active_flags.split(',')
            except:
                self.show( '***' )
                self.show( '*** Invalid debug param given: %s' % active_flags )
                self.show( '*** please correct your param!' )
                self.show( '*** due to this, full debuging is enabled' )
                self.active = self.debug_flags
            
            for f in flags:
                s = f.strip()
                ok_flags.append( s )
            self.active = ok_flags

        self._remove_dupe_flags()
        return r
    
    def active_get( self ):
        "returns currently active flags."
        return self.active
    
    
    def _as_one_list( self, items ):
        """ init param might contain nested lists, typically from group flags.
        
        This code organises lst and remves dupes
        """
        if type( items ) <> type( [] ) and type( items ) <> type( () ):
            return [ items ]
        r = []
        for l in items:
            if type( l ) == type([]):
                lst2 = self._as_one_list( l )
                for l2 in lst2: 
                    self._append_unique_str(r, l2 )
            elif l == None:
                continue
            else:
                self._append_unique_str(r, l )
        return r
    
    
    def _append_unique_str( self, lst, item ):
        """filter out any dupes."""
        if type(item) <> type(''):
            msg2 = '%s' % item
            raise 'Invalid item type (should be string)',msg2
        if item not in lst:
            lst.append( item )
        return lst

    
    def _validate_flag( self, flags ):
        'verify that flag is defined.'
        if flags:
            for f in self._as_one_list( flags ):
                if not f in self.debug_flags:
                    msg2 = '%s' % f
                    raise 'Invalid debugflag given', msg2

    def _remove_dupe_flags( self ):
        """
        if multiple instances of Debug is used in same app, 
        some flags might be created multiple time, filter out dupes
        """
        unique_flags = []
        for f in self.debug_flags:
            if f not in unique_flags:
                unique_flags.append(f)
        self.debug_flags = unique_flags

    colors={}
    def Show(self, flag, msg, prefix=''):
        msg=msg.replace('\r','\\r').replace('\n','\\n').replace('><','>\n  <')
        if not colors_enabled: pass
        elif self.colors.has_key(prefix): msg=self.colors[prefix]+msg+color_none
        else: msg=color_none+msg
        if not colors_enabled: prefixcolor=''
        elif self.colors.has_key(flag): prefixcolor=self.colors[flag]
        else: prefixcolor=color_none
        
        if prefix=='error':
            _exception = sys.exc_info()
            if _exception[0]:
                msg=msg+'\n'+''.join(traceback.format_exception(_exception[0], _exception[1], _exception[2])).rstrip()
        
        prefix= self.prefix+prefixcolor+(flag+' '*12)[:12]+' '+(prefix+' '*6)[:6]
        self.show(msg, flag, prefix)

    def is_active( self, flag ):
        if not self.active: return 0
        if not flag or flag in self.active and DBG_ALWAYS not in self.active or flag not in self.active and DBG_ALWAYS in self.active : return 1
        return 0

DBG_ALWAYS='always'

##Uncomment this to effectively disable all debugging and all debugging overhead.
#Debug=NoDebug
