from bs4 import BeautifulSoup
from couchpotato.core.media._base.providers.userscript.base import UserscriptBase

autoload = 'Filmstarts'


class Filmstarts(UserscriptBase):

	includes = ['*://www.filmstarts.de/kritiken/*']
	
	def getMovie(self, url):
		try:
			data = self.getUrl(url)
		except:
			return
			
		html = BeautifulSoup(data)
		table = html.find("table", attrs={"class": "table table-standard thead-standard table-striped_2 fs11"})
		
		if table.find(text='Originaltitel'):
			# Get original film title from the table specified above
			name = table.find("div", text="Originaltitel").parent.parent.parent.td.text
		else:
			# If none is available get the title from the meta data
			name = html.find("meta", {"property":"og:title"})['content']
			
		# Year of production is not available in the meta data, so get it from the table
		year = table.find("tr", text="Produktionsjahr").parent.parent.parent.td.text
		
		return self.search(name, year)