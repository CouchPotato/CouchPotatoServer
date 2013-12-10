from .main import Dereferer


def start():
	return Dereferer()


config = [{
			'name': 'dereferer',
			'groups': [
				{
				'tab': 'general',
					'name': 'dereferer',
					'label': 'Dereferer',
					'description': 'Use a derefering service to strip HOSTs from external links (such as IMDb)',
					'options': [
						{
							'name': 'enabled',
							'default': True,
							'type': 'enabler',
						},
						{
							'advanced': True,
							'name': 'service_url',
							'default': 'http://www.dereferer.org/?',
						},
					],
				}
			],
		}]