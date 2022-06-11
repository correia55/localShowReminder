import os
import unittest.mock
import urllib.request

import globalsub
import sqlalchemy.orm

import configuration
import db_calls
import tmdb_calls

# To ensure the tests find the config folder no matter where it runs
if 'tests' in os.getcwd():
    base_path = ''
else:
    base_path = 'tests/'

# Prepare the mock variables for the modules
configuration_mock = unittest.mock.MagicMock()
db_calls_mock = unittest.mock.MagicMock()
external_request_mock = unittest.mock.MagicMock()


class TestTmdbCalls(unittest.TestCase):
    session: sqlalchemy.orm.Session

    @classmethod
    def setUpClass(cls) -> None:
        global db_calls_mock, external_request_mock, configuration_mock

        # Replace all references to the modules with mocks
        globalsub.subs(configuration, configuration_mock)
        globalsub.subs(db_calls, db_calls_mock)
        globalsub.subs(urllib.request, external_request_mock)

    @classmethod
    def tearDownClass(cls) -> None:
        # Replace back all references to the mocked modules
        globalsub.restore(configuration)
        globalsub.restore(db_calls)
        globalsub.restore(urllib.request)

    def setUp(self) -> None:
        self.session = unittest.mock.MagicMock()

    def test_get_show_using_id_01(self):
        """ Test get_show_using_id with no valid cache. """

        # Prepare the calls to the mocks
        configuration_mock.tmdb_key = 'tmdb_key'

        # Prepare the call to read the cache
        db_calls_mock.get_cache.return_value = None

        # Prepare the call to TMDB
        tmdb_response_file = open(base_path + "config/tmdb_show_74806.json", "r")
        tmdb_response = tmdb_response_file.read().encode()
        tmdb_response_file.close()

        external_request_mock.Request.return_value = 'the request'

        http_response = unittest.mock.MagicMock()
        external_request_mock.urlopen.return_value = http_response

        http_response.read.return_value = tmdb_response

        # Prepare the call to write to the cache
        cache_key = 'tmdb|id|tv-None-74806'

        db_calls_mock.register_cache(self.session, cache_key, tmdb_response.decode("utf-8"))

        # Call the function
        actual_result = tmdb_calls.get_show_using_id(self.session, 74806, False)

        # Verify the result
        self.assertEqual(74806, actual_result.id)
        self.assertEqual('Most Expensivest', actual_result.original_title)
        self.assertEqual('en', actual_result.original_language)
        self.assertEqual(1.545, actual_result.popularity)
        self.assertEqual('2 Chainz uncovers all of the extravagant ways the 1% enjoys blowing its load.',
                         actual_result.overview)
        self.assertEqual('Most Expensivest', actual_result.title)
        self.assertEqual(0.0, actual_result.vote_average)
        self.assertEqual(False, actual_result.is_movie)
        self.assertEqual(['Reality'], actual_result.genres)
        self.assertEqual('https://image.tmdb.org/t/p/w220_and_h330_face/9o4fGOURLkk9ajuDMMJmfGPk9cw.jpg',
                         actual_result.poster_path)
        self.assertEqual(['US'], actual_result.origin_country)
        self.assertEqual(2017, actual_result.year)

        # Verify the calls to the mocks
        db_calls_mock.get_cache.assert_called_with(self.session, cache_key)

        external_request_mock.Request.assert_called_with('https://api.themoviedb.org/3/tv/74806?api_key=tmdb_key')
        external_request_mock.urlopen.assert_called_with('the request')
