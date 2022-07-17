import datetime
import os
import unittest.mock
from typing import Type

import globalsub
import sqlalchemy.orm

import configuration
import db_calls
import file_parsers.generic_weekly_spreadsheet_parser
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
        return datetime.datetime(2022, 7, 16, 15, 13, 34)


class TestGenericWeeklySpreadsheetParser(unittest.TestCase):
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
    def test_add_file_data_sic(self, tmdb_calls_mock) -> None:
        """ Test the function GenericXlsx.add_file_data with a sample from a Sic file. """

        # Prepare the mocks
        # Replace datetime class with a utility class with a fixed datetime
        datetime.datetime = NewDatetime

        # Prepare the call to get_channel_name
        channel_data = models.Channel('SIC', 'SIC')
        channel_data.id = 8373

        db_calls_mock.get_channel_name.return_value = channel_data

        # Treatment of the entries
        # ----------------------------
        # Prepare the calls to search_channel_show_data
        db_calls_mock.search_channel_show_data_correction.side_effect = [None, None, None, None, None, None, None, None,
                                                                         None, None, None, None]

        # Prepare the calls to search_channel_show_data
        show_data = models.ShowData('_EDICAO_DA_MANHA_', 'EDIÇÃO DA MANHÃ')
        show_data.id = 7503
        show_data.original_title = 'EDIÇÃO DA MANHÃ'
        show_data.is_movie = True

        show_data_2 = models.ShowData('_ETNIAS_', 'ETNIAS')
        show_data_2.id = 7912
        show_data_2.original_title = 'ETNIAS'
        show_data_2.is_movie = False

        show_data_3 = models.ShowData('_MARVELS_SPIDERMAN:_MAXIMUM_VENUM_', 'MARVELS SPIDERMAN: MAXIMUM VENUM')
        show_data_3.id = 82837
        show_data_3.original_title = 'MARVELS SPIDERMAN: MAXIMUM VENUM'
        show_data_3.is_movie = False

        show_data_4 = models.ShowData('_UMA_AVENTURA_', 'UMA AVENTURA')
        show_data_4.id = 1233
        show_data_4.original_title = 'UMA AVENTURA'
        show_data_4.is_movie = False

        show_data_5 = models.ShowData('_MEDICO_DA_CASA_', 'MÉDICO DA CASA')
        show_data_5.id = 3444
        show_data_5.original_title = 'MÉDICO DA CASA'
        show_data_5.is_movie = False

        db_calls_mock.insert_if_missing_show_data.side_effect = [(True, show_data_2), (True, show_data_3),
                                                                 (False, show_data_3), (True, show_data_4),
                                                                 (False, show_data_4), (True, show_data),
                                                                 (False, show_data), (False, show_data),
                                                                 (False, show_data), (False, show_data),
                                                                 (True, show_data_5), (False, show_data_4)]

        # Prepare the calls to search_shows_by_text
        tmdb_calls_mock.search_shows_by_text.side_effect = [(0, []), (0, []), (0, []), (0, []), (0, [])]

        # Prepare the calls to register_show_session
        show_session = models.ShowSession(None, None, None, None, None)

        db_calls_mock.register_show_session.side_effect = [show_session, show_session, show_session, show_session,
                                                           show_session, show_session, show_session, show_session,
                                                           show_session, show_session, show_session, show_session]

        # Prepare the calls to search_existing_session
        db_calls_mock.search_existing_session.side_effect = [None, None, None, None, None, None, None]

        # Call the function
        actual_result = file_parsers.generic_weekly_spreadsheet_parser.GenericWeeklySpreadsheetParser.add_file_data(
            self.session,
            base_path + 'data/sic_example.xls',
            'SIC')

        # Get back the datetime.datetime
        datetime.datetime = self.datetime_backup

        # Verify the result
        self.assertEqual(datetime.datetime(2022, 7, 4, 5, 55, 0), actual_result.start_datetime)
        self.assertEqual(datetime.datetime(2022, 7, 10, 8, 50, 0), actual_result.end_datetime)
        self.assertEqual(12, actual_result.total_nb_sessions_in_file)
        self.assertEqual(0, actual_result.nb_updated_sessions)
        self.assertEqual(12, actual_result.nb_added_sessions)
        self.assertEqual(0, actual_result.nb_deleted_sessions)

        # Verify the calls to the mocks
        db_calls_mock.get_channel_name.assert_called_with(self.session, 'SIC')

        db_calls_mock.search_channel_show_data_correction.assert_has_calls(
            [unittest.mock.call(self.session, 8373, False, 'ETNIAS', 'ETNIAS', directors=None, year=None, subgenre=None,
                                creators=None),
             unittest.mock.call(self.session, 8373, False, 'MARVELS SPIDERMAN: MAXIMUM VENUM',
                                'MARVELS SPIDERMAN: MAXIMUM VENUM', directors=None, year=None, subgenre=None,
                                creators=None),
             unittest.mock.call(self.session, 8373, False, 'MARVELS SPIDERMAN: MAXIMUM VENUM',
                                'MARVELS SPIDERMAN: MAXIMUM VENUM', directors=None, year=None, subgenre=None,
                                creators=None),
             unittest.mock.call(self.session, 8373, False, 'UMA AVENTURA', 'UMA AVENTURA', directors=None, year=None,
                                subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, False, 'UMA AVENTURA', 'UMA AVENTURA', directors=None, year=None,
                                subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, True, 'EDIÇÃO DA MANHÃ', 'EDIÇÃO DA MANHÃ', directors=None,
                                year=None, subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, True, 'EDIÇÃO DA MANHÃ', 'EDIÇÃO DA MANHÃ', directors=None,
                                year=None, subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, True, 'EDIÇÃO DA MANHÃ', 'EDIÇÃO DA MANHÃ', directors=None,
                                year=None, subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, True, 'EDIÇÃO DA MANHÃ', 'EDIÇÃO DA MANHÃ', directors=None,
                                year=None, subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, True, 'EDIÇÃO DA MANHÃ', 'EDIÇÃO DA MANHÃ', directors=None,
                                year=None, subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, False, 'MÉDICO DA CASA', 'MÉDICO DA CASA', directors=None,
                                year=None, subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, False, 'UMA AVENTURA', 'UMA AVENTURA', directors=None, year=None,
                                subgenre=None, creators=None)])

        db_calls_mock.insert_if_missing_show_data.assert_has_calls(
            [unittest.mock.call(self.session, 'ETNIAS', original_title='ETNIAS', is_movie=False, season=22,
                                date_time=datetime.datetime(2022, 7, 9, 6), cast=None, duration=None,
                                synopsis=None, year=None, genre='Series', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None),
             unittest.mock.call(self.session, 'MARVELS SPIDERMAN: MAXIMUM VENUM',
                                original_title='MARVELS SPIDERMAN: MAXIMUM VENUM', is_movie=False, season=1,
                                date_time=datetime.datetime(2022, 7, 10, 6, 30), cast=None, duration=None,
                                synopsis=None, year=None, genre='Series', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None),
             unittest.mock.call(self.session, 'MARVELS SPIDERMAN: MAXIMUM VENUM',
                                original_title='MARVELS SPIDERMAN: MAXIMUM VENUM', is_movie=False, season=1,
                                date_time=datetime.datetime(2022, 7, 9, 6, 45), cast=None, duration=None,
                                synopsis=None, year=None, genre='Series', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None),
             unittest.mock.call(self.session, 'UMA AVENTURA', original_title='UMA AVENTURA', is_movie=False, season=2,
                                date_time=datetime.datetime(2022, 7, 9, 7, 15), cast=None, duration=None,
                                synopsis=None, year=None, genre='Series', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None),
             unittest.mock.call(self.session, 'UMA AVENTURA', original_title='UMA AVENTURA', is_movie=False, season=4,
                                date_time=datetime.datetime(2022, 7, 10, 7), cast=None, duration=None,
                                synopsis=None, year=None, genre='Series', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None),
             unittest.mock.call(self.session, 'EDIÇÃO DA MANHÃ',
                                original_title='EDIÇÃO DA MANHÃ', is_movie=True, season=None,
                                date_time=datetime.datetime(2022, 7, 4, 6), cast=None, duration=None,
                                synopsis=None, year=None, genre='Movie', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None),
             unittest.mock.call(self.session, 'EDIÇÃO DA MANHÃ',
                                original_title='EDIÇÃO DA MANHÃ', is_movie=True, season=None,
                                date_time=datetime.datetime(2022, 7, 5, 6), cast=None, duration=None,
                                synopsis=None, year=None, genre='Movie', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None),
             unittest.mock.call(self.session, 'EDIÇÃO DA MANHÃ',
                                original_title='EDIÇÃO DA MANHÃ', is_movie=True, season=None,
                                date_time=datetime.datetime(2022, 7, 6, 6), cast=None, duration=None,
                                synopsis=None, year=None, genre='Movie', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None),
             unittest.mock.call(self.session, 'EDIÇÃO DA MANHÃ',
                                original_title='EDIÇÃO DA MANHÃ', is_movie=True, season=None,
                                date_time=datetime.datetime(2022, 7, 7, 6), cast=None, duration=None,
                                synopsis=None, year=None, genre='Movie', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None),
             unittest.mock.call(self.session, 'EDIÇÃO DA MANHÃ',
                                original_title='EDIÇÃO DA MANHÃ', is_movie=True, season=None,
                                date_time=datetime.datetime(2022, 7, 8, 6), cast=None, duration=None,
                                synopsis=None, year=None, genre='Movie', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None),
             unittest.mock.call(self.session, 'MÉDICO DA CASA',
                                original_title='MÉDICO DA CASA', is_movie=False, season=1,
                                date_time=datetime.datetime(2022, 7, 9, 8), cast=None, duration=None,
                                synopsis=None, year=None, genre='Series', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None),
             unittest.mock.call(self.session, 'UMA AVENTURA',
                                original_title='UMA AVENTURA', is_movie=False, season=4,
                                date_time=datetime.datetime(2022, 7, 10, 8), cast=None, duration=None,
                                synopsis=None, year=None, genre='Series', subgenre=None, audio_languages=None,
                                countries=None, directors=None, age_classification=None, creators=None)])

        tmdb_calls_mock.search_shows_by_text.assert_has_calls(
            [unittest.mock.call(self.session, 'ETNIAS', is_movie=False, year=None),
             unittest.mock.call(self.session, 'MARVELS SPIDERMAN: MAXIMUM VENUM', is_movie=False, year=None),
             unittest.mock.call(self.session, 'UMA AVENTURA', is_movie=False, year=None),
             unittest.mock.call(self.session, 'EDIÇÃO DA MANHÃ', is_movie=True, year=None),
             unittest.mock.call(self.session, 'MÉDICO DA CASA', is_movie=False, year=None)])

        db_calls_mock.register_show_session.assert_has_calls(
            [unittest.mock.call(self.session, 22, 28, datetime.datetime(2022, 7, 9, 6), 8373, 7912, audio_language=None,
                                extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, 1, 12, datetime.datetime(2022, 7, 10, 6, 30), 8373, 82837,
                                audio_language=None, extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, 1, 11, datetime.datetime(2022, 7, 9, 6, 45), 8373, 82837,
                                audio_language=None, extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, 2, 17, datetime.datetime(2022, 7, 9, 7, 15), 8373, 1233,
                                audio_language=None, extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, 4, 7, datetime.datetime(2022, 7, 10, 7), 8373, 1233,
                                audio_language=None, extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2022, 7, 4, 6), 8373, 7503,
                                audio_language=None, extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2022, 7, 5, 6), 8373, 7503,
                                audio_language=None, extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2022, 7, 6, 6), 8373, 7503,
                                audio_language=None, extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2022, 7, 7, 6), 8373, 7503,
                                audio_language=None, extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2022, 7, 8, 6), 8373, 7503,
                                audio_language=None, extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, 1, 21, datetime.datetime(2022, 7, 9, 8), 8373, 3444,
                                audio_language=None, extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, 4, 8, datetime.datetime(2022, 7, 10, 8), 8373, 1233,
                                audio_language=None, extended_cut=False, should_commit=False)])

        db_calls_mock.search_existing_session.assert_has_calls(
            [unittest.mock.call(self.session, 1, 11, datetime.datetime(2022, 7, 9, 6, 45), 8373, 82837),
             unittest.mock.call(self.session, 4, 7, datetime.datetime(2022, 7, 10, 7), 8373, 1233),
             unittest.mock.call(self.session, None, None, datetime.datetime(2022, 7, 5, 6), 8373, 7503),
             unittest.mock.call(self.session, None, None, datetime.datetime(2022, 7, 6, 6), 8373, 7503),
             unittest.mock.call(self.session, None, None, datetime.datetime(2022, 7, 7, 6), 8373, 7503),
             unittest.mock.call(self.session, None, None, datetime.datetime(2022, 7, 8, 6), 8373, 7503),
             unittest.mock.call(self.session, 4, 8, datetime.datetime(2022, 7, 10, 8), 8373, 1233)])
