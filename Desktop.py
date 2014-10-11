from esky.util import appdir_from_executable #@UnresolvedImport
from threading import Thread
from version import VERSION
from wx.lib.softwareupdate import SoftwareUpdate
import os
import sys
import time
import webbrowser
import wx

# Include proper dirs
if hasattr(sys, 'frozen'):
    import libs
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(libs.__file__)))
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

def icon():
    icon = 'icon_windows.png'
    if os.path.isfile('icon_mac.png'):
        icon = 'icon_mac.png'

    return wx.Icon(icon, wx.BITMAP_TYPE_PNG)

lib_dir = os.path.join(base_path, 'libs')

sys.path.insert(0, base_path)
sys.path.insert(0, lib_dir)

from couchpotato.environment import Env

class TaskBarIcon(wx.TaskBarIcon):

    TBMENU_OPEN = wx.NewId()
    TBMENU_SETTINGS = wx.NewId()
    TBMENU_EXIT = wx.ID_EXIT

    closed = False
    menu = False
    enabled = False

    def __init__(self, frame):
        wx.TaskBarIcon.__init__(self)
        self.frame = frame

        self.SetIcon(icon())

        self.Bind(wx.EVT_TASKBAR_LEFT_UP, self.OnTaskBarClick)
        self.Bind(wx.EVT_TASKBAR_RIGHT_UP, self.OnTaskBarClick)

        self.Bind(wx.EVT_MENU, self.onOpen, id = self.TBMENU_OPEN)
        self.Bind(wx.EVT_MENU, self.onSettings, id = self.TBMENU_SETTINGS)
        self.Bind(wx.EVT_MENU, self.onTaskBarClose, id = self.TBMENU_EXIT)

    def OnTaskBarClick(self, evt):
        menu = self.CreatePopupMenu()
        self.PopupMenu(menu)
        menu.Destroy()

    def enable(self):
        self.enabled = True

        if self.menu:
            self.open_menu.Enable(True)
            self.setting_menu.Enable(True)

            self.open_menu.SetText('Open')

    def CreatePopupMenu(self):

        if not self.menu:
            self.menu = wx.Menu()
            self.open_menu = self.menu.Append(self.TBMENU_OPEN, 'Open')
            self.setting_menu = self.menu.Append(self.TBMENU_SETTINGS, 'About')
            self.exit_menu = self.menu.Append(self.TBMENU_EXIT, 'Quit')

            if not self.enabled:
                self.open_menu.Enable(False)
                self.setting_menu.Enable(False)

                self.open_menu.SetText('Loading...')

        return self.menu

    def onOpen(self, event):
        url = self.frame.parent.getSetting('base_url')
        webbrowser.open(url)

    def onSettings(self, event):
        url = self.frame.parent.getSetting('base_url') + 'settings/about/'
        webbrowser.open(url)

    def onTaskBarClose(self, evt):
        if self.closed:
            return

        self.closed = True

        self.RemoveIcon()
        wx.CallAfter(self.frame.Close)


    def makeIcon(self, img):
        if "wxMSW" in wx.PlatformInfo:
            img = img.Scale(16, 16)
        elif "wxGTK" in wx.PlatformInfo:
            img = img.Scale(22, 22)

        icon = wx.IconFromBitmap(img.CopyFromBitmap())
        return icon


class MainFrame(wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__(self, None, style = wx.FRAME_NO_TASKBAR)

        self.parent = parent
        self.tbicon = TaskBarIcon(self)


class WorkerThread(Thread):

    def __init__(self, desktop):
        Thread.__init__(self)
        self.daemon = True
        self._desktop = desktop

        self.start()

    def run(self):

        # Get options via arg
        from couchpotato.runner import getOptions
        args = ['--quiet']
        self.options = getOptions(args)

        # Load settings
        settings = Env.get('settings')
        settings.setFile(self.options.config_file)

        # Create data dir if needed
        self.data_dir = os.path.expanduser(Env.setting('data_dir'))
        if self.data_dir == '':
            from couchpotato.core.helpers.variable import getDataDir
            self.data_dir = getDataDir()

        if not os.path.isdir(self.data_dir):
            os.makedirs(self.data_dir)

        # Create logging dir
        self.log_dir = os.path.join(self.data_dir, 'logs');
        if not os.path.isdir(self.log_dir):
            os.mkdir(self.log_dir)

        try:
            from couchpotato.runner import runCouchPotato
            runCouchPotato(self.options, base_path, args, data_dir = self.data_dir, log_dir = self.log_dir, Env = Env, desktop = self._desktop)
        except:
            pass

        self._desktop.frame.Close()
        self._desktop.ExitMainLoop()


class CouchPotatoApp(wx.App, SoftwareUpdate):

    settings = {}
    events = {}
    restart = False
    closing = False
    triggered_onClose = False

    def OnInit(self):

        # Updater
        base_url = 'https://api.couchpota.to/updates/%s'
        self.InitUpdates(base_url % VERSION + '/', 'https://couchpota.to/updates/%s' % 'changelog.html',
                         icon = icon())

        self.frame = MainFrame(self)
        self.frame.Bind(wx.EVT_CLOSE, self.onClose)

        # CouchPotato thread
        self.worker = WorkerThread(self)

        return True

    def onAppLoad(self):
        self.frame.tbicon.enable()

    def setSettings(self, settings = {}):
        self.settings = settings

    def getSetting(self, name):
        return self.settings.get(name)

    def addEvents(self, events = {}):
        for name in events.iterkeys():
            self.events[name] = events[name]

    def onClose(self, event):

        if not self.closing:
            self.closing = True
            self.frame.tbicon.onTaskBarClose(event)

        onClose = self.events.get('onClose')
        if onClose and not self.triggered_onClose:
            self.triggered_onClose = True
            onClose(event)

    def afterShutdown(self, restart = False):
        self.frame.Destroy()
        self.restart = restart
        self.ExitMainLoop()


if __name__ == '__main__':

    app = CouchPotatoApp(redirect = False)
    app.MainLoop()

    time.sleep(1)

    if app.restart:

        def appexe_from_executable(exepath):
            appdir = appdir_from_executable(exepath)
            exename = os.path.basename(exepath)

            if sys.platform == "darwin":
                if os.path.isdir(os.path.join(appdir, "Contents", "MacOS")):
                    return os.path.join(appdir, "Contents", "MacOS", exename)

            return os.path.join(appdir, exename)

        exe = appexe_from_executable(sys.executable)
        os.chdir(os.path.dirname(exe))

        os.execv(exe, [exe] + sys.argv[1:])
