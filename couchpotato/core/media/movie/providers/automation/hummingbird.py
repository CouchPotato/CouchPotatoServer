from couchpotato.core.logger import CPLog
from couchpotato.core.media.movie.providers.automation.base import Automation


log = CPLog(__name__)

autoload = 'Hummingbird'


class Hummingbird(Automation):

	def getIMDBids(self):
		movies = []
		for movie in self.getWatchlist():
			imdb = self.search(movie[0], movie[1])
			if imdb:
				movies.append(imdb['imdb'])
		return movies

	def getWatchlist(self):
		if not self.conf('automation_username'):
			log.error('You need to fill in a username')
			return []

		url = "http://hummingbird.me/api/v1/users/%s/library" % self.conf('automation_username')
		data = self.getJsonData(url)

		chosen_filter = {
			'automation_list_current': 'currently-watching',
			'automation_list_plan': 'plan-to-watch',
			'automation_list_completed': 'completed',
			'automation_list_hold': 'on-hold',
			'automation_list_dropped': 'dropped',
		}

		chosen_lists = []
		for x in chosen_filter:
			if self.conf(x):
				chosen_lists.append(chosen_filter[x])

		entries = []
		for item in data:
			if item['anime']['show_type'] != 'Movie' or item['status'] not in chosen_lists:
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
					'default': True,
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
