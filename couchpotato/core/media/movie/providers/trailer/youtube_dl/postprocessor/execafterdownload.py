from __future__ import unicode_literals

import subprocess

from .common import PostProcessor
from ..compat import shlex_quote
from ..utils import PostProcessingError


class ExecAfterDownloadPP(PostProcessor):
    def __init__(self, downloader=None, verboseOutput=None, exec_cmd=None):
        self.verboseOutput = verboseOutput
        self.exec_cmd = exec_cmd

    def run(self, information):
        cmd = self.exec_cmd
        if '{}' not in cmd:
            cmd += ' {}'

        cmd = cmd.replace('{}', shlex_quote(information['filepath']))

        self._downloader.to_screen("[exec] Executing command: %s" % cmd)
        retCode = subprocess.call(cmd, shell=True)
        if retCode != 0:
            raise PostProcessingError(
                'Command returned error code %d' % retCode)

        return None, information  # by default, keep file and do nothing
