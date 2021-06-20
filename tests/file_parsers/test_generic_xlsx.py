import datetime
import os
import unittest.mock
from types import ModuleType
from typing import Type

import globalsub
import sqlalchemy.orm

import configuration
import db_calls
import file_parsers.generic_xlsx
import models

# Prepare the variables for replacing db_calls
db_calls_backup: ModuleType
db_calls_mock = unittest.mock.MagicMock()

# To ensure the tests find the data folder no matter where it runs
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


class TestGenericXlsx(unittest.TestCase):
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
        global db_calls_backup, db_calls_mock

        # Save a reference to the module db_calls
        db_calls_backup = db_calls

        # Replace all references to the module db_calls with a mock
        globalsub.subs(db_calls, db_calls_mock)

    @classmethod
    def tearDownClass(cls) -> None:
        # Replace back all references to the module db_calls to the module
        globalsub.subs(db_calls_mock, db_calls_backup)

    def test_process_title_01(self) -> None:
        """ Test the function GenericXlsx.process_title with format season_at_the_end on a series. """

        # The expected result
        expected_result = 'Monster Croc Wrangler'

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.process_title('Monster Croc Wrangler 4',
                                                                            'season_at_the_end')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_02(self) -> None:
        """ Test the function GenericXlsx.process_title with format season_at_the_end on a movie. """

        # The expected result
        expected_result = 'Tiger On The Run'

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.process_title('Tiger On The Run', 'season_at_the_end')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    @unittest.mock.patch('get_file_data.tmdb_calls')
    def test_add_file_data_nat_geo_wild(self, tmdb_calls_mock) -> None:
        """ Test the function GenericXlsx.add_file_data with a sample from a Nat Geo Wild file. """

        # Prepare the mocks
        # Replace datetime class with a utility class with a fixed datetime
        datetime.datetime = NewDatetime

        # Prepare the call to get_channel_name
        channel_data = models.Channel('WILD', 'Nat Geo Wild')
        channel_data.id = 8373

        db_calls_mock.get_channel_name.return_value = channel_data

        # Treatment of the entries
        # ----------------------------
        # Prepare the calls to search_channel_show_data
        db_calls_mock.search_channel_show_data_correction.side_effect = [None, None]

        # Prepare the calls to search_channel_show_data
        show_data = models.ShowData('_Monster_Croc_Wrangler_', 'Monster Croc Wrangler')
        show_data.id = 7503
        show_data.original_title = 'Monster Croc Wrangler'
        show_data.synopsis = 'Managers of Victoria River Downs Ranch; Rusty and Julie haven\'t had trouble with ' \
                             'Crocs for years. But recently a number of big Salties have been spotted in the river. ' \
                             'Matt Wright is called in to clear any problem Crocs and keep the ranch workers and ' \
                             'kids safe.'
        show_data.genre = 'Series'
        show_data.is_movie = False
        show_data.countries = 'Australia'
        show_data.subgenre = 'Natural History'
        show_data.age_classification = '12+'

        show_data_2 = models.ShowData('_Tiger_On_The_Run_', 'Tiger On The Run')
        show_data_2.id = 7912
        show_data_2.original_title = 'Tiger On The Run'
        show_data_2.year = 2015
        show_data_2.synopsis = '"Tiger on the Run" is a natural history documentary following a young tiger in ' \
                               'India, that\'s been forced out of his home territory by another male, and has to ' \
                               'struggle for survival. The film promises to address the issue of habitat ' \
                               'destruction and interaction of tigers and humans caused by the shrinking habitat.'
        show_data_2.director = 'Dwight H. Little'
        show_data_2.genre = 'Movie'
        show_data_2.is_movie = True
        show_data_2.countries = 'South Africa'
        show_data_2.subgenre = 'Natural History'
        show_data_2.age_classification = '12+'

        db_calls_mock.insert_if_missing_show_data.side_effect = [(True, show_data), (True, show_data_2)]

        # Prepare the calls to search_shows_by_text
        tmdb_calls_mock.search_shows_by_text.side_effect = [(0, []), (0, []), (0, [])]

        # Prepare the calls to register_show_session
        show_session = models.ShowSession(4, 7, datetime.datetime(2021, 7, 1, 5), 8373, 7503)
        show_session_2 = models.ShowSession(None, None, datetime.datetime(2021, 7, 1, 5, 50), 8373, 7912)

        db_calls_mock.register_show_session.side_effect = [show_session, show_session_2]

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.add_file_data(self.session,
                                                                            base_path + 'data/nat_geo_wild_example.xls',
                                                                            'Nat Geo Wild')

        # Get back the datetime.datetime
        datetime.datetime = self.datetime_backup

        # Verify the result
        self.assertEqual(datetime.datetime(2021, 7, 1, 4, 55, 0), actual_result.start_datetime)
        self.assertEqual(datetime.datetime(2021, 7, 2, 0, 23, 0), actual_result.end_datetime)
        self.assertEqual(2, actual_result.total_nb_sessions_in_file)
        self.assertEqual(0, actual_result.nb_updated_sessions)
        self.assertEqual(2, actual_result.nb_added_sessions)
        self.assertEqual(0, actual_result.nb_deleted_sessions)

        # Verify the calls to the mocks
        db_calls_mock.get_channel_name.assert_called_with(self.session, 'Nat Geo Wild')

        db_calls_mock.search_channel_show_data_correction.assert_has_calls(
            [unittest.mock.call(self.session, 8373, False, 'Monster Croc Wrangler', 'Monster Croc Wrangler',
                                directors=None, year=2019,
                                subgenre='Natural History', creators=None),
             unittest.mock.call(self.session, 8373, True, 'Tiger On The Run', 'Tiger On The Run',
                                directors=None, year=2015, subgenre='Natural History', creators=None)])

        db_calls_mock.insert_if_missing_show_data.assert_has_calls(
            [unittest.mock.call(self.session, 'Monster Croc Wrangler', cast=None,
                                original_title='Monster Croc Wrangler', duration=21,
                                synopsis='Managers of Victoria River Downs Ranch; Rusty and Julie haven\'t had trouble'
                                         ' with Crocs for years. But recently a number of big Salties have been '
                                         'spotted in the river. Matt Wright is called in to clear any problem Crocs '
                                         'and keep the ranch workers and kids safe.', year=2019, genre='Series',
                                subgenre='Natural History', audio_languages=None, countries='Australia',
                                directors=None, age_classification='12+', is_movie=False, season=4,
                                creators=None),
             unittest.mock.call(self.session, 'Tiger On The Run', cast=None,
                                original_title='Tiger On The Run', duration=44,
                                synopsis='"Tiger on the Run" is a natural history documentary following a young tiger '
                                         'in India, that\'s been forced out of his home territory by another male, and '
                                         'has to struggle for survival. The film promises to address the issue of '
                                         'habitat destruction and interaction of tigers and humans caused by the '
                                         'shrinking habitat.', year=2015, genre='Movie', subgenre='Natural History',
                                audio_languages=None, countries='South Africa',
                                directors=None, age_classification='12+', is_movie=True, season=None,
                                creators=None)])

        tmdb_calls_mock.search_shows_by_text.assert_has_calls(
            [unittest.mock.call(self.session, 'Monster Croc Wrangler', is_movie=False, year=None),
             unittest.mock.call(self.session, 'Tiger On The Run', is_movie=True, year=2015),
             unittest.mock.call(self.session, 'Tiger On The Run', is_movie=True, year=None)])

        db_calls_mock.register_show_session.assert_has_calls(
            [unittest.mock.call(self.session, 4, 7, datetime.datetime(2021, 7, 1, 5), 8373, 7503, audio_language=None,
                                extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2021, 7, 2, 0, 18), 8373, 7912,
                                audio_language=None, extended_cut=False, should_commit=False)])

    @unittest.mock.patch('get_file_data.tmdb_calls')
    def test_add_file_data_national_geographic(self, tmdb_calls_mock) -> None:
        """ Test the function GenericXlsx.add_file_data with a sample from a National Geographic file. """

        # Prepare the mocks
        # Replace datetime class with a utility class with a fixed datetime
        datetime.datetime = NewDatetime

        # Prepare the call to get_channel_name
        channel_data = models.Channel('NGC', 'National Geographic')
        channel_data.id = 8373

        db_calls_mock.get_channel_name.return_value = channel_data

        # Treatment of the entries
        # ----------------------------
        # Prepare the calls to search_channel_show_data
        db_calls_mock.search_channel_show_data_correction.side_effect = [None, None]

        # Prepare the calls to search_channel_show_data
        show_data = models.ShowData('_Cidades_Perdidas_com_Albert_Lin_', 'Cidades Perdidas com Albert Lin')
        show_data.id = 7503
        show_data.original_title = 'Lost Cities With Albert Lin'
        show_data.synopsis = 'O explorador da National Geographic, Albert Lin, viaja até Petra, na Jordânia, para ' \
                             'descobrir as origens da famosa cidade. É lá que descobre que esta foi construída ' \
                             'pelos Nabateus e procura vestígios das suas cidades e templos.'
        show_data.genre = 'Series'
        show_data.is_movie = False
        show_data.age_classification = '12+'

        show_data_2 = models.ShowData('_Bastidores_Marijuana_', 'Bastidores: Marijuana')
        show_data_2.id = 7912
        show_data_2.original_title = 'Inside Marijuana'
        show_data_2.year = 2008
        show_data_2.synopsis = 'Marijuana é a substância ilícita mais consumida no planeta. Na maior parte dos ' \
                               'países, esta planta é ilegal - alguns dizerm que é perigosa, outros vêem-na de ' \
                               'outra forma. O governo dos Estados Unidos coloca-a na mesma categoria que a ' \
                               'Heroína. Esta planta é considerada das substâmncias mais complexas por parte ' \
                               'dos cientistas, e o alcance que tem é mundial. Misturada com a cultura, economia, ' \
                               'sistema judicial e medicina, esta planta é sinónimo de perigo e promessa.'
        show_data_2.genre = 'Movie'
        show_data_2.is_movie = True
        show_data_2.age_classification = '16+'

        db_calls_mock.insert_if_missing_show_data.side_effect = [(True, show_data), (True, show_data_2)]

        # Prepare the calls to search_shows_by_text
        tmdb_calls_mock.search_shows_by_text.side_effect = [(0, []), (0, []), (0, [])]

        # Prepare the calls to register_show_session
        show_session = models.ShowSession(1, 4, datetime.datetime(2021, 7, 1, 5), 8373, 7503)
        show_session_2 = models.ShowSession(None, None, datetime.datetime(2021, 7, 18, 0, 48), 8373, 7912)

        db_calls_mock.register_show_session.side_effect = [show_session, show_session_2]

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.add_file_data(self.session,
                                                                            base_path + 'data/national_geographic_example.xlsx',
                                                                            'National Geographic')

        # Get back the datetime.datetime
        datetime.datetime = self.datetime_backup

        # Verify the result
        self.assertEqual(datetime.datetime(2021, 7, 1, 4, 55, 0), actual_result.start_datetime)
        self.assertEqual(datetime.datetime(2021, 7, 17, 23, 53, 0), actual_result.end_datetime)
        self.assertEqual(2, actual_result.total_nb_sessions_in_file)
        self.assertEqual(0, actual_result.nb_updated_sessions)
        self.assertEqual(2, actual_result.nb_added_sessions)
        self.assertEqual(0, actual_result.nb_deleted_sessions)

        # Verify the calls to the mocks
        db_calls_mock.get_channel_name.assert_called_with(self.session, 'National Geographic')

        db_calls_mock.search_channel_show_data_correction.assert_has_calls(
            [unittest.mock.call(self.session, 8373, False, 'Lost Cities With Albert Lin',
                                'Cidades Perdidas com Albert Lin', directors=None, year=2019,
                                subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, True, 'Inside Marijuana', 'Bastidores: Marijuana',
                                directors=None, year=2008, subgenre=None, creators=None)])

        db_calls_mock.insert_if_missing_show_data.assert_has_calls(
            [unittest.mock.call(self.session, 'Cidades Perdidas com Albert Lin', cast=None,
                                original_title='Lost Cities With Albert Lin', duration=None,
                                synopsis='O explorador da National Geographic, Albert Lin, viaja até Petra, na '
                                         'Jordânia, para descobrir as origens da famosa cidade. É lá que descobre que '
                                         'esta foi construída pelos Nabateus e procura vestígios das suas cidades e '
                                         'templos.', year=2019, genre='Series',
                                subgenre=None, audio_languages=None, countries=None,
                                directors=None, age_classification='12+', is_movie=False, season=1,
                                creators=None),
             unittest.mock.call(self.session, 'Bastidores: Marijuana', cast=None,
                                original_title='Inside Marijuana', duration=None,
                                synopsis='Marijuana é a substância ilícita mais consumida no planeta. Na maior parte '
                                         'dos países, esta planta é ilegal - alguns dizerm que é perigosa, outros '
                                         'vêem-na de outra forma. O governo dos Estados Unidos coloca-a na mesma '
                                         'categoria que a Heroína. Esta planta é considerada das substâmncias mais '
                                         'complexas por parte dos cientistas, e o alcance que tem é mundial. Misturada '
                                         'com a cultura, economia, sistema judicial e medicina, esta planta é sinónimo '
                                         'de perigo e promessa.', year=2008, genre='Movie', subgenre=None,
                                audio_languages=None, countries=None,
                                directors=None, age_classification='16+', is_movie=True, season=None,
                                creators=None)])

        tmdb_calls_mock.search_shows_by_text.assert_has_calls(
            [unittest.mock.call(self.session, 'Lost Cities With Albert Lin', is_movie=False, year=None),
             unittest.mock.call(self.session, 'Inside Marijuana', is_movie=True, year=2008),
             unittest.mock.call(self.session, 'Inside Marijuana', is_movie=True, year=None)])

        db_calls_mock.register_show_session.assert_has_calls(
            [unittest.mock.call(self.session, 1, 4, datetime.datetime(2021, 7, 1, 5), 8373, 7503, audio_language=None,
                                extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2021, 7, 17, 23, 48), 8373, 7912,
                                audio_language=None, extended_cut=False, should_commit=False)])

    @unittest.mock.patch('get_file_data.tmdb_calls')
    def test_add_file_data_fox_crime(self, tmdb_calls_mock) -> None:
        """ Test the function GenericXlsx.add_file_data with a sample from a FOX Crime file. """

        # Prepare the mocks
        # Replace datetime class with a utility class with a fixed datetime
        datetime.datetime = NewDatetime

        # Prepare the call to get_channel_name
        channel_data = models.Channel('FOXCR', 'FOX Crime')
        channel_data.id = 8373

        db_calls_mock.get_channel_name.return_value = channel_data

        # Treatment of the entries
        # ----------------------------
        # Prepare the calls to search_channel_show_data
        db_calls_mock.search_channel_show_data_correction.side_effect = [None, None]

        # Prepare the calls to search_channel_show_data
        show_data = models.ShowData('_Lie_To_Me_', 'Lie To Me')
        show_data.id = 7503
        show_data.original_title = 'Lie To Me'
        show_data.synopsis = 'Um adolescente perturbado crê que foi raptado em bebé e recorre ao Lightman Group para ' \
                             'o ajudar a desvendar os segredos do seu passado; Eli investiga a origem de uma ' \
                             'debandada letal que ocorreu numa grande superfície comercial, no dia após o Dia de ' \
                             'Ação de Graças.'
        show_data.genre = 'Series'
        show_data.is_movie = False
        show_data.age_classification = '12+'

        show_data_2 = models.ShowData('_Crime_Disse_Ela_', 'Crime, Disse Ela')
        show_data_2.id = 7912
        show_data_2.original_title = 'Murder She Wrote'
        show_data_2.synopsis = 'Será que um florista de Beverly Hills foi morto porque estava a fornecer mais do ' \
                               'que flores a editores de revistas de mexericos?'
        show_data_2.genre = 'Series'
        show_data_2.is_movie = False
        show_data_2.age_classification = '12+'

        db_calls_mock.insert_if_missing_show_data.side_effect = [(True, show_data), (True, show_data_2)]

        # Prepare the calls to search_shows_by_text
        tmdb_calls_mock.search_shows_by_text.side_effect = [(0, []), (0, []), (0, [])]

        # Prepare the calls to register_show_session
        show_session = models.ShowSession(1, 4, datetime.datetime(2021, 7, 1, 5), 8373, 7503)
        show_session_2 = models.ShowSession(None, None, datetime.datetime(2021, 7, 1, 5, 34), 8373, 7912)

        db_calls_mock.register_show_session.side_effect = [show_session, show_session_2]

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.add_file_data(self.session,
                                                                            base_path + 'data/fox_crime_example.xlsx',
                                                                            'FOX Crime')

        # Get back the datetime.datetime
        datetime.datetime = self.datetime_backup

        # Verify the result
        self.assertEqual(datetime.datetime(2021, 7, 1, 4, 55, 0), actual_result.start_datetime)
        self.assertEqual(datetime.datetime(2021, 7, 1, 5, 39, 0), actual_result.end_datetime)
        self.assertEqual(2, actual_result.total_nb_sessions_in_file)
        self.assertEqual(0, actual_result.nb_updated_sessions)
        self.assertEqual(2, actual_result.nb_added_sessions)
        self.assertEqual(0, actual_result.nb_deleted_sessions)

        # Verify the calls to the mocks
        db_calls_mock.get_channel_name.assert_called_with(self.session, 'FOX Crime')

        db_calls_mock.search_channel_show_data_correction.assert_has_calls(
            [unittest.mock.call(self.session, 8373, False, 'Lie To Me',
                                'Lie To Me', directors=None, year=2009,
                                subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, False, 'Murder She Wrote', 'Crime, Disse Ela',
                                directors=None, year=1993, subgenre=None,
                                creators=['Peter S. Fischer', 'Richard Levinson', 'William Link'])])

        db_calls_mock.insert_if_missing_show_data.assert_has_calls(
            [unittest.mock.call(self.session, 'Lie To Me', cast='Bill Zasadil,Erica Grace,Gordon Greene,Hannah Cox,J. '
                                                                'Downing,Jackie Debatin,Jim Hanna,John Bishop,Kelli '
                                                                'Williams,Laurel Weber,Lisa Waltz,Mark Ankeny,Nick '
                                                                'Searcy,Randy Lowell,Shashawnee Hall,Tim Roth,Whitney '
                                                                'Powell',
                                original_title='Lie To Me', duration=None,
                                synopsis='Um adolescente perturbado crê que foi raptado em bebé e recorre ao Lightman '
                                         'Group para o ajudar a desvendar os segredos do seu passado; Eli investiga '
                                         'a origem de uma debandada letal que ocorreu numa grande superfície '
                                         'comercial, no dia após o Dia de Ação de Graças.', year=2009, genre='Series',
                                subgenre=None, audio_languages=None, countries=None,
                                directors=None, age_classification='12+', is_movie=False, season=2,
                                creators=None),
             unittest.mock.call(self.session, 'Crime, Disse Ela', cast='Angela Lansbury,Ron Masak,William Windom',
                                original_title='Murder She Wrote', duration=None,
                                synopsis='Será que um florista de Beverly Hills foi morto porque estava a fornecer '
                                         'mais do que flores a editores de revistas de mexericos?', year=1993,
                                genre='Series', subgenre=None,
                                audio_languages=None, countries=None,
                                directors=None, age_classification='12+', is_movie=False, season=9,
                                creators=['Peter S. Fischer', 'Richard Levinson', 'William Link'])])

        tmdb_calls_mock.search_shows_by_text.assert_has_calls(
            [unittest.mock.call(self.session, 'Lie To Me', is_movie=False, year=None),
             unittest.mock.call(self.session, 'Murder She Wrote', is_movie=False, year=None)])

        db_calls_mock.register_show_session.assert_has_calls(
            [unittest.mock.call(self.session, 2, 7, datetime.datetime(2021, 7, 1, 5), 8373, 7503, audio_language=None,
                                extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, 9, 15, datetime.datetime(2021, 7, 1, 5, 34), 8373, 7912,
                                audio_language=None, extended_cut=False, should_commit=False)])
