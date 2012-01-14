import re
import hashlib
import time

__version__ = '0.5'

#GNTP/<version> <messagetype> <encryptionAlgorithmID>[:<ivValue>][ <keyHashAlgorithmID>:<keyHash>.<salt>]
GNTP_INFO_LINE = re.compile(
	'GNTP/(?P<version>\d+\.\d+) (?P<messagetype>REGISTER|NOTIFY|SUBSCRIBE|\-OK|\-ERROR)' +
	' (?P<encryptionAlgorithmID>[A-Z0-9]+(:(?P<ivValue>[A-F0-9]+))?) ?' +
	'((?P<keyHashAlgorithmID>[A-Z0-9]+):(?P<keyHash>[A-F0-9]+).(?P<salt>[A-F0-9]+))?\r\n',
	re.IGNORECASE
)

GNTP_INFO_LINE_SHORT = re.compile(
	'GNTP/(?P<version>\d+\.\d+) (?P<messagetype>REGISTER|NOTIFY|SUBSCRIBE|\-OK|\-ERROR)',
	re.IGNORECASE
)

GNTP_HEADER = re.compile('([\w-]+):(.+)')

GNTP_EOL = u'\r\n'


class BaseError(Exception):
	def gntp_error(self):
		error = GNTPError(self.errorcode, self.errordesc)
		return error.encode()


class ParseError(BaseError):
	errorcode = 500
	errordesc = 'Error parsing the message'


class AuthError(BaseError):
	errorcode = 400
	errordesc = 'Error with authorization'


class UnsupportedError(BaseError):
	errorcode = 500
	errordesc = 'Currently unsupported by gntp.py'


class _GNTPBase(object):
	"""Base initilization

	:param string messagetype: GNTP Message type
	:param string version: GNTP Protocol version
	:param string encription: Encryption protocol
	"""
	def __init__(self, messagetype=None, version='1.0', encryption=None):
		self.info = {
			'version': version,
			'messagetype': messagetype,
			'encryptionAlgorithmID': encryption
		}
		self.headers = {}
		self.resources = {}

	def __str__(self):
		return self.encode()

	def _parse_info(self, data):
		"""Parse the first line of a GNTP message to get security and other info values

		:param string data: GNTP Message
		:return dict: Parsed GNTP Info line
		"""

		match = GNTP_INFO_LINE.match(data)

		if not match:
			raise ParseError('ERROR_PARSING_INFO_LINE')

		info = match.groupdict()
		if info['encryptionAlgorithmID'] == 'NONE':
			info['encryptionAlgorithmID'] = None

		return info

	def set_password(self, password, encryptAlgo='MD5'):
		"""Set a password for a GNTP Message

		:param string password: Null to clear password
		:param string encryptAlgo: Supports MD5, SHA1, SHA256, SHA512
		"""
		hash = {
			'MD5': hashlib.md5,
			'SHA1': hashlib.sha1,
			'SHA256': hashlib.sha256,
			'SHA512': hashlib.sha512,
		}

		self.password = password
		self.encryptAlgo = encryptAlgo.upper()
		if not password:
			self.info['encryptionAlgorithmID'] = None
			self.info['keyHashAlgorithm'] = None
			return
		if not self.encryptAlgo in hash.keys():
			raise UnsupportedError('INVALID HASH "%s"' % self.encryptAlgo)

		hashfunction = hash.get(self.encryptAlgo)

		password = password.encode('utf8')
		seed = time.ctime()
		salt = hashfunction(seed).hexdigest()
		saltHash = hashfunction(seed).digest()
		keyBasis = password + saltHash
		key = hashfunction(keyBasis).digest()
		keyHash = hashfunction(key).hexdigest()

		self.info['keyHashAlgorithmID'] = self.encryptAlgo
		self.info['keyHash'] = keyHash.upper()
		self.info['salt'] = salt.upper()

	def _decode_hex(self, value):
		"""Helper function to decode hex string to `proper` hex string

		:param string value: Human readable hex string
		:return string: Hex string
		"""
		result = ''
		for i in range(0, len(value), 2):
			tmp = int(value[i:i + 2], 16)
			result += chr(tmp)
		return result

	def _decode_binary(self, rawIdentifier, identifier):
		rawIdentifier += '\r\n\r\n'
		dataLength = int(identifier['Length'])
		pointerStart = self.raw.find(rawIdentifier) + len(rawIdentifier)
		pointerEnd = pointerStart + dataLength
		data = self.raw[pointerStart:pointerEnd]
		if not len(data) == dataLength:
			raise ParseError('INVALID_DATA_LENGTH Expected: %s Recieved %s' % (dataLength, len(data)))
		return data

	def _validate_password(self, password):
		"""Validate GNTP Message against stored password"""
		self.password = password
		if password == None:
			raise AuthError('Missing password')
		keyHash = self.info.get('keyHash', None)
		if keyHash is None and self.password is None:
			return True
		if keyHash is None:
			raise AuthError('Invalid keyHash')
		if self.password is None:
			raise AuthError('Missing password')

		password = self.password.encode('utf8')
		saltHash = self._decode_hex(self.info['salt'])

		keyBasis = password + saltHash
		key = hashlib.md5(keyBasis).digest()
		keyHash = hashlib.md5(key).hexdigest()

		if not keyHash.upper() == self.info['keyHash'].upper():
			raise AuthError('Invalid Hash')
		return True

	def validate(self):
		"""Verify required headers"""
		for header in self._requiredHeaders:
			if not self.headers.get(header, False):
				raise ParseError('Missing Notification Header: ' + header)

	def _format_info(self):
		"""Generate info line for GNTP Message

		:return string:
		"""
		info = u'GNTP/%s %s' % (
			self.info.get('version'),
			self.info.get('messagetype'),
		)
		if self.info.get('encryptionAlgorithmID', None):
			info += ' %s:%s' % (
				self.info.get('encryptionAlgorithmID'),
				self.info.get('ivValue'),
			)
		else:
			info += ' NONE'

		if self.info.get('keyHashAlgorithmID', None):
			info += ' %s:%s.%s' % (
				self.info.get('keyHashAlgorithmID'),
				self.info.get('keyHash'),
				self.info.get('salt')
			)

		return info

	def _parse_dict(self, data):
		"""Helper function to parse blocks of GNTP headers into a dictionary

		:param string data:
		:return dict:
		"""
		dict = {}
		for line in data.split('\r\n'):
			match = GNTP_HEADER.match(line)
			if not match:
				continue

			key = match.group(1).strip()
			val = match.group(2).strip()
			dict[key] = val
		return dict

	def add_header(self, key, value):
		if isinstance(value, unicode):
			self.headers[key] = value
		else:
			self.headers[key] = unicode('%s' % value, 'utf8', 'replace')

	def decode(self, data, password=None):
		"""Decode GNTP Message

		:param string data:
		"""
		self.password = password
		self.raw = data
		parts = self.raw.split('\r\n\r\n')
		self.info = self._parse_info(data)
		self.headers = self._parse_dict(parts[0])

	def encode(self):
		"""Encode a GNTP Message

		:return string: Encoded GNTP Message ready to be sent
		"""
		self.validate()

		message = self._format_info() + GNTP_EOL
		#Headers
		for k, v in self.headers.iteritems():
			message += u'%s: %s%s' % (k, v, GNTP_EOL)

		message += GNTP_EOL
		return message


class GNTPRegister(_GNTPBase):
	"""Represents a GNTP Registration Command

	:param string data: (Optional) See decode()
	:param string password: (Optional) Password to use while encoding/decoding messages
	"""
	_requiredHeaders = [
		'Application-Name',
		'Notifications-Count'
	]
	_requiredNotificationHeaders = ['Notification-Name']

	def __init__(self, data=None, password=None):
		_GNTPBase.__init__(self, 'REGISTER')
		self.notifications = []

		if data:
			self.decode(data, password)
		else:
			self.set_password(password)
			self.add_header('Application-Name', 'pygntp')
			self.add_header('Notifications-Count', 0)

	def validate(self):
		'''Validate required headers and validate notification headers'''
		for header in self._requiredHeaders:
			if not self.headers.get(header, False):
				raise ParseError('Missing Registration Header: ' + header)
		for notice in self.notifications:
			for header in self._requiredNotificationHeaders:
				if not notice.get(header, False):
					raise ParseError('Missing Notification Header: ' + header)

	def decode(self, data, password):
		"""Decode existing GNTP Registration message

		:param string data: Message to decode
		"""
		self.raw = data
		parts = self.raw.split('\r\n\r\n')
		self.info = self._parse_info(data)
		self._validate_password(password)
		self.headers = self._parse_dict(parts[0])

		for i, part in enumerate(parts):
			if i == 0:
				continue  # Skip Header
			if part.strip() == '':
				continue
			notice = self._parse_dict(part)
			if notice.get('Notification-Name', False):
				self.notifications.append(notice)
			elif notice.get('Identifier', False):
				notice['Data'] = self._decode_binary(part, notice)
				#open('register.png','wblol').write(notice['Data'])
				self.resources[notice.get('Identifier')] = notice

	def add_notification(self, name, enabled=True):
		"""Add new Notification to Registration message

		:param string name: Notification Name
		:param boolean enabled: Enable this notification by default
		"""
		notice = {}
		notice['Notification-Name'] = u'%s' % name
		notice['Notification-Enabled'] = u'%s' % enabled

		self.notifications.append(notice)
		self.add_header('Notifications-Count', len(self.notifications))

	def encode(self):
		"""Encode a GNTP Registration Message

		:return string: Encoded GNTP Registration message
		"""
		self.validate()

		message = self._format_info() + GNTP_EOL
		#Headers
		for k, v in self.headers.iteritems():
			message += u'%s: %s%s' % (k, v, GNTP_EOL)

		#Notifications
		if len(self.notifications) > 0:
			for notice in self.notifications:
				message += GNTP_EOL
				for k, v in notice.iteritems():
					message += u'%s: %s%s' % (k, v, GNTP_EOL)

		message += GNTP_EOL
		return message


class GNTPNotice(_GNTPBase):
	"""Represents a GNTP Notification Command

	:param string data: (Optional) See decode()
	:param string app: (Optional) Set Application-Name
	:param string name: (Optional) Set Notification-Name
	:param string title: (Optional) Set Notification Title
	:param string password: (Optional) Password to use while encoding/decoding messages
	"""
	_requiredHeaders = [
		'Application-Name',
		'Notification-Name',
		'Notification-Title'
	]

	def __init__(self, data=None, app=None, name=None, title=None, password=None):
		_GNTPBase.__init__(self, 'NOTIFY')

		if data:
			self.decode(data, password)
		else:
			self.set_password(password)
			if app:
				self.add_header('Application-Name', app)
			if name:
				self.add_header('Notification-Name', name)
			if title:
				self.add_header('Notification-Title', title)

	def decode(self, data, password):
		"""Decode existing GNTP Notification message

		:param string data: Message to decode.
		"""
		self.raw = data
		parts = self.raw.split('\r\n\r\n')
		self.info = self._parse_info(data)
		self._validate_password(password)
		self.headers = self._parse_dict(parts[0])

		for i, part in enumerate(parts):
			if i == 0:
				continue  # Skip Header
			if part.strip() == '':
				continue
			notice = self._parse_dict(part)
			if notice.get('Identifier', False):
				notice['Data'] = self._decode_binary(part, notice)
				#open('notice.png','wblol').write(notice['Data'])
				self.resources[notice.get('Identifier')] = notice

	def encode(self):
		"""Encode a GNTP Notification Message

		:return string: GNTP Notification Message ready to be sent
		"""
		self.validate()

		message = self._format_info() + GNTP_EOL
		#Headers
		for k, v in self.headers.iteritems():
			message += u'%s: %s%s' % (k, v, GNTP_EOL)

		message += GNTP_EOL
		return message


class GNTPSubscribe(_GNTPBase):
	"""Represents a GNTP Subscribe Command

	:param string data: (Optional) See decode()
	:param string password: (Optional) Password to use while encoding/decoding messages
	"""
	_requiredHeaders = [
		'Subscriber-ID',
		'Subscriber-Name',
	]

	def __init__(self, data=None, password=None):
		_GNTPBase.__init__(self, 'SUBSCRIBE')
		if data:
			self.decode(data, password)
		else:
			self.set_password(password)


class GNTPOK(_GNTPBase):
	"""Represents a GNTP OK Response

	:param string data: (Optional) See _GNTPResponse.decode()
	:param string action: (Optional) Set type of action the OK Response is for
	"""
	_requiredHeaders = ['Response-Action']

	def __init__(self, data=None, action=None):
		_GNTPBase.__init__(self, '-OK')
		if data:
			self.decode(data)
		if action:
			self.add_header('Response-Action', action)


class GNTPError(_GNTPBase):
	"""Represents a GNTP Error response

	:param string data: (Optional) See _GNTPResponse.decode()
	:param string errorcode: (Optional) Error code
	:param string errordesc: (Optional) Error Description
	"""
	_requiredHeaders = ['Error-Code', 'Error-Description']

	def __init__(self, data=None, errorcode=None, errordesc=None):
		_GNTPBase.__init__(self, '-ERROR')
		if data:
			self.decode(data)
		if errorcode:
			self.add_header('Error-Code', errorcode)
			self.add_header('Error-Description', errordesc)

	def error(self):
		return self.headers['Error-Code'], self.headers['Error-Description']


def parse_gntp(data, password=None):
	"""Attempt to parse a message as a GNTP message

	:param string data: Message to be parsed
	:param string password: Optional password to be used to verify the message
	"""
	match = GNTP_INFO_LINE_SHORT.match(data)
	if not match:
		raise ParseError('INVALID_GNTP_INFO')
	info = match.groupdict()
	if info['messagetype'] == 'REGISTER':
		return GNTPRegister(data, password=password)
	elif info['messagetype'] == 'NOTIFY':
		return GNTPNotice(data, password=password)
	elif info['messagetype'] == 'SUBSCRIBE':
		return GNTPSubscribe(data, password=password)
	elif info['messagetype'] == '-OK':
		return GNTPOK(data)
	elif info['messagetype'] == '-ERROR':
		return GNTPError(data)
	raise ParseError('INVALID_GNTP_MESSAGE')
