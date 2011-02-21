import os
import string

if os.name == 'nt':
    import win32file

class FileBrowser():

    def __init__(self, path = '/'):
        self.path = path

    def getDirectories(self):

        # Return driveletters or root if path is empty
        if self.path == '/' or not self.path:
            if os.name == 'nt':
                return self.getDriveLetters()
            self.path = '/'

        dirs = []
        for f in os.listdir(self.path):
            path = os.path.join(self.path, f)
            if(os.path.isdir(path)):
                dirs.append(path)

        return dirs

    def getFiles(self):
        pass

    def getDriveLetters(self):

        driveletters = []
        for drive in string.ascii_uppercase:
            if win32file.GetDriveType(drive + ":") == win32file.DRIVE_FIXED:
                driveletters.append(drive + ":")

        return driveletters
