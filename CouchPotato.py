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
    print base_path
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

lib_dir = os.path.join(base_path, 'libs')

sys.path.insert(0, base_path)
sys.path.insert(0, lib_dir)

# Get options via arg
from couchpotato.runner import getOptions
from couchpotato.runner import runCouchPotato


class TaskBarIcon(wx.TaskBarIcon):

    TBMENU_OPEN = wx.NewId()
    TBMENU_SETTINGS = wx.NewId()
    TBMENU_ABOUT = wx.ID_ABOUT
    TBMENU_EXIT = wx.ID_EXIT

    def __init__(self, frame):
        wx.TaskBarIcon.__init__(self)
        self.frame = frame

        icon = wx.Icon('icon.ico', wx.BITMAP_TYPE_ANY)
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
        self._desktop = desktop

        self.start()

    def run(self):

        args = ['--nogit', '--console_log']#, '--quiet']
        options = getOptions(base_path, args)

        try:
            runCouchPotato(options, base_path, args, desktop = self._desktop)
        except KeyboardInterrupt, e:
            raise
        except Exception, e:
            raise
        finally:
            pass


class CouchPotatoApp(wx.App, SoftwareUpdate):

    settings = {}
    events = {}
    restart = False

    def OnInit(self):

        # Updater
        base_url = 'http://couchpotatoapp.com/updates/'
        self.InitUpdates(base_url, base_url + 'changelog.txt',
                         icon = wx.Icon('icon.ico'))

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


if __name__ == '__main__':
    app = CouchPotatoApp(redirect = False)
    app.MainLoop()

    #path = os.path.join(sys.path[0].decode(sys.getfilesystemencoding()), sys.argv[0])
    #if app.restart:
    #    wx.Process.Open(sys.executable + ' ' + path)
