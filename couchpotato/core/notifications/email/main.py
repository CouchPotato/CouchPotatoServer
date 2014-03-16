from couchpotato.core.helpers.encoding import toUnicode
from couchpotato.core.helpers.variable import splitString
from couchpotato.core.logger import CPLog
from couchpotato.core.notifications.base import Notification
from couchpotato.environment import Env
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
import smtplib
import traceback

log = CPLog(__name__)


class Email(Notification):

    def notify(self, message = '', data = None, listener = None):
        if not data: data = {}

        # Extract all the settings from settings
        from_address = self.conf('from')
        to_address = self.conf('to')
        ssl = self.conf('ssl')
        smtp_server = self.conf('smtp_server')
        smtp_user = self.conf('smtp_user')
        smtp_pass = self.conf('smtp_pass')
        smtp_port = self.conf('smtp_port')
        starttls = self.conf('starttls')

        # Make the basic message
        message = MIMEText(toUnicode(message), _charset = Env.get('encoding'))
        message['Subject'] = self.default_title
        message['From'] = from_address
        message['To'] = to_address
        message['Date'] = formatdate(localtime = 1)
        message['Message-ID'] = make_msgid()

        try:
            # Open the SMTP connection, via SSL if requested
            log.debug("Connecting to host %s on port %s" % (smtp_server, smtp_port))
            log.debug("SMTP over SSL %s", ("enabled" if ssl == 1 else "disabled"))
            mailserver = smtplib.SMTP_SSL(smtp_server) if ssl == 1 else smtplib.SMTP(smtp_server)

            if starttls:
                log.debug("Using StartTLS to initiate the connection with the SMTP server")
                mailserver.starttls()

            # Say hello to the server
            mailserver.ehlo()

            # Check too see if an login attempt should be attempted
            if len(smtp_user) > 0:
                log.debug("Logging on to SMTP server using username \'%s\'%s", (smtp_user, " and a password" if len(smtp_pass) > 0 else ""))
                mailserver.login(smtp_user, smtp_pass)

            # Send the e-mail
            log.debug("Sending the email")
            mailserver.sendmail(from_address, splitString(to_address), message.as_string())

            # Close the SMTP connection
            mailserver.quit()

            log.info('Email notification sent')

            return True
        except:
            log.error('E-mail failed: %s', traceback.format_exc())

        return False
