from bs4 import BeautifulSoup
from couchpotato.core.media._base.providers.userscript.base import UserscriptBase
import re

autoload = 'Filmstarts'


class Filmstarts(UserscriptBase):

	includes = ['*://www.filmstarts.de/kritiken/*']
	
	def getMovie(self, url):
		try:
			data = self.getUrl(url)
		except:
			return
			
		html = BeautifulSoup(data)
		table = html.find("section", attrs={"class": "section ovw ovw-synopsis", "id": "synopsis-details"})
		
		if table.find(text=re.compile('Originaltitel')): #some trailing whitespaces on some pages
			# Get original film title from the table specified above
			name = name = table.find("span", text=re.compile("Originaltitel")).findNext('h2').text
		else:
			# If none is available get the title from the meta data
			name = html.find("meta", {"property":"og:title"})['content']
			
		# Year of production is not available in the meta data, so get it from the table
		year = table.find("span", text=re.compile("Produktionsjahr")).findNext('span').text
		
		return self.search(name, year)
