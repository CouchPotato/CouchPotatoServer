
# JID Escaping XEP-0106 for the xmpppy based transports written by Norman Rasmussen

"""This file is the XEP-0106 commands.

Implemented commands as follows:

4.2 Encode : Encoding Transformation
4.3 Decode : Decoding Transformation


"""

xep0106mapping = [
	[' ' ,'20'],
	['"' ,'22'],
	['&' ,'26'],
	['\'','27'],
	['/' ,'2f'],
	[':' ,'3a'],
	['<' ,'3c'],
	['>' ,'3e'],
	['@' ,'40']]

def JIDEncode(str):
	str = str.replace('\\5c', '\\5c5c')
	for each in xep0106mapping:
		str = str.replace('\\' + each[1], '\\5c' + each[1])
	for each in xep0106mapping:
		str = str.replace(each[0], '\\' + each[1])
	return str

def JIDDecode(str):
	for each in xep0106mapping:
		str = str.replace('\\' + each[1], each[0])
	return str.replace('\\5c', '\\')

if __name__ == "__main__":
	def test(before,valid):
		during = JIDEncode(before)
		after = JIDDecode(during)
		if during == valid and after == before:
			print 'PASS Before: ' + before
			print 'PASS During: ' + during
		else:
			print 'FAIL Before: ' + before
			print 'FAIL During: ' + during
			print 'FAIL After : ' + after
		print

	test('jid escaping',r'jid\20escaping')
	test(r'\3and\2is\5@example.com',r'\5c3and\2is\5\40example.com')
	test(r'\3catsand\2catsis\5cats@example.com',r'\5c3catsand\2catsis\5c5cats\40example.com')
	test(r'\2plus\2is\4',r'\2plus\2is\4')
	test(r'foo\bar',r'foo\bar')
	test(r'foob\41r',r'foob\41r')
	test('here\'s_a wild_&_/cr%zy/_address@example.com',r'here\27s_a\20wild_\26_\2fcr%zy\2f_address\40example.com')
