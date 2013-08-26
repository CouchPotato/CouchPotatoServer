# Add any imports needed for your script.
import sys
import os
import shutil
import datetime
import time

from couchpotato.core.logger import CPLog

log = CPLog(__name__)

def process(group):
    log.info('started external script: Template')
    # Log anything in your script, to CouchPotato's log using
    # log.error
    # log.warning
    # log.info
    # log.debug

    # The following information is passed into this script from couchpotato. 
    # group['library']
    # group['files']
    # group['meta_data']
    # group['files']

    # do stuff here:

    log.info('processing has completed for scrirt: Template')    

    # Any changes you made to the "group" data needs to be written back into group and returned to the renamer.

    return group
