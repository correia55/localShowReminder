import datetime
import os
import sys
import unittest.mock
from typing import Type

import sqlalchemy.orm

import models

# Configure a mock for the configuration file
configuration_mock = unittest.mock.MagicMock()
sys.modules['configuration'] = configuration_mock

# Configure a mock for the db_calls file
db_calls_mock = unittest.mock.MagicMock()
sys.modules['db_calls'] = db_calls_mock

# Configure a mock for the process_emails file
process_emails_mock = unittest.mock.MagicMock()
sys.modules['process_emails'] = process_emails_mock

import tmdb_calls
import get_file_data

# To ensure the tests find the data folder no matter where it runs
if 'tests' in os.getcwd():
    base_path = ''
else:
    base_path = 'tests/'


# This class allows us to set a fake datetime as the today date in datetime
# Remark: they need to be set and then reset
class NewDatetime(datetime.datetime):
    @classmethod
    def utcnow(cls):
        return datetime.datetime(2021, 3, 1, 15, 13, 34)


class TestGetFileData(unittest.TestCase):
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        self.session = unittest.mock.MagicMock()

    def test_delete_old_sessions(self) -> None:
        """ Test the function delete_old_sessions. """

        # The expected result
        expected_result = 2

        # Prepare the mocks
        # Prepare the call to search_old_sessions
        show_session_1 = models.ShowSession(None, None, datetime.datetime(2020, 1, 1), 5, 10)
        show_session_1.id = 1

        show_session_2 = models.ShowSession(1, 10, datetime.datetime(2020, 2, 2), 8, 25)
        show_session_2.id = 2

        db_calls_mock.search_old_sessions.return_value = [show_session_1, show_session_2]

        # Prepare the call to get_reminders_session for session 1 and session 2
        reminder_1 = models.Reminder(10, 1, 7)
        reminder_1.id = 1

        reminder_2 = models.Reminder(50, 1, 4)
        reminder_2.id = 2

        reminders_session_1 = [reminder_1, reminder_2]
        reminders_session_2 = []

        db_calls_mock.get_reminders_session.side_effect = [reminders_session_1, reminders_session_2]

        # Prepare the call to get_show_session_complete for session 1
        channel = models.Channel(None, 'Channel Name')

        show_data = models.ShowData('_Show_Name_', 'Show Name')
        show_data.is_movie = True

        complete_session = (show_session_1, channel, show_data)

        db_calls_mock.get_show_session_complete.return_value = complete_session

        # Prepare the call to get_user_id for reminder 1 and reminder 2
        user_7 = models.User('user7@email.com', 'password', 'pt')
        user_7.id = 7

        user_4 = models.User('user4@email.com', 'password', 'pt')
        user_4.id = 4

        db_calls_mock.get_user_id.side_effect = [user_7, user_4]

        # Prepare the call to send_deleted_sessions_email for user 7 and user 4
        process_emails_mock.send_deleted_sessions_email.return_value = True

        # Call the function
        start_datetime = datetime.datetime.utcnow() - datetime.timedelta(days=2)
        end_datetime = datetime.datetime.utcnow()
        channels = ['Odisseia']

        actual_result = get_file_data.delete_old_sessions(self.session, start_datetime, end_datetime, channels)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        db_calls_mock.search_old_sessions.assert_called_with(self.session, start_datetime, end_datetime, channels)
        db_calls_mock.get_reminders_session.assert_has_calls(
            [unittest.mock.call(self.session, 1), unittest.mock.call(self.session, 2)])
        db_calls_mock.get_show_session_complete.assert_called_with(self.session, 1)
        db_calls_mock.get_user_id.assert_has_calls(
            [unittest.mock.call(self.session, 7), unittest.mock.call(self.session, 4)])
        process_emails_mock.send_deleted_sessions_email.assert_has_calls(
            [unittest.mock.call('user7@email.com', unittest.mock.ANY),
             unittest.mock.call('user4@email.com', unittest.mock.ANY)])
        self.session.delete.assert_has_calls(
            [unittest.mock.call(reminder_1), unittest.mock.call(reminder_2), unittest.mock.call(show_session_1),
             unittest.mock.call(show_session_2)])

    @unittest.mock.patch('get_file_data.tmdb_calls')
    def test_search_tmdb_match_01(self, tmdb_calls_mock) -> None:
        """ Test the function search_tmdb_match with a match on a query with year. """

        # The expected result
        expected_result = tmdb_calls.TmdbShow()
        expected_result.year = 2020
        expected_result.is_movie = True
        expected_result.id = 2
        expected_result.original_title = 'Original Title'

        # Prepare the mocks
        # Prepare the call to search_shows_by_text
        tmdb_show_1 = tmdb_calls.TmdbShow()
        tmdb_show_1.year = 2020
        tmdb_show_1.is_movie = True
        tmdb_show_1.id = 1
        tmdb_show_1.original_title = 'Similar Title'

        tmdb_calls_mock.search_shows_by_text.return_value = (1, [tmdb_show_1, expected_result])

        # Prepare the call to get_show_crew_members for the show 1
        tmdb_calls_mock.get_show_crew_members.return_value = []

        # Call the function
        show_data = models.ShowData('_search_title', 'Localized Title')
        show_data.director = 'Director 1,Director 2'
        show_data.year = 2020
        show_data.genre = 'Documentary'
        show_data.original_title = 'Original Title'
        show_data.is_movie = True

        actual_result = get_file_data.search_tmdb_match(self.session, show_data, use_year=True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        tmdb_calls_mock.search_shows_by_text.assert_called_with(self.session, 'Original Title', is_movie=True,
                                                                year=2020)

        tmdb_calls_mock.get_show_crew_members.assert_called_with(1, True)


class TestCinemundo(unittest.TestCase):
    session: sqlalchemy.orm.Session

    def test_Cinemundo_process_title_01(self) -> None:
        """ Test the function Cinemundo.process_title with nothing in particular. """

        # The expected result
        expected_result = ('Mortadela e Salamão: Missão Não Possível', True, None)

        # Call the function
        actual_result = get_file_data.Cinemundo.process_title('Mortadela e Salamão: Missão Não Possível VP')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_Cinemundo_process_title_02(self) -> None:
        """ Test the function Cinemundo.process_title with quotation marks. """

        # The expected result
        expected_result = ('Je m\'appelle Bernadette', False, None)

        # Call the function
        actual_result = get_file_data.Cinemundo.process_title('Je m´appelle Bernadette')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_Cinemundo_process_title_03(self) -> None:
        """ Test the function Cinemundo.process_title with season. """

        # The expected result
        expected_result = ('True Justice', False, 2)

        # Call the function
        actual_result = get_file_data.Cinemundo.process_title('True Justice S2: Vengeance is Mine')

        # Verify the result
        self.assertEqual(expected_result, actual_result)


class TestTvCine(unittest.TestCase):
    session: sqlalchemy.orm.Session

    def test_TVCine_process_title_01(self) -> None:
        """ Test the function TvCine.process_title with a title with "(VO)". """

        # The expected result
        expected_result = ('The Angry Birds Movie 2', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Angry Birds Movie 2, The (VO)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_02(self) -> None:
        """ Test the function TvCine.process_title with a title with "(VP)". """

        # The expected result
        expected_result = ('The Angry Birds Movie 2', True, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Angry Birds Movie 2, The (VP)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_03(self) -> None:
        """ Test the function TvCine.process_title with the year in the title. """

        # The expected result
        expected_result = ('Endings, Beginnings', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Endings, Beginnings (2019)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_04(self) -> None:
        """ Test the function TvCine.process_title with an inverted section at the end. """

        # The expected result
        expected_result = ('A Beautiful Day In The Neighborhood', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Beautiful Day In The Neighborhood, A')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_05(self) -> None:
        """ Test the function TvCine.process_title with year and "VO". """

        # The expected result
        expected_result = ('Abominable', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Abominable (2019) (VO)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_06(self) -> None:
        """ Test the function TvCine.process_title with year and "VP". """

        # The expected result
        expected_result = ('Abominable', True, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Abominable (2019) (VP)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_07(self) -> None:
        """ Test the function TvCine.process_title with year, "VP" and an inverted section. """

        # The expected result
        expected_result = ('The Addams Family', True, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Addams Family, The (2019) (VP)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_08(self) -> None:
        """ Test the function TvCine.process_title with the extended cut. """

        # The expected result
        expected_result = ('Furious 7', False, True)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Furious 7 (extended cut)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_09(self) -> None:
        """ Test the function TvCine.process_title with a quotation mark. """

        # The expected result
        expected_result = ('Child\'s Play', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Child`s Play (2019)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_10(self) -> None:
        """ Test the function TvCine.process_title with nothing in particular. """

        # The expected result
        expected_result = ('Birds Of Prey (And The Fantabulous Emancipation Of One Harley Quinn)', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title(
            'Birds Of Prey (And The Fantabulous Emancipation Of One Harley Quinn)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_11(self) -> None:
        """ Test the function TvCine.process_title with parts of the title switched but not at the end. """

        # The expected result
        expected_result = ('The Lost World : Jurassic Park', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Lost World, The: Jurassic Park')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_12(self) -> None:
        """ Test the function TvCine.process_title with parts of the title switched but not at the end. """

        # The expected result
        expected_result = ('Le Ninfee di Monet - Un Incantesimo di Acqua e Luce', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title(
            'Ninfee di Monet, Le - Un Incantesimo di Acqua e Luce')

        # Verify the result
        self.assertEqual(expected_result, actual_result)


class TestOdisseia(unittest.TestCase):
    session: sqlalchemy.orm.Session
    datetime_backup: Type[datetime.datetime]

    def setUp(self) -> None:
        self.session = unittest.mock.MagicMock()
        configuration_mock.show_sessions_validity_days = 7

        # Save the datetime.date
        self.datetime_backup = datetime.datetime

    def tearDown(self) -> None:
        # Reset the datetime class to work normally
        datetime.date = self.datetime_backup

    def test_Odisseia_process_title_01(self) -> None:
        """ Test the function Odisseia.process_title with nothing in particular. """

        # The expected result
        expected_result = 'Attack and Defend'

        # Call the function
        actual_result = get_file_data.Odisseia.process_title('Attack and Defend')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_Odisseia_process_title_02(self) -> None:
        """ Test the function Odisseia.process_title with quotation marks. """

        # The expected result
        expected_result = 'History\'s Greatest Lies'

        # Call the function
        actual_result = get_file_data.Odisseia.process_title('History´s Greatest Lies')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_Odisseia_add_file_data(self) -> None:
        """
        Test the function Odisseia.add_file_data with a new session of a show with a matching channel correction.
        An old event was added to show that nothing changes and it is ignored.
        """

        # Prepare the mocks
        # Replace datetime class with a utility class with a fixed today datetime
        datetime.datetime = NewDatetime

        # Prepare the call to get_channel_name
        channel_data = models.Channel('Acronym', 'Channel Name')
        channel_data.id = 8373

        db_calls_mock.get_channel_name.return_value = channel_data

        # Prepare the call to search_channel_show_data
        channel_show_data = models.ChannelShowData(8373, 2, False, 'Attack and Defend', 'Ataque e Defesa')
        channel_show_data.show_id = 51474

        db_calls_mock.search_channel_show_data_correction.return_value = channel_show_data

        # Prepare the call to get_show_data_id
        show_data = models.ShowData('Search Title', 'Localized Title')
        show_data.id = 51474

        db_calls_mock.get_show_data_id.return_value = show_data

        # Prepare the call to search_existing_session
        db_calls_mock.search_existing_session.return_value = None

        # Prepare the call to register_show_session
        show_session = models.ShowSession(1, 5, datetime.datetime(2021, 3, 19, 5, 15, 16), 8373, 51474)

        db_calls_mock.register_show_session.return_value = show_session

        # Prepare the call to search_old_sessions
        db_calls_mock.search_old_sessions.return_value = []

        # Call the function
        actual_result = get_file_data.Odisseia.add_file_data(self.session, base_path + 'data/odisseia_example.xml')

        # Verify the result
        self.assertEqual(datetime.datetime(2021, 3, 19, 5, 10, 16), actual_result.start_datetime)
        self.assertEqual(datetime.datetime(2021, 3, 19, 5, 20, 16), actual_result.end_datetime)
        self.assertEqual(1, actual_result.total_nb_sessions_in_file)
        self.assertEqual(0, actual_result.nb_updated_sessions)
        self.assertEqual(1, actual_result.nb_added_sessions)
        self.assertEqual(0, actual_result.nb_deleted_sessions)

        # Verify the calls to the mocks
        db_calls_mock.get_channel_name.assert_called_with(self.session, 'Odisseia')

        db_calls_mock.search_channel_show_data_correction.assert_called_with(self.session, 8373, False,
                                                                             'Attack and Defend', 'Ataque e Defesa',
                                                                             directors=['Seaton McLean'],
                                                                             year=2015, subgenre='Natureza',
                                                                             creators=None)

        db_calls_mock.get_show_data_id.assert_called_with(self.session, 51474)

        db_calls_mock.search_existing_session.assert_called_with(self.session, 1, 5,
                                                                 datetime.datetime(2021, 3, 19, 5, 15, 16), 8373, 51474)

        db_calls_mock.register_show_session.assert_called_with(self.session, 1, 5,
                                                               datetime.datetime(2021, 3, 19, 5, 15, 16), 8373, 51474,
                                                               audio_language=None, extended_cut=False,
                                                               should_commit=False)

        db_calls_mock.search_old_sessions.assert_called_with(self.session, datetime.datetime(2021, 3, 19, 5, 10, 16),
                                                             datetime.datetime(2021, 3, 19, 5, 20, 16), ['Odisseia'])


class TestFoxLife(unittest.TestCase):
    session: sqlalchemy.orm.Session

    def test_process_title_01(self) -> None:
        """ Test the function FoxLife.process_title with a simple movie. """

        # The expected result
        expected_result = 'Home By Spring'

        # Call the function
        actual_result = get_file_data.FoxLife.process_title('Home By Spring', True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_02(self) -> None:
        """ Test the function FoxLife.process_title with a simple series. """

        # The expected result
        expected_result = 'Private Practice'

        # Call the function
        actual_result = get_file_data.FoxLife.process_title('Private Practice 1', False)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_03(self) -> None:
        """ Test the function FoxLife.process_title with year in the title of the series. """

        # The expected result
        expected_result = 'New Amsterdam'

        # Call the function
        actual_result = get_file_data.FoxLife.process_title('New Amsterdam (2018) 3', False)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_04(self) -> None:
        """ Test the function FoxLife.process_title with re-release in the title of a movie. """

        # The expected result
        expected_result = 'Titanic'

        # Call the function
        actual_result = get_file_data.FoxLife.process_title('Titanic (re-release 2012)', True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)


if __name__ == '__main__':
    unittest.main()
