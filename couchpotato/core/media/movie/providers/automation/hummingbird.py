import base64
import urllib2
import json

from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation


log = CPLog(__name__)

autoload = 'Hummingbird'


class Hummingbird(Automation):

	def __init__(self):
		super(Hummingbird, self).__init__()

	def getIMDBids(self):
		movies = []
		for movie in self.getWatchlist():
			imdb = self.search(movie[0], movie[1])
			if imdb:
				movies.append(imdb['imdb'])
		return movies

	def getWatchlist(self):
		url = "http://hummingbird.me/api/v1/users/%s/library" % self.conf('automation_username')
		try:
			data = json.load(urllib2.urlopen(url))
		except ValueError:
			log.error('Error getting list from hummingbird.')

		chosen = [self.conf('automation_list_current'), self.conf('automation_list_plan'), self.conf('automation_list_completed'), self.conf('automation_list_hold'), self.conf('automation_list_dropped')]
		chosen_lists = []
		if chosen[0] == True:
			chosen_lists.append('currently-watching')
		if chosen[1] == True:
			chosen_lists.append('plan-to-watch')
		if chosen[2] == True:
			chosen_lists.append('completed')
		if chosen[3] == True:
			chosen_lists.append('on-hold')
		if chosen[4] == True:
			chosen_lists.append('dropped')
		
		entries = []
		for item in data:
			if item['status'] not in chosen_lists:
				continue
			if item['anime']['show_type'] != 'Movie':
				continue
			title = item['anime']['title']
			year = item['anime']['started_airing']
			if year:
				year = year[:4]
			entries.append([title, year])
		return entries

config = [{
	'name': 'hummingbird',
	'groups': [
		{
			'tab': 'automation',
			'list': 'watchlist_providers',
			'name': 'hummingbird_automation',
			'label': 'Hummingbird',
			'description': 'Import movies from your Hummingbird.me lists',
			'options': [
				{
					'name': 'automation_enabled',
					'default': False,
					'type': 'enabler',
				},
				{
					'name': 'automation_username',
					'label': 'Username',
				},
				{
					'name': 'automation_list_current',
					'type': 'bool',
					'label': 'Currently Watching',
					'default': False,
				},
				{
					'name': 'automation_list_plan',
					'type': 'bool',
					'label': 'Plan to Watch',
					'default': False,
				},
				{
					'name': 'automation_list_completed',
					'type': 'bool',
					'label': 'Completed',
					'default': False,
				},
				{
					'name': 'automation_list_hold',
					'type': 'bool',
					'label': 'On Hold',
					'default': False,
				},
				{
					'name': 'automation_list_dropped',
					'type': 'bool',
					'label': 'Dropped',
					'default': False,
				},
			],
		},
	],
}]
