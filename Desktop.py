from threading import Thread
from wx.lib.softwareupdate import SoftwareUpdate
import os
import sys
import webbrowser
import wx


# Include proper dirs
if hasattr(sys, 'frozen'):
    import libs
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(libs.__file__)))
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

lib_dir = os.path.join(base_path, 'libs')

sys.path.insert(0, base_path)
sys.path.insert(0, lib_dir)

from couchpotato.environment import Env

class TaskBarIcon(wx.TaskBarIcon):

    TBMENU_OPEN = wx.NewId()
    TBMENU_SETTINGS = wx.NewId()
    TBMENU_ABOUT = wx.ID_ABOUT
    TBMENU_EXIT = wx.ID_EXIT

    def __init__(self, frame):
        wx.TaskBarIcon.__init__(self)
        self.frame = frame

        icon = wx.Icon('icon.png', wx.BITMAP_TYPE_PNG)
        self.SetIcon(icon)

        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.onTaskBarActivate)

        self.Bind(wx.EVT_MENU, self.onOpen, id = self.TBMENU_OPEN)
        self.Bind(wx.EVT_MENU, self.onSettings, id = self.TBMENU_SETTINGS)
        self.Bind(wx.EVT_MENU, self.onAbout, id = self.TBMENU_ABOUT)
        self.Bind(wx.EVT_MENU, self.onTaskBarClose, id = self.TBMENU_EXIT)


    def CreatePopupMenu(self):
        menu = wx.Menu()
        menu.Append(self.TBMENU_OPEN, "Open")
        menu.Append(self.TBMENU_SETTINGS, "Settings")
        menu.Append(self.TBMENU_ABOUT, "About")
        menu.Append(self.TBMENU_EXIT, "Close")
        return menu

    def onOpen(self, event):
        url = self.frame.parent.getSetting('base_url')
        webbrowser.open(url)

    def onSettings(self, event):
        url = self.frame.parent.getSetting('base_url') + '/settings/'
        webbrowser.open(url)

    def onAbout(self, event):
        print 'onAbout'

    def onTaskBarActivate(self, evt):
        if not self.frame.IsShown():
            self.frame.Show(True)
        self.frame.Raise()

    def onTaskBarClose(self, evt):
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
        wx.Frame.__init__(self, None)

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
        args = ['--nogit', '--console_log']
        self.options = getOptions(base_path, args)

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


class CouchPotatoApp(wx.App, SoftwareUpdate):

    settings = {}
    events = {}
    restart = False

    def OnInit(self):

        # Updater
        base_url = 'http://couchpota.to/updates/'
        self.InitUpdates(base_url, base_url + 'changelog.html',
                         icon = wx.Icon('icon.png'))

        self.frame = MainFrame(self)
        self.frame.Bind(wx.EVT_CLOSE, self.onClose)

        # CouchPotato thread
        self.worker = WorkerThread(self)

        return True

    def setSettings(self, settings = {}):
        self.settings = settings

    def getSetting(self, name):
        return self.settings.get(name)

    def addEvents(self, events = {}):
        for name in events.iterkeys():
            self.events[name] = events[name]

    def onClose(self, event):

        onClose = self.events.get('onClose')
        if self.events.get('onClose'):
            onClose(event)
        else:
            self.afterShutdown()

    def afterShutdown(self, restart = False):
        self.frame.Destroy()
        self.restart = restart

        self.ExitMainLoop()


if __name__ == '__main__':
    app = CouchPotatoApp(redirect = False)
    app.MainLoop()

    path = os.path.join(sys.path[0].decode(sys.getfilesystemencoding()), sys.argv[0])
    if app.restart:
        pass
        #wx.Process.Open(path)
