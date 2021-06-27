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
import tmdb_calls

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
                                                                            'season_at_the_end', False)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_02(self) -> None:
        """ Test the function GenericXlsx.process_title with format season_at_the_end on a movie. """

        # The expected result
        expected_result = 'Tiger On The Run'

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.process_title('Tiger On The Run', 'season_at_the_end',
                                                                            True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_03(self) -> None:
        """
        Test the function GenericXlsx.process_title with format season_at_the_end on a movie with a number at the end.
        """

        # The expected result
        expected_result = 'The Hunger Games: Mockingjay Part 1'

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.process_title('The Hunger Games: Mockingjay Part 1',
                                                                            'has_year_season_at_the_end', True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_04(self) -> None:
        """ Test the function Fox.process_title with a simple movie. """

        # The expected result
        expected_result = 'Home By Spring'

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.process_title('Home By Spring',
                                                                            'has_year_season_at_the_end', True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_05(self) -> None:
        """ Test the function Fox.process_title with a simple series. """

        # The expected result
        expected_result = 'Private Practice'

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.process_title('Private Practice 1',
                                                                            'has_year_season_at_the_end', False)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_06(self) -> None:
        """ Test the function Fox.process_title with year in the title of the series. """

        # The expected result
        expected_result = 'New Amsterdam'

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.process_title('New Amsterdam (2018) 3',
                                                                            'has_year_season_at_the_end', False)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_07(self) -> None:
        """ Test the function Fox.process_title with re-release in the title of a movie. """

        # The expected result
        expected_result = 'Titanic'

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.process_title('Titanic (re-release 2012)',
                                                                            'has_year_season_at_the_end', True)

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
    def test_add_file_data_fox_comedy(self, tmdb_calls_mock) -> None:
        """ Test the function GenericXlsx.add_file_data with a sample from a FOX Comedy file. """

        # Prepare the mocks
        # Replace datetime class with a utility class with a fixed datetime
        datetime.datetime = NewDatetime

        # Prepare the call to get_channel_name
        channel_data = models.Channel('FOXCOM', 'FOX Comedy')
        channel_data.id = 8373

        db_calls_mock.get_channel_name.return_value = channel_data

        # Treatment of the entries
        # ----------------------------
        # Prepare the calls to search_channel_show_data
        db_calls_mock.search_channel_show_data_correction.side_effect = [None, None]

        # Prepare the calls to search_channel_show_data
        show_data = models.ShowData('_Black-ish_', 'Black-ish')
        show_data.id = 7503
        show_data.original_title = 'Black-ish'
        show_data.synopsis = 'Dre e Bow querem inscrever Kyra na escola Valley Glen Prep, mas ficam furiosos quando ' \
                             'a escola os trata como um caso de caridade. Entretanto, Junior quer ir trabalhar como ' \
                             'assistente de Josh na Stevens & Lido.'
        show_data.genre = 'Series'
        show_data.is_movie = False
        show_data.age_classification = '12+'

        show_data_2 = models.ShowData('_Doidos_à_Solta_de_Novo_', 'Doidos à Solta, de Novo')
        show_data_2.id = 7912
        show_data_2.original_title = 'Dumb and Dumber To'
        show_data_2.year = 2014
        show_data_2.synopsis = 'Vinte anos após a sua primeira aventura, Lloyd e Harry embarcam numa viagem para ' \
                               'encontrar a filha de Harry que havia sido dada para adoção.'
        show_data_2.genre = 'Movie'
        show_data_2.is_movie = True
        show_data_2.age_classification = '12+'

        db_calls_mock.insert_if_missing_show_data.side_effect = [(True, show_data), (True, show_data_2)]

        # Prepare the calls to search_shows_by_text
        tmdb_calls_mock.search_shows_by_text.side_effect = [(0, []), (0, []), (0, [])]

        # Prepare the calls to register_show_session
        show_session = models.ShowSession(1, 4, datetime.datetime(2021, 6, 1, 5, 6), 8373, 7503)
        show_session_2 = models.ShowSession(None, None, datetime.datetime(2021, 6, 27, 20, 8), 8373, 7912)

        db_calls_mock.register_show_session.side_effect = [show_session, show_session_2]

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.add_file_data(self.session,
                                                                            base_path + 'data/fox_comedy_example.xlsx',
                                                                            'FOX Comedy')

        # Get back the datetime.datetime
        datetime.datetime = self.datetime_backup

        # Verify the result
        self.assertEqual(datetime.datetime(2021, 6, 1, 5, 1, 0), actual_result.start_datetime)
        self.assertEqual(datetime.datetime(2021, 6, 27, 20, 13, 0), actual_result.end_datetime)
        self.assertEqual(2, actual_result.total_nb_sessions_in_file)
        self.assertEqual(0, actual_result.nb_updated_sessions)
        self.assertEqual(2, actual_result.nb_added_sessions)
        self.assertEqual(0, actual_result.nb_deleted_sessions)

        # Verify the calls to the mocks
        db_calls_mock.get_channel_name.assert_called_with(self.session, 'FOX Comedy')

        db_calls_mock.search_channel_show_data_correction.assert_has_calls(
            [unittest.mock.call(self.session, 8373, False, 'Black-ish', 'Black-ish', directors=None, year=2017,
                                subgenre=None, creators=['Kenya Barris']),
             unittest.mock.call(self.session, 8373, True, 'Dumb and Dumber To', 'Doidos à Solta, de Novo',
                                directors=['Bobby Farrelly', 'Peter Farrelly'], year=2014, subgenre=None,
                                creators=None)])

        db_calls_mock.insert_if_missing_show_data.assert_has_calls(
            [unittest.mock.call(self.session, 'Black-ish', cast='Anthony Anderson,Marcus Scribner,Tracee Ellis Ross',
                                original_title='Black-ish', duration=22,
                                synopsis='Dre e Bow querem inscrever Kyra na escola Valley Glen Prep, mas ficam '
                                         'furiosos quando a escola os trata como um caso de caridade. Entretanto, '
                                         'Junior quer ir trabalhar como assistente de Josh na Stevens & Lido.',
                                year=2017, genre='Series',
                                subgenre=None, audio_languages=None, countries=None,
                                directors=None, age_classification='12+', is_movie=False, season=5,
                                creators=['Kenya Barris']),
             unittest.mock.call(self.session, 'Doidos à Solta, de Novo', cast='Jeff Daniels,Jim Carrey,Rob Riggle',
                                original_title='Dumb and Dumber To', duration=111,
                                synopsis='Vinte anos após a sua primeira aventura, Lloyd e Harry embarcam numa viagem '
                                         'para encontrar a filha de Harry que havia sido dada para adoção.', year=2014,
                                genre='Movie', subgenre=None,
                                audio_languages=None, countries=None,
                                directors=['Bobby Farrelly', 'Peter Farrelly'], age_classification='12+', is_movie=True,
                                season=None,
                                creators=None)])

        tmdb_calls_mock.search_shows_by_text.assert_has_calls(
            [unittest.mock.call(self.session, 'Black-ish', is_movie=False, year=None),
             unittest.mock.call(self.session, 'Dumb and Dumber To', is_movie=True, year=2014),
             unittest.mock.call(self.session, 'Dumb and Dumber To', is_movie=True, year=None)])

        db_calls_mock.register_show_session.assert_has_calls(
            [unittest.mock.call(self.session, 5, 15, datetime.datetime(2021, 6, 1, 5, 6), 8373, 7503,
                                audio_language=None,
                                extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2021, 6, 27, 20, 8), 8373, 7912,
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

    @unittest.mock.patch('get_file_data.tmdb_calls')
    def test_add_file_data_mundo_fox(self, tmdb_calls_mock) -> None:
        """ Test the function GenericXlsx.add_file_data with a sample from a Mundo FOX file. """

        # Prepare the mocks
        # Replace datetime class with a utility class with a fixed datetime
        datetime.datetime = NewDatetime

        # Prepare the call to get_channel_name
        channel_data = models.Channel('MUNDOFOX', 'Mundo FOX')
        channel_data.id = 8373

        db_calls_mock.get_channel_name.return_value = channel_data

        # Treatment of the entries
        # ----------------------------
        # Prepare the calls to search_channel_show_data
        db_calls_mock.search_channel_show_data_correction.side_effect = [None, None]

        # Prepare the calls to search_channel_show_data
        show_data = models.ShowData('_Lei_&_Ordem_Unidade_Especial_', 'Lei & Ordem: Unidade Especial')
        show_data.id = 7503
        show_data.original_title = 'Law & Order: Special Victims Unit'
        show_data.synopsis = 'Uma investigação leva Benson ao limite quando um suspeito alega que a genética o ' \
                             'compele a cometer crimes de violação.'
        show_data.genre = 'Series'
        show_data.is_movie = False
        show_data.age_classification = '12+'

        show_data_2 = models.ShowData('_Robin_Hood_', 'Robin Hood')
        show_data_2.id = 7912
        show_data_2.original_title = 'Robin Hood'
        show_data_2.year = 2010
        show_data_2.synopsis = 'Inglaterra, século XIII. Robin Longstride (Russell Crowe) toda a sua vida prestou ' \
                               'serviço leal ao rei Ricardo I, de cognome Coração de Leão, mas hoje, após a morte do ' \
                               'grande soberano, o país atravessa uma grave crise nas mãos do Príncipe João (Oscar ' \
                               'Isaac) transformando Nottingham numa cidade saqueada não apenas pelos governantes ' \
                               'mas também pelo próprio xerife local (Matthew Macfadyen). Ao encontrar o amor em ' \
                               'Lady Marion (Cate Blanchett), na esperança de merecer a sua mão e salvar a população ' \
                               'de toda a iniquidade, ele vai criar um grupo de mercenários justiceiros, cujas ' \
                               'capacidades guerreiras só se poderão comparar à sua alegria de viver. Assim nascerá ' \
                               'a lenda de Robin Hood, o grande herói fora-da-lei que, roubando aos ricos para dar ' \
                               'aos pobres, devolveu a glória e a liberdade ao país que o viu nascer.'
        show_data_2.genre = 'Movie'
        show_data_2.is_movie = True
        show_data_2.age_classification = '12+'

        db_calls_mock.insert_if_missing_show_data.side_effect = [(True, show_data), (True, show_data_2)]

        # Prepare the calls to search_shows_by_text
        tmdb_calls_mock.search_shows_by_text.side_effect = [(0, []), (0, []), (0, [])]

        # Prepare the calls to register_show_session
        show_session = models.ShowSession(1, 4, datetime.datetime(2021, 7, 1, 5, 33), 8373, 7503)
        show_session_2 = models.ShowSession(None, None, datetime.datetime(2021, 7, 5, 8, 52), 8373, 7912)

        db_calls_mock.register_show_session.side_effect = [show_session, show_session_2]

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.add_file_data(self.session,
                                                                            base_path + 'data/mundo_fox_example.xlsx',
                                                                            'Mundo FOX')

        # Get back the datetime.datetime
        datetime.datetime = self.datetime_backup

        # Verify the result
        self.assertEqual(datetime.datetime(2021, 7, 1, 5, 28, 0), actual_result.start_datetime)
        self.assertEqual(datetime.datetime(2021, 7, 5, 8, 57, 0), actual_result.end_datetime)
        self.assertEqual(2, actual_result.total_nb_sessions_in_file)
        self.assertEqual(0, actual_result.nb_updated_sessions)
        self.assertEqual(2, actual_result.nb_added_sessions)
        self.assertEqual(0, actual_result.nb_deleted_sessions)

        # Verify the calls to the mocks
        db_calls_mock.get_channel_name.assert_called_with(self.session, 'Mundo FOX')

        db_calls_mock.search_channel_show_data_correction.assert_has_calls(
            [unittest.mock.call(self.session, 8373, False, 'Law & Order: Special Victims Unit',
                                'Lei & Ordem: Unidade Especial', directors=None, year=2016,
                                subgenre=None, creators=['Dick Wolf']),
             unittest.mock.call(self.session, 8373, True, 'Robin Hood', 'Robin Hood',
                                directors=['Ridley Scott'], year=2010, subgenre=None,
                                creators=None)])

        db_calls_mock.insert_if_missing_show_data.assert_has_calls(
            [unittest.mock.call(self.session, 'Lei & Ordem: Unidade Especial',
                                cast='Christopher Meloni,Ice-T,Mariska Hargitay',
                                original_title='Law & Order: Special Victims Unit', duration=None,
                                synopsis='Uma investigação leva Benson ao limite quando um suspeito alega que a '
                                         'genética o compele a cometer crimes de violação.',
                                year=2016, genre='Series', subgenre=None, audio_languages=None, countries=None,
                                directors=None, age_classification='12+', is_movie=False, season=18,
                                creators=['Dick Wolf']),
             unittest.mock.call(self.session, 'Robin Hood', cast='Cate Blanchett,Russell Crowe',
                                original_title='Robin Hood', duration=None,
                                synopsis='Inglaterra, século XIII. Robin Longstride (Russell Crowe) toda a sua vida '
                                         'prestou serviço leal ao rei Ricardo I, de cognome Coração de Leão, mas hoje, '
                                         'após a morte do grande soberano, o país atravessa uma grave crise nas mãos '
                                         'do Príncipe João (Oscar Isaac) transformando Nottingham numa cidade saqueada '
                                         'não apenas pelos governantes mas também pelo próprio xerife local (Matthew '
                                         'Macfadyen). Ao encontrar o amor em Lady Marion (Cate Blanchett), na '
                                         'esperança de merecer a sua mão e salvar a população de toda a iniquidade, '
                                         'ele vai criar um grupo de mercenários justiceiros, cujas capacidades '
                                         'guerreiras só se poderão comparar à sua alegria de viver. Assim nascerá a '
                                         'lenda de Robin Hood, o grande herói fora-da-lei que, roubando aos ricos para '
                                         'dar aos pobres, devolveu a glória e a liberdade ao país que o viu nascer.',
                                year=2010,
                                genre='Movie', subgenre=None, audio_languages=None, countries=None,
                                directors=['Ridley Scott'], age_classification='12+', is_movie=True,
                                season=None, creators=None)])

        tmdb_calls_mock.search_shows_by_text.assert_has_calls(
            [unittest.mock.call(self.session, 'Law & Order: Special Victims Unit', is_movie=False, year=None),
             unittest.mock.call(self.session, 'Robin Hood', is_movie=True, year=2010),
             unittest.mock.call(self.session, 'Robin Hood', is_movie=True, year=None)])

        db_calls_mock.register_show_session.assert_has_calls(
            [unittest.mock.call(self.session, 18, 14, datetime.datetime(2021, 7, 1, 5, 33), 8373, 7503,
                                audio_language=None,
                                extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2021, 7, 5, 8, 52), 8373, 7912,
                                audio_language=None, extended_cut=False, should_commit=False)])

    @unittest.mock.patch('get_file_data.tmdb_calls')
    def test_add_file_data_fox_life(self, tmdb_calls_mock) -> None:
        """ Test the function Fox.add_file_data with a sample from a FOX Life file. """

        # Prepare the mocks
        # Replace datetime class with a utility class with a fixed datetime
        datetime.datetime = NewDatetime

        # Prepare the call to get_channel_name
        channel_data = models.Channel('FLIFE', 'FOX Life')
        channel_data.id = 8373

        db_calls_mock.get_channel_name.return_value = channel_data

        # Treatment of the entries
        # ----------------------------
        # Prepare the calls to search_channel_show_data
        db_calls_mock.search_channel_show_data_correction.side_effect = [None, None]

        # Prepare the calls to search_channel_show_data
        show_data = models.ShowData('_Odd_Mom_Out_', 'Odd Mom Out')
        show_data.id = 7503
        show_data.original_title = 'Odd Mom Out'
        show_data.synopsis = 'Jill e Andy estão impressionados com o amadurecimento de Hazel quando a visitam num ' \
                             'campo de retiro, onde as vítimas do esquema Ponzi de Ernie Krevitt tentam lidar com a ' \
                             'sua nova realidade financeira.'
        show_data.creators = 'Jill Kargman'
        show_data.genre = 'Series'
        show_data.is_movie = False

        show_data_2 = models.ShowData('_Home_By_Spring_', 'Home By Spring')
        show_data_2.id = 7912
        show_data_2.original_title = 'Home By Spring'
        show_data_2.year = 2018
        show_data_2.synopsis = 'Uma organizadora de eventos ambiciosa tem uma oportunidade única e vai no lugar da ' \
                               'sua chefe e volta à sua terra natal numa zona rural. Com a ajuda da sua família e do ' \
                               'homem que deixou para trás, ela cria o retiro perfeito de primavera, mas irá ' \
                               'descobrir que aquilo de que precisa estava muito mais próximo do que imaginava?'
        show_data_2.cast = 'Poppy Drayton,Steven R. McQueen'
        show_data_2.director = 'Dwight H. Little'
        show_data_2.genre = 'Movie'
        show_data_2.is_movie = True

        db_calls_mock.insert_if_missing_show_data.side_effect = [(True, show_data), (True, show_data_2)]

        # Prepare the calls to search_shows_by_text
        tmdb_show = tmdb_calls.TmdbShow()
        tmdb_show.year = 2015
        tmdb_show.is_movie = False
        tmdb_show.id = 1
        tmdb_show.original_title = 'Odd Mom Out'

        tmdb_show_2 = tmdb_calls.TmdbShow()
        tmdb_show_2.year = 2018
        tmdb_show_2.is_movie = True
        tmdb_show_2.id = 112
        tmdb_show_2.original_title = 'Home By Spring'

        tmdb_calls_mock.search_shows_by_text.side_effect = [(1, [tmdb_show]), (1, [tmdb_show_2])]

        # Prepare the calls to get_show_using_id - for the first entry
        show_details = tmdb_calls.TmdbShow()
        show_details.creators = ['Other Person', 'Jill Kargman']

        tmdb_calls_mock.get_show_using_id.return_value = show_details

        # Prepare the calls to get_show_data_tmdb_id
        db_calls_mock.get_show_data_tmdb_id.side_effect = [None, None]

        # Prepare the calls to register_show_session
        show_session = models.ShowSession(3, 1, datetime.datetime(2021, 6, 1, 5), 8373, 7503)
        show_session_2 = models.ShowSession(None, None, datetime.datetime(2021, 6, 1, 7, 19), 8373, 7912)

        db_calls_mock.register_show_session.side_effect = [show_session, show_session_2]

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.add_file_data(self.session,
                                                                            base_path + 'data/fox_life_example.xlsx',
                                                                            'FOX Life')

        # Get back the datetime.datetime
        datetime.datetime = self.datetime_backup

        # Verify the result
        self.assertEqual(datetime.datetime(2021, 6, 1, 4, 55, 0), actual_result.start_datetime)
        self.assertEqual(datetime.datetime(2021, 6, 1, 7, 24, 0), actual_result.end_datetime)
        self.assertEqual(2, actual_result.total_nb_sessions_in_file)
        self.assertEqual(0, actual_result.nb_updated_sessions)
        self.assertEqual(2, actual_result.nb_added_sessions)
        self.assertEqual(0, actual_result.nb_deleted_sessions)

        # Verify the calls to the mocks
        db_calls_mock.get_channel_name.assert_called_with(self.session, 'FOX Life')

        db_calls_mock.search_channel_show_data_correction.assert_has_calls(
            [unittest.mock.call(self.session, 8373, False, 'Odd Mom Out', 'Odd Mom Out', directors=None, year=2017,
                                subgenre=None, creators=['Jill Kargman']),
             unittest.mock.call(self.session, 8373, True, 'Home By Spring', 'Home By Spring',
                                directors=['Dwight H. Little'], year=2018, subgenre=None, creators=None)])

        db_calls_mock.insert_if_missing_show_data.assert_has_calls(
            [unittest.mock.call(self.session, 'Odd Mom Out', cast='Andy Buckley,Jill Kargman',
                                original_title='Odd Mom Out', duration=10,
                                synopsis='Jill e Andy estão impressionados com o amadurecimento de Hazel quando a '
                                         'visitam num campo de retiro, onde as vítimas do esquema Ponzi de Ernie '
                                         'Krevitt tentam lidar com a sua nova realidade financeira.',
                                year=2017, genre='Series', subgenre=None, audio_languages=None, countries=None,
                                directors=None, age_classification='12+', is_movie=False, season=3,
                                creators=['Jill Kargman']),
             unittest.mock.call(self.session, 'Home By Spring', cast='Poppy Drayton,Steven R. McQueen',
                                original_title='Home By Spring', duration=87,
                                synopsis='Uma organizadora de eventos ambiciosa tem uma oportunidade única e vai no '
                                         'lugar da sua chefe e volta à sua terra natal numa zona rural. Com a ajuda '
                                         'da sua família e do homem que deixou para trás, ela cria o retiro perfeito '
                                         'de primavera, mas irá descobrir que aquilo de que precisa estava muito mais '
                                         'próximo do que imaginava?',
                                year=2018, genre='Movie', subgenre=None, audio_languages=None, countries=None,
                                directors=['Dwight H. Little'], age_classification='12+', is_movie=True, season=None,
                                creators=None)])

        tmdb_calls_mock.search_shows_by_text.assert_has_calls(
            [unittest.mock.call(self.session, 'Odd Mom Out', is_movie=False, year=None),
             unittest.mock.call(self.session, 'Home By Spring', is_movie=True, year=2018)])

        tmdb_calls_mock.get_show_using_id.assert_called_with(self.session, 1, False)

        db_calls_mock.get_show_data_tmdb_id.assert_has_calls(
            [unittest.mock.call(self.session, 1),
             unittest.mock.call(self.session, 112)])

        db_calls_mock.register_show_session.assert_has_calls(
            [unittest.mock.call(self.session, 3, 1, datetime.datetime(2021, 6, 1, 5), 8373, 7503, audio_language=None,
                                extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2021, 6, 1, 7, 19), 8373, 7912,
                                audio_language=None, extended_cut=False, should_commit=False)])

    @unittest.mock.patch('get_file_data.tmdb_calls')
    def test_add_file_data_fox(self, tmdb_calls_mock) -> None:
        """ Test the function Fox.add_file_data with a sample from a FOX file. """

        # Prepare the mocks
        # Replace datetime class with a utility class with a fixed datetime
        datetime.datetime = NewDatetime

        # Prepare the call to get_channel_name
        channel_data = models.Channel('FOX', 'FOX')
        channel_data.id = 8373

        db_calls_mock.get_channel_name.return_value = channel_data

        # Treatment of the entries
        # ----------------------------
        # Prepare the calls to search_channel_show_data
        db_calls_mock.search_channel_show_data_correction.side_effect = [None, None]

        # Prepare the calls to search_channel_show_data
        show_data = models.ShowData('_MacGyver_', 'MacGyver')
        show_data.id = 7503
        show_data.original_title = 'MacGyver'
        show_data.synopsis = 'Quando estavam em missão em busca de uma pista sobre o Codex, Mac e a equipa descobrem ' \
                             'que Murdoc hackeou os seus comunicadores e tem gravado as suas interações há meses. ' \
                             'Agora, Mac e a equipa têm de deter Murdoc, que está a trabalhar com Andrews, num ' \
                             'momento em que eles planeiam matar milhares de pessoas e revelar os segredos mais ' \
                             'bem guardados de todos os membros da Phoenix.'
        show_data.cast = 'Lucas Till'
        show_data.genre = 'Series'
        show_data.is_movie = False

        show_data_2 = models.ShowData('_Safe_O_Intocavel_', 'Safe - O Intocável')
        show_data_2.id = 7912
        show_data_2.original_title = 'Safe'
        show_data_2.year = 2012
        show_data_2.synopsis = 'Mei, uma menina cuja memória contém um código numérico de valor inestimável, vê-se ' \
                               'perseguida pelas Tríades, pela máfia russa e pelos polícias corruptos de Nova ' \
                               'Iorque. Em seu auxílio está um ex-lutador cuja vida foi destruída pelos gangsters ' \
                               'que andam atrás de Mei.'
        show_data_2.cast = 'Catherine Chan,Chris Sarandon,Jason Statham'
        show_data_2.director = 'Boaz Yakin'
        show_data_2.genre = 'Movie'
        show_data_2.is_movie = True

        db_calls_mock.insert_if_missing_show_data.side_effect = [(True, show_data), (True, show_data_2)]

        # Prepare the calls to search_shows_by_text
        tmdb_show = tmdb_calls.TmdbShow()
        tmdb_show.year = 2015
        tmdb_show.is_movie = False
        tmdb_show.id = 1
        tmdb_show.original_title = 'MacGyver'

        tmdb_show_2 = tmdb_calls.TmdbShow()
        tmdb_show_2.year = 2012
        tmdb_show_2.is_movie = True
        tmdb_show_2.id = 112
        tmdb_show_2.original_title = 'Safe'

        tmdb_calls_mock.search_shows_by_text.side_effect = [(1, [tmdb_show]), (1, [tmdb_show_2])]

        # Prepare the calls to get_show_data_tmdb_id
        db_calls_mock.get_show_data_tmdb_id.side_effect = [None, None]

        # Prepare the calls to register_show_session
        show_session = models.ShowSession(3, 1, datetime.datetime(2021, 6, 1, 21, 15), 8373, 7503)
        show_session_2 = models.ShowSession(None, None, datetime.datetime(2021, 6, 1, 22, 4), 8373, 7912)

        db_calls_mock.register_show_session.side_effect = [show_session, show_session_2]

        # Call the function
        actual_result = file_parsers.generic_xlsx.GenericXlsx.add_file_data(self.session,
                                                                            base_path + 'data/fox_example.xlsx', 'FOX')

        # Get back the datetime.datetime
        datetime.datetime = self.datetime_backup

        # Verify the result
        self.assertEqual(datetime.datetime(2021, 6, 1, 21, 10, 0), actual_result.start_datetime)
        self.assertEqual(datetime.datetime(2021, 6, 1, 22, 9, 0), actual_result.end_datetime)
        self.assertEqual(2, actual_result.total_nb_sessions_in_file)
        self.assertEqual(0, actual_result.nb_updated_sessions)
        self.assertEqual(2, actual_result.nb_added_sessions)
        self.assertEqual(0, actual_result.nb_deleted_sessions)

        # Verify the calls to the mocks
        db_calls_mock.get_channel_name.assert_called_with(self.session, 'FOX')

        db_calls_mock.search_channel_show_data_correction.assert_has_calls(
            [unittest.mock.call(self.session, 8373, False, 'MacGyver', 'MacGyver', directors=None, year=2020,
                                subgenre=None, creators=None),
             unittest.mock.call(self.session, 8373, True, 'Safe', 'Safe - O Intocável',
                                directors=['Boaz Yakin'], year=2012, subgenre=None, creators=None)])

        db_calls_mock.insert_if_missing_show_data.assert_has_calls(
            [unittest.mock.call(self.session, 'MacGyver', cast='Lucas Till',
                                original_title='MacGyver', duration=48,
                                synopsis='Quando estavam em missão em busca de uma pista sobre o Codex, Mac e a '
                                         'equipa descobrem que Murdoc hackeou os seus comunicadores e tem gravado '
                                         'as suas interações há meses. Agora, Mac e a equipa têm de deter Murdoc, '
                                         'que está a trabalhar com Andrews, num momento em que eles planeiam matar '
                                         'milhares de pessoas e revelar os segredos mais bem guardados de todos os '
                                         'membros da Phoenix.',
                                year=2020, genre='Series', subgenre=None, audio_languages=None, countries=None,
                                directors=None, age_classification='12+', is_movie=False, season=5,
                                creators=None),
             unittest.mock.call(self.session, 'Safe - O Intocável', cast='Catherine Chan,Chris Sarandon,Jason Statham',
                                original_title='Safe', duration=99,
                                synopsis='Mei, uma menina cuja memória contém um código numérico de valor '
                                         'inestimável, vê-se perseguida pelas Tríades, pela máfia russa e pelos '
                                         'polícias corruptos de Nova Iorque. Em seu auxílio está um ex-lutador cuja '
                                         'vida foi destruída pelos gangsters que andam atrás de Mei.',
                                year=2012, genre='Movie', subgenre=None, audio_languages=None, countries=None,
                                directors=['Boaz Yakin'], age_classification='18+', is_movie=True, season=None,
                                creators=None)])

        tmdb_calls_mock.search_shows_by_text.assert_has_calls(
            [unittest.mock.call(self.session, 'MacGyver', is_movie=False, year=None),
             unittest.mock.call(self.session, 'Safe', is_movie=True, year=2012)])

        db_calls_mock.get_show_data_tmdb_id.assert_has_calls(
            [unittest.mock.call(self.session, 1),
             unittest.mock.call(self.session, 112)])

        db_calls_mock.register_show_session.assert_has_calls(
            [unittest.mock.call(self.session, 5, 10, datetime.datetime(2021, 6, 1, 21, 15), 8373, 7503,
                                audio_language=None,
                                extended_cut=False, should_commit=False),
             unittest.mock.call(self.session, None, None, datetime.datetime(2021, 6, 1, 22, 4), 8373, 7912,
                                audio_language=None, extended_cut=False, should_commit=False)])
