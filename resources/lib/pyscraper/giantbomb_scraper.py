from datetime import datetime
from web_scraper import WebScraper
from rcbexceptions import *
from util import Logutil as log

# FIXME TODO exceptions, e.g. game not found


class GiantBomb_Scraper(WebScraper):
	"""GiantBomb.com has its API described at https://www.giantbomb.com/api/documentation """
	_name = 'GiantBomb.com'
	_apikey = '279442d60999f92c5e5f693b4d23bd3b6fd8e868'
	_search_url = 'https://giantbomb.com/api/search'    # http://www.giantbomb.com/api/search/?api_key=XXX&query=SEARCHTERM&field_list=name,id
	_retrieve_url = 'https://www.giantbomb.com/api/game/{0}/'  # game ID is substituted

	# Mapping between the dict keys and the JSON fields in the response
	_game_mapping = {
		'Game': 'name',
		'Description': 'deck',        # Short description
	}

	def __init__(self):
		pass

	def _get_search_url(self):
		return self._search_url

	def _get_search_params(self, **kwargs):
		return {'api_key': self._apikey,
				'query': '{0}'.format(self.prepare_gamename_for_request(kwargs['gamename'])),
				'resources': 'game',
				'filter': 'platforms:{0}'.format(self.consoleDict[kwargs['platform']][3]),
				'format': 'json',
				'field_list': 'id,name,platforms,original_release_date'}

	# FIXME generic kwargs
	def _get_retrieve_url(self, gameid):
		return self._retrieve_url.format(gameid)

	def _get_retrieve_params(self):
		return {'api_key': self._apikey,
				'format': 'json'}

	def _check_status_code(self, sc):
		if sc == 100:
			raise ScraperExceededAPIQuoteException("API quota exceeded for GiantBomb")
		elif sc == 101:
			raise ScraperGameNotFoundException("Did not find game matching ID")
		elif sc != 1:
			raise ScraperUnexpectedError("Unexpected error when scraping GiantBomb")

	def search(self, gamename, platform=None):
		response = self.open_json_url(url=self._get_search_url(), params=self._get_search_params(gamename=gamename, platform=platform))

		# Handle status code
		self._check_status_code(response['status_code'])

		result = self._parse_search_results(response)

		return result

	def retrieve(self, gameid):
		response = self.open_json_url(url=self._get_retrieve_url(gameid), params=self._get_retrieve_params())

		# Handle status code
		self._check_status_code(response['status_code'])

		results = self._parse_game_result(response['results'])
		return results

	def _parse_search_results(self, response):
		""" response is expected to be a JSON object """
		log.debug("Parsing response for search results: {0}".format(response))
		results = []

		if response['number_of_total_results'] == 0:
			log.warn("No results found")
			return results

		for result in response['results']:
			try:
				year = self._parse_date(result['original_release_date'])
				results.append({'id': result['id'],
								'title': result['name'],
								'releaseDate': year,
								'SearchKey': [result['name']]})
			except KeyError as k:
				log.warn("Unable to find expected field in response")
			except Exception as e:
				log.warn("Error parsing field: {0}".format(e))

		log.debug("Found {0} results using requests JSON parser: {1}".format(len(results), results))
		return results

	def _parse_game_result(self, response):
		""" response is expected to be a JSON object """
		result = {}

		# Standard fields
		for k, v in self._game_mapping.items():
			try:
				# HACK - for compatibility we need to put each result in an array
				#result[k] = response[v]
				result[k] = [response[v]]
			except KeyError as k:
				log.warn("Unable to find key: {0}".format(k))
			except Exception as e:
				log.warn("Unable to extract data from key {0}".format(e))

		# Custom fields (i.e. ones that require special handling
		# HACK - for compatibility we need to put each result in an array
		result['ReleaseYear'] = [self._parse_date(response['original_release_date'])]
		result['Developers'] = self._parse_developers(response['developers'])
		result['Publishers'] = self._parse_publishers(response['publishers'])
		result['Genre'] = self._parse_genres(response['genres'])

		# FIXME TODO Artwork and images are quite cumbersome to get from giantbomb search results

		return result

	def _parse_date(self, datestr):
		"""Convert the release date into the expected format

		Args:
			datestr: Date string captured from the original_release_data, usually in format as per "1987-12-18 00:00:00"

		Returns:
			Year represented as a 4 digit string, e.g. "1987"

		"""
		if datestr is None:
			return '1970'
		return datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S").strftime("%Y")

	def _parse_developers(self, developers):
		devs = []
		for dev in developers:
			devs.append(dev['name'])
		#print "Developers: " + str(devs)
		return devs

	def _parse_publishers(self, publishers):
		pubs = []
		for pub in publishers:
			pubs.append(pub['name'])
		#print "Publishers: " + str(pubs)
		return pubs

	def _parse_genres(self, genres):
		gens = []
		for gen in genres:
			gens.append(gen['name'])
		return gens
