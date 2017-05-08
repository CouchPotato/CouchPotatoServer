from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from email.mime.text import MIMEText
import traceback
import smtplib

log = CPLog(__name__)


class Email(Notification):

    def notify(self, message = '', data = {}, listener = None):
        if self.isDisabled(): return

        # Extract all the settings from the database
        from_address = self.conf('from')
        to = self.conf('to')
        smtp_server = self.conf('smtp_server')
        ssl = self.conf('ssl')
        smtp_user = self.conf('smtp_user')
        smtp_pass = self.conf('smtp_pass')
        
        # Make the basic message
        message = MIMEText(toUnicode(message))
        message['Subject'] = self.conf('subject')
        message['From'] = from_address
        message['To'] = to
        
        try:
            # Open the SMTP connection, via SSL if requested
            if ssl == 1:
                mailserver = smtplib.SMTP_SSL(smtp_server)
            else:
                mailserver = smtplib.SMTP(smtp_server)

            
            # Check too see if an login attempt should be attempted
            if len(smtp_user) > 0:
                mailserver.login(smtp_user, smtp_pass)
            
            # Send the e-mail
            mailserver.sendmail(from_address, to, message.as_string())
            
            # Close the SMTP connection
            mailserver.quit()
            log.info('Email notifications sent.')
            return True
        except:
            log.error('E-mail failed: %s', traceback.format_exc())
            return False
        
        return False
