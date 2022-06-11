import datetime
import os
import unittest.mock
from typing import Type

import globalsub
import sqlalchemy.orm

import configuration
import db_calls
import file_parsers.generic_spreadsheet_merged_cells_parser
import models

# Prepare the mock variables for the modules
db_calls_mock = unittest.mock.MagicMock()

# To ensure the tests find the config folder no matter where it runs
if 'tests' in os.getcwd():
    base_path = '../'
else:
    base_path = 'tests/'


# This class allows us to set a fake datetime as the today date in datetime
# Remark: they need to be set and then reset
class NewDatetime(datetime.datetime):
    @classmethod
    def utcnow(cls):
        return datetime.datetime(2021, 3, 1, 15, 13, 34)


class TestGenericSpreadsheetMergedCellsParser(unittest.TestCase):
    session: sqlalchemy.orm.Session

    datetime_backup: Type[datetime.datetime]

    def setUp(self) -> None:
        self.session = unittest.mock.MagicMock()
        configuration.show_sessions_validity_days = 7
        configuration.base_dir = base_path + '../'

        # Save the datetime.date
        self.datetime_backup = datetime.datetime

    def tearDown(self) -> None:
        db_calls_mock.reset_mock()

        # Reset the datetime class to work normally
        datetime.datetime = self.datetime_backup

    @classmethod
    def setUpClass(cls) -> None:
        global db_calls_mock

        # Replace all references to the modules with mocks
        globalsub.subs(db_calls, db_calls_mock)

    @classmethod
    def tearDownClass(cls) -> None:
        # Replace back all references to the mocked modules
        globalsub.restore(db_calls)

    @unittest.mock.patch('get_file_data.tmdb_calls')
    def test_add_file_data_historia(self, tmdb_calls_mock) -> None:
        """ Test the function GenericSpreadsheetMergedCellsParser.add_file_data with a sample from the format of a Historia file. """

        # Prepare the mocks
        # Replace datetime class with a utility class with a fixed datetime
        datetime.datetime = NewDatetime

        # Prepare the call to get_channel_name
        channel_data = models.Channel('HIST', 'História')
        channel_data.id = 8373

        db_calls_mock.get_channel_name.return_value = channel_data

        # Treatment of the entries
        # ----------------------------
        # Prepare the calls to search_channel_show_data
        db_calls_mock.search_channel_show_data_correction.side_effect = [None, None]

        # Prepare the calls to insert_if_missing_show_data
        show_data = models.ShowData(None, None)
        show_data.id = 7503

        show_data_2 = models.ShowData(None, None)
        show_data_2.id = 7912

        db_calls_mock.insert_if_missing_show_data.side_effect = [(True, show_data), (True, show_data_2)]

        # Prepare the calls to register_show_session
        show_session = models.ShowSession(None, None, None, None, None)
        show_session_2 = models.ShowSession(None, None, None, None, None)

        db_calls_mock.register_show_session.side_effect = [show_session, show_session_2]

        # Call the function
        actual_result = file_parsers.generic_spreadsheet_merged_cells_parser.GenericSpreadsheetMergedCellsParser.add_file_data(
            self.session, base_path + 'data/historia_example.xls', 'História')

        # Get back the datetime.datetime
        datetime.datetime = self.datetime_backup

        # Verify the result
        self.assertEqual(datetime.datetime(2022, 5, 31, 23, 13), actual_result.start_datetime)
        self.assertEqual(datetime.datetime(2022, 6, 1, 3, 26), actual_result.end_datetime)
        self.assertEqual(2, actual_result.total_nb_sessions_in_file)
        self.assertEqual(0, actual_result.nb_updated_sessions)
        self.assertEqual(2, actual_result.nb_added_sessions)
        self.assertEqual(0, actual_result.nb_deleted_sessions)

        # Verify the calls to the mocks
        tmdb_calls_mock.search_shows_by_text.assert_not_called()

        db_calls_mock.get_channel_name.assert_called_with(self.session, 'História')

        db_calls_mock.search_channel_show_data_correction.assert_has_calls(
            [unittest.mock.call(self.session, 8373, False, None, 'Forjado no Fogo', directors=None, year=None,
                                subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, True, None, 'Animais na Guerra', directors=None, year=None,
                                subgenre=None, creators=None)])

        db_calls_mock.insert_if_missing_show_data.assert_has_calls(
            [unittest.mock.call(self.session, 'Forjado no Fogo', cast=None, original_title=None, duration=40,
                                synopsis=None, year=None, genre='Series', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification='NR12',
                                is_movie=False, season=7, creators=None,
                                date_time=datetime.datetime(2022, 5, 31, 23, 18)),
             unittest.mock.call(self.session, 'Animais na Guerra', cast=None, original_title=None, duration=52,
                                synopsis=None, year=None, genre='Movie', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification='NR12',
                                is_movie=True, season=None, creators=None,
                                date_time=datetime.datetime(2022, 6, 1, 3, 21))])

        db_calls_mock.register_show_session.assert_has_calls(
            [unittest.mock.call(self.session, 7, 160, datetime.datetime(2022, 5, 31, 23, 18), 8373, 7503,
                                audio_language=None, extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2022, 6, 1, 3, 21), 8373, 7912,
                                audio_language=None, extended_cut=False, should_commit=False)])
