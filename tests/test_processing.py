import datetime
import unittest.mock
from typing import Type

import globalsub
import sqlalchemy.orm

import configuration
import db_calls
import models
import process_emails
import processing
import response_models
import tmdb_calls

# Prepare the mock variables for the modules
db_calls_mock = unittest.mock.MagicMock()
process_emails_mock = unittest.mock.MagicMock()
tmdb_calls_mock = unittest.mock.MagicMock()


# This class allows us to set a fake date as the today date in datetime
# Remark: they need to be set and then reset
class NewDate(datetime.date):
    @classmethod
    def today(cls):
        return datetime.date(2021, 3, 10)


class TestProcessing(unittest.TestCase):
    session: sqlalchemy.orm.Session

    date_backup: Type[datetime.date]

    def setUp(self) -> None:
        self.session = unittest.mock.MagicMock()
        configuration.cache_validity_days = 1

        # Save the datetime.date
        self.date_backup = datetime.date

    def tearDown(self) -> None:
        # Reset the datetime class to work normally
        datetime.date = self.date_backup

    @classmethod
    def setUpClass(cls) -> None:
        global db_calls_mock, process_emails_mock, tmdb_calls_mock

        # Replace all references to the modules with mocks
        globalsub.subs(db_calls, db_calls_mock)
        globalsub.subs(process_emails, process_emails_mock)
        globalsub.subs(tmdb_calls, tmdb_calls_mock)

    @classmethod
    def tearDownClass(cls) -> None:
        # Replace back all references to the mocked modules
        globalsub.restore(db_calls)
        globalsub.restore(process_emails)
        globalsub.restore(tmdb_calls)

    def test_process_alarms_ok_01(self) -> None:
        """ Test the function process_alarms without alarms. """

        # Prepare the mocks
        db_calls_mock.get_alarms.return_value = []

        original_datetime = datetime.datetime(2020, 8, 1, 9)
        last_update = models.LastUpdate(None, original_datetime)

        db_calls_mock.get_last_update.return_value = last_update

        db_calls_mock.commit.return_value = [True]

        # Call the function
        processing.process_alarms(self.session)

        # Verify the result
        self.assertTrue(last_update.alarms_datetime > original_datetime)

        # Verify the calls to the mocks
        db_calls_mock.get_alarms.assert_called_with(self.session)

        db_calls_mock.get_last_update.assert_called_with(self.session)

        db_calls_mock.commit.assert_called_with(self.session)

    def test_process_alarms_ok_02(self) -> None:
        """ Test the function process_alarms with an alarm that gets two matches. """

        # 1 - Prepare the mocks
        # The db_calls.get_user_id in process_alarms
        user = models.User('email', 'pasword', 'pt')
        user.id = 933

        db_calls_mock.get_user_id.return_value = user

        # The db_calls.get_alarms in process_alarms
        alarm = models.Alarm(None, 123, True, response_models.AlarmType.DB.value, None, None, 933)

        db_calls_mock.get_alarms.return_value = [alarm]

        # The db_calls.get_show_titles in get_show_titles
        show_titles = models.ShowTitles(123, True, 'Title 1|Title 2')
        show_titles.insertion_datetime = datetime.datetime.utcnow() - datetime.timedelta(hours=3)

        db_calls_mock.get_show_titles.return_value = show_titles

        # The db_calls.get_last_update in process_alarms -> search_sessions_db_with_tmdb_id ->
        # get_last_update_alarms_datetime
        original_datetime = datetime.datetime(2020, 8, 1, 9)
        last_update = models.LastUpdate(None, original_datetime)

        db_calls_mock.get_last_update.return_value = last_update

        # The db_calls.search_show_sessions_data_with_tmdb_id in process_alarms -> search_sessions_db_with_tmdb_id
        channel = models.Channel('CH', 'Channel')
        channel.id = 76

        show_data = models.ShowData('search title', 'Título')
        show_data.id = 27
        show_data.tmdb_id = 123

        show_session = models.ShowSession(None, None, original_datetime + datetime.timedelta(days=2), 76, 27)
        show_session.update_timestamp = datetime.datetime.utcnow() + datetime.timedelta(hours=38)

        db_calls_mock.search_show_sessions_data_with_tmdb_id.return_value = [(show_session, channel, show_data)]

        # The db_calls.get_user_excluded_channels in process_alarms -> search_sessions_db_with_tmdb_id
        channel_2 = models.Channel('CH2', 'Channel 2')
        channel_2.id = 981

        user_excluded_channel = models.UserExcludedChannel(933, 981)

        db_calls_mock.get_user_excluded_channels.return_value = [user_excluded_channel]

        # The db_calls.get_last_update in process_alarms -> search_sessions_db -> get_last_update_alarms_datetime
        # has been done with return_value

        # The db_calls.get_user_excluded_channels in process_alarms -> search_sessions_db
        db_calls_mock.get_user_excluded_channels.return_value = [user_excluded_channel]

        # The db_calls.search_show_sessions_data in process_alarms -> search_sessions_db for 'Title 1'
        show_session_2 = models.ShowSession(None, None, original_datetime + datetime.timedelta(days=3), 76, 27)
        show_session_2.update_timestamp = datetime.datetime.utcnow() + datetime.timedelta(hours=38)

        db_calls_mock.search_show_sessions_data.side_effect = [[(show_session_2, channel, show_data)], []]

        # The db_calls.search_show_sessions_data in process_alarms -> search_sessions_db
        # for 'Title 1' has been done with side_effect

        # The process_emails.set_language in process_alarms is void

        # The process_emails.send_alarms_email in process_alarms
        process_emails_mock.send_alarms_email.return_value = True

        # The db_calls.get_last_update in process_alarms has been done with return_value

        # The db_calls.commit in process_alarms
        db_calls_mock.commit.return_value = True

        # 2 - Call the function
        processing.process_alarms(self.session)

        # 3 - Verify the results
        self.assertTrue(last_update.alarms_datetime > original_datetime)

        # Verify the calls to the mocks
        db_calls_mock.get_user_id.assert_called_with(self.session, 933)

        db_calls_mock.get_alarms.assert_called_with(self.session)

        db_calls_mock.get_show_titles.assert_called_with(self.session, 123, True)

        db_calls_mock.get_last_update.assert_has_calls([unittest.mock.call(self.session),
                                                        unittest.mock.call(self.session),
                                                        unittest.mock.call(self.session)])

        db_calls_mock.search_show_sessions_data_with_tmdb_id.assert_called_with(self.session, 123, True, None, None,
                                                                                below_datetime=original_datetime)

        db_calls_mock.get_user_excluded_channels.assert_has_calls([unittest.mock.call(self.session, 933),
                                                                   unittest.mock.call(self.session, 933)])

        db_calls_mock.search_show_sessions_data.assert_has_calls([unittest.mock.call(self.session, '_Title_1_', True,
                                                                                     None, None, False, True,
                                                                                     below_datetime=original_datetime,
                                                                                     ignore_with_tmdb_id=True),
                                                                  unittest.mock.call(self.session, '_Title_2_', True,
                                                                                     None, None, False, True,
                                                                                     below_datetime=original_datetime,
                                                                                     ignore_with_tmdb_id=True)])

        process_emails_mock.set_language.assert_called_with('pt')

        send_alarms_email_calls = process_emails_mock.send_alarms_email.call_args_list

        self.assertEqual(1, len(send_alarms_email_calls))

        call_args, _ = send_alarms_email_calls[0]

        self.assertEqual('email', call_args[0])

        actual_results = call_args[1]

        self.assertEqual(2, len(actual_results))

        self.assertEqual(response_models.LocalShowResultType.TV, actual_results[0].type)
        self.assertEqual('Título', actual_results[0].show_name)
        self.assertEqual('Channel', actual_results[0].service_name)
        self.assertEqual(original_datetime + datetime.timedelta(days=2), actual_results[0].date_time)

        self.assertEqual(response_models.LocalShowResultType.TV, actual_results[1].type)
        self.assertEqual('Título', actual_results[1].show_name)
        self.assertEqual('Channel', actual_results[1].service_name)
        self.assertEqual(original_datetime + datetime.timedelta(days=3), actual_results[1].date_time)

        db_calls_mock.commit.assert_called_with(self.session)

    def test_process_alarms_ok_03(self) -> None:
        """ Test the function process_alarms with an alarm that gets two matches, but both from an excluded channel. """

        # 1 - Prepare the mocks
        # The db_calls.get_user_id in process_alarms
        user = models.User('email', 'pasword', 'pt')
        user.id = 933

        db_calls_mock.get_user_id.return_value = user

        # The db_calls.get_alarms in process_alarms
        alarm = models.Alarm(None, 123, True, response_models.AlarmType.DB.value, None, None, 933)

        db_calls_mock.get_alarms.return_value = [alarm]

        # The db_calls.get_show_titles in get_show_titles
        show_titles = models.ShowTitles(123, True, 'Title 1|Title 2')
        show_titles.insertion_datetime = datetime.datetime.utcnow() - datetime.timedelta(hours=3)

        db_calls_mock.get_show_titles.return_value = show_titles

        # The db_calls.get_last_update in process_alarms -> search_sessions_db_with_tmdb_id ->
        # get_last_update_alarms_datetime
        original_datetime = datetime.datetime(2020, 8, 1, 9)
        last_update = models.LastUpdate(None, original_datetime)

        db_calls_mock.get_last_update.return_value = last_update

        # The db_calls.search_show_sessions_data_with_tmdb_id in process_alarms -> search_sessions_db_with_tmdb_id
        channel = models.Channel('CH', 'Channel')
        channel.id = 76

        show_data = models.ShowData('search title', 'Título')
        show_data.id = 27
        show_data.tmdb_id = 123

        show_session = models.ShowSession(None, None, original_datetime + datetime.timedelta(days=2), 76, 27)
        show_session.update_timestamp = datetime.datetime.utcnow() + datetime.timedelta(hours=38)

        db_calls_mock.search_show_sessions_data_with_tmdb_id.return_value = [(show_session, channel, show_data)]

        # The db_calls.get_user_excluded_channels in process_alarms -> search_sessions_db_with_tmdb_id
        user_excluded_channel = models.UserExcludedChannel(933, 76)

        db_calls_mock.get_user_excluded_channels.return_value = [user_excluded_channel]

        # The db_calls.get_last_update in process_alarms -> search_sessions_db -> get_last_update_alarms_datetime
        # has been done with return_value

        # The db_calls.get_user_excluded_channels in process_alarms -> search_sessions_db
        db_calls_mock.get_user_excluded_channels.return_value = [user_excluded_channel]

        # The db_calls.search_show_sessions_data in process_alarms -> search_sessions_db for 'Title 1'
        show_session_2 = models.ShowSession(None, None, original_datetime + datetime.timedelta(days=3), 76, 27)
        show_session_2.update_timestamp = datetime.datetime.utcnow() + datetime.timedelta(hours=38)

        db_calls_mock.search_show_sessions_data.side_effect = [[(show_session_2, channel, show_data)], []]

        # The db_calls.search_show_sessions_data in process_alarms -> search_sessions_db
        # for 'Title 1' has been done with side_effect

        # The db_calls.get_last_update in process_alarms has been done with return_value

        # The db_calls.commit in process_alarms
        db_calls_mock.commit.return_value = True

        # 2 - Call the function
        processing.process_alarms(self.session)

        # 3 - Verify the results
        self.assertTrue(last_update.alarms_datetime > original_datetime)

        # Verify the calls to the mocks
        db_calls_mock.get_user_id.assert_called_with(self.session, 933)

        db_calls_mock.get_alarms.assert_called_with(self.session)

        db_calls_mock.get_show_titles.assert_called_with(self.session, 123, True)

        db_calls_mock.get_last_update.assert_has_calls([unittest.mock.call(self.session),
                                                        unittest.mock.call(self.session),
                                                        unittest.mock.call(self.session)])

        db_calls_mock.search_show_sessions_data_with_tmdb_id.assert_called_with(self.session, 123, True, None, None,
                                                                                below_datetime=original_datetime)

        db_calls_mock.get_user_excluded_channels.assert_has_calls([unittest.mock.call(self.session, 933),
                                                                   unittest.mock.call(self.session, 933)])

        db_calls_mock.search_show_sessions_data.assert_has_calls([unittest.mock.call(self.session, '_Title_1_', True,
                                                                                     None, None, False, True,
                                                                                     below_datetime=original_datetime,
                                                                                     ignore_with_tmdb_id=True),
                                                                  unittest.mock.call(self.session, '_Title_2_', True,
                                                                                     None, None, False, True,
                                                                                     below_datetime=original_datetime,
                                                                                     ignore_with_tmdb_id=True)])

        db_calls_mock.commit.assert_called_with(self.session)

    def test_process_excluded_channel_list_ok_01(self) -> None:
        """ Test the function process_excluded_channel_list without changes to the current list. """

        # Prepare the mocks
        db_calls_mock.get_user_excluded_channels.return_value = [models.UserExcludedChannel(1, 10)]

        # Call the function
        processing.process_excluded_channel_list(self.session, 1, [10])

        # Verify the result
        # Verify the calls to the mocks
        db_calls_mock.get_user_excluded_channels.assert_called_with(self.session, 1)

    def test_process_excluded_channel_list_ok_02(self) -> None:
        """ Test the function process_excluded_channel_list with changes to the current list. """

        # Prepare the mocks
        excluded_channel = models.UserExcludedChannel(1, 10)
        db_calls_mock.get_user_excluded_channels.return_value = [excluded_channel]

        excluded_channel_2 = models.UserExcludedChannel(1, 15)
        db_calls_mock.register_user_excluded_channel.return_value = [excluded_channel, excluded_channel_2]

        # Call the function
        processing.process_excluded_channel_list(self.session, 1, [10, 15])

        # Verify the result
        # Verify the calls to the mocks
        db_calls_mock.get_user_excluded_channels.assert_called_with(self.session, 1)

        self.session.delete.assert_called_with(excluded_channel)

        db_calls_mock.register_user_excluded_channel.assert_has_calls(
            [unittest.mock.call(self.session, 1, 10, should_commit=False),
             unittest.mock.call(self.session, 1, 15, should_commit=False)])

    def test_get_settings_error(self) -> None:
        """ Test the function get_settings when the user is not found. """

        # Prepare the mocks
        db_calls_mock.get_user_id.return_value = None

        # Call the function
        processing.get_settings(self.session, 1)

        # Verify the result
        # Verify the calls to the mocks
        db_calls_mock.get_user_id.assert_called_with(self.session, 1)

    def test_get_settings_ok(self) -> None:
        """ Test the function get_settings when the user is not found. """

        # Expected results
        expected_result = {'include_adult_channels': False, 'language': 'pt', 'excluded_channel_list': [10, 15]}

        # Prepare the mocks
        user = models.User('email', 'password', 'pt')
        user.id = 1
        user.show_adult = False

        db_calls_mock.get_user_id.return_value = user

        excluded_channel = models.UserExcludedChannel(1, 10)
        excluded_channel_2 = models.UserExcludedChannel(1, 15)

        db_calls_mock.get_user_excluded_channels.return_value = [excluded_channel, excluded_channel_2]

        # Call the function
        actual_result = processing.get_settings(self.session, 1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        db_calls_mock.get_user_id.assert_called_with(self.session, 1)

        db_calls_mock.get_user_excluded_channels.assert_called_with(self.session, 1)

    def test_calculate_highlights_ok(self) -> None:
        """ Test the function calculate_highlights. """

        # Replace datetime class with a utility class with a fixed datetime
        datetime.date = NewDate

        # Prepare the mocks
        # Calls to check if the highlights already exist
        new_highlights_1 = models.Highlights(models.HighlightsType.NEW, 2021, 10, [1, 2], [None, 10])

        score_highlights_2 = models.Highlights(models.HighlightsType.SCORE, 2021, 11, [], None)

        db_calls_mock.get_week_highlights.side_effect = [None, new_highlights_1, score_highlights_2, None]

        # Call to obtains the shows of the week, for updating
        show_data = models.ShowData('Show 1', 'Show 1')
        show_data.tmdb_id = 1234
        show_data.tmdb_vote_average = 3
        show_data.tmdb_vote_count = 25
        show_data.is_movie = True
        show_data.year = 2020
        show_data.id = 189

        show_data_2 = models.ShowData('Show 2', 'Show 2')
        show_data_2.tmdb_id = 6789
        show_data_2.tmdb_vote_average = 6
        show_data_2.tmdb_vote_count = 25
        show_data_2.is_movie = True
        show_data_2.year = 2011
        show_data_2.id = 2

        show_data_3 = models.ShowData('Show 3', 'Show 3')
        show_data_3.tmdb_id = 1271
        show_data_3.tmdb_vote_average = 6
        show_data_3.tmdb_vote_count = 25
        show_data_3.is_movie = True
        show_data_3.year = 2004
        show_data_3.id = 3

        show_data_4 = models.ShowData('Show 4', 'Show 4')
        show_data_4.tmdb_id = 1274
        show_data_4.tmdb_vote_average = 5.4
        show_data_4.tmdb_vote_count = 25
        show_data_4.is_movie = False
        show_data_4.year = 2004
        show_data_4.id = 46
        show_data_4.season_premiere = 3

        db_calls_mock.get_shows_interval.side_effect = [[show_data, show_data_2, show_data_3, show_data_4]]

        # Calls to obtain the TMDB config for each of the shows
        tmdb_show = response_models.TmdbShow()
        tmdb_show.vote_average = 7
        tmdb_show.popularity = 100
        tmdb_show.vote_count = 25
        tmdb_show.id = 1234

        tmdb_show_2 = response_models.TmdbShow()
        tmdb_show_2.vote_average = 5
        tmdb_show_2.popularity = 34
        tmdb_show_2.vote_count = 25
        tmdb_show_2.id = 6789

        tmdb_show_3 = response_models.TmdbShow()
        tmdb_show_3.vote_average = 5.5
        tmdb_show_3.popularity = 123
        tmdb_show_3.vote_count = 25
        tmdb_show_3.id = 1274

        tmdb_calls_mock.get_show_using_id.side_effect = [tmdb_show, tmdb_show_2, tmdb_show_3]

        # Calls to get the highest scored shows
        db_calls_mock.get_highest_scored_shows_interval.side_effect = [[(189, 1234, 7)], [(46, 1274, 5.5)]]

        # Calls to get the new shows
        db_calls_mock.get_new_shows_interval.side_effect = [[(55, 42, datetime.date(2021, 3, 10), 5)], []]

        # Calls to register highlights
        new_score_highlights = models.Highlights(models.HighlightsType.SCORE, 2021, 10, [189, 46], None)

        new_new_highlights = models.Highlights(models.HighlightsType.NEW, 2021, 11, [55], [5])

        db_calls_mock.register_highlights.side_effect = [new_score_highlights, new_new_highlights]

        # Call the function
        processing.calculate_highlights(self.session)

        # Verify the calls to the mocks
        db_calls_mock.get_week_highlights.assert_has_calls(
            [unittest.mock.call(self.session, models.HighlightsType.SCORE, 2021, 10),
             unittest.mock.call(self.session, models.HighlightsType.NEW, 2021, 10),
             unittest.mock.call(self.session, models.HighlightsType.SCORE, 2021, 11),
             unittest.mock.call(self.session, models.HighlightsType.NEW, 2021, 11)])

        db_calls_mock.get_shows_interval.assert_called_with(self.session, datetime.datetime(2021, 3, 8),
                                                            datetime.datetime(2021, 3, 14, 23, 59, 59))

        tmdb_calls_mock.get_show_using_id.assert_has_calls(
            [unittest.mock.call(self.session, 1234, True),
             unittest.mock.call(self.session, 6789, True),
             unittest.mock.call(self.session, 1274, False)])

        db_calls_mock.get_highest_scored_shows_interval.assert_has_calls(
            [unittest.mock.call(self.session, datetime.datetime(2021, 3, 8),
                                datetime.datetime(2021, 3, 14, 23, 59, 59), True),
             unittest.mock.call(self.session, datetime.datetime(2021, 3, 8),
                                datetime.datetime(2021, 3, 14, 23, 59, 59), False)])

        db_calls_mock.get_new_shows_interval.assert_has_calls(
            [unittest.mock.call(self.session, datetime.datetime(2021, 3, 15),
                                datetime.datetime(2021, 3, 21, 23, 59, 59), True),
             unittest.mock.call(self.session, datetime.datetime(2021, 3, 15),
                                datetime.datetime(2021, 3, 21, 23, 59, 59), False)])

        db_calls_mock.register_highlights.assert_has_calls(
            [unittest.mock.call(self.session, models.HighlightsType.SCORE, 2021, 10, [189, 46]),
             unittest.mock.call(self.session, models.HighlightsType.NEW, 2021, 11, [55], [5])])

    def test_get_response_highlights_week_ok(self) -> None:
        """ Test the function get_response_highlights_week. """

        # Prepare the mocks
        # Calls to get the highlights
        score_highlights = models.Highlights(models.HighlightsType.SCORE, 2021, 2, [3], None)
        new_highlights = models.Highlights(models.HighlightsType.NEW, 2021, 2, [1, 2], [None, 10])

        db_calls_mock.get_week_highlights.side_effect = [score_highlights, new_highlights]

        # Calls to get the shows
        show_3 = models.ShowData("_Programa_3_", "Programa 3")
        show_3.id = 3
        show_3.tmdb_id = 3792
        show_3.synopsis = "Synopsis 3"
        show_3.is_movie = True
        show_3.original_title = "Show 3"

        show_1 = models.ShowData("_Programa_1_", "Programa 1")
        show_1.id = 1
        show_1.tmdb_id = 84
        show_1.synopsis = "Synopsis 1"
        show_1.is_movie = False
        show_1.original_title = "Show 1"

        show_2 = models.ShowData("_Programa_2_", "Programa 2")
        show_2.id = 2
        show_2.tmdb_id = 1111
        show_2.synopsis = "Synopsis 2"
        show_2.is_movie = False
        show_2.original_title = "Show 2"

        db_calls_mock.get_show_data_id.side_effect = [show_3, show_1, show_2]

        # Calls to obtain the TMDB config for each of the shows
        tmdb_show_3 = response_models.TmdbShow()
        tmdb_show_3.id = 3792
        tmdb_show_3.vote_average = 5.5
        tmdb_show_3.vote_count = 25
        tmdb_show_3.popularity = 123
        tmdb_show_3.original_title = "Show 3"
        tmdb_show_3.title = "Show 3"
        tmdb_show_3.is_movie = True
        tmdb_show_3.overview = "Overview 3"
        tmdb_show_3.original_language = "en"
        tmdb_show_3.match_reason = "Name"

        tmdb_show = response_models.TmdbShow()
        tmdb_show.id = 84
        tmdb_show.vote_average = 7
        tmdb_show.vote_count = 50
        tmdb_show.popularity = 100
        tmdb_show.original_title = "Show 1"
        tmdb_show.title = "Show 1"
        tmdb_show.is_movie = False
        tmdb_show.overview = "Overview 1"
        tmdb_show.original_language = "en"
        tmdb_show.match_reason = "Name"

        tmdb_show_2 = response_models.TmdbShow()
        tmdb_show_2.id = 1111
        tmdb_show_2.vote_average = 5
        tmdb_show_2.vote_count = 33
        tmdb_show_2.popularity = 34
        tmdb_show_2.original_title = "Show 2"
        tmdb_show_2.title = "Show 2"
        tmdb_show_2.is_movie = False
        tmdb_show_2.overview = "Overview 2"
        tmdb_show_2.original_language = "en"
        tmdb_show_2.match_reason = "Name"

        tmdb_calls_mock.get_show_using_id.side_effect = [tmdb_show_3, tmdb_show, tmdb_show_2]

        # Call the function
        actual_result = processing.get_response_highlights_week(self.session, 2021, 2)

        # Verify the calls to the mocks
        db_calls_mock.get_week_highlights.assert_has_calls(
            [unittest.mock.call(self.session, models.HighlightsType.SCORE, 2021, 2),
             unittest.mock.call(self.session, models.HighlightsType.NEW, 2021, 2)])

        db_calls_mock.get_show_data_id.assert_has_calls(
            [unittest.mock.call(self.session, 3),
             unittest.mock.call(self.session, 1),
             unittest.mock.call(self.session, 2)])

        tmdb_calls_mock.get_show_using_id.assert_has_calls(
            [unittest.mock.call(self.session, 3792, True),
             unittest.mock.call(self.session, 84, False),
             unittest.mock.call(self.session, 1111, False)])

        # Verify the result
        self.assertEqual(2, len(actual_result))

        self.assertEqual("SCORE", actual_result[0].key)
        self.assertEqual(2021, actual_result[0].year)
        self.assertEqual(2, actual_result[0].week)

        expected_show_3 = {'is_movie': True, 'show_title': 'Show 3', 'show_year': None, 'trakt_id': 3792,
                           'show_overview': "Synopsis 3", 'language': "en", 'vote_average': 5.5, 'vote_count': 25,
                           'popularity': 123, 'show_image': 'N/A', 'match_reason': 'Name',
                           'translated_title': 'Programa 3'}

        self.assertEqual(1, len(actual_result[0].show_list))
        self.assertEqual(expected_show_3, actual_result[0].show_list[0])

        self.assertEqual("NEW", actual_result[1].key)
        self.assertEqual(2021, actual_result[1].year)
        self.assertEqual(2, actual_result[1].week)

        self.assertEqual(2, len(actual_result[1].show_list))

        expected_show_1 = {'is_movie': False, 'show_title': 'Show 1', 'translated_title': 'Programa 1',
                           'show_year': None, 'trakt_id': 84, 'show_overview': "Synopsis 1", 'language': "en",
                           'vote_average': 7, 'vote_count': 50, 'popularity': 100, 'show_image': 'N/A',
                           'match_reason': 'Name'}

        self.assertEqual(expected_show_1, actual_result[1].show_list[0])

        expected_show_2 = {'is_movie': False, 'show_title': 'Show 2', 'translated_title': 'Programa 2',
                           'show_year': None, 'trakt_id': 1111, 'show_overview': "Synopsis 2", 'language': "en",
                           'vote_average': 5, 'vote_count': 33, 'popularity': 34, 'show_image': 'N/A',
                           'season_premiere': 10, 'match_reason': 'Name'}

        self.assertEqual(expected_show_2, actual_result[1].show_list[1])
