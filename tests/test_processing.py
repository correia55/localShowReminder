import datetime
import sys
import unittest.mock

import sqlalchemy.orm

import models
import response_models

# Configure a mock for the db_calls file
configuration_mock = unittest.mock.MagicMock()
sys.modules['configuration'] = configuration_mock

# These are still needed to prevent the problems with the reading of the configuration
# Configure a mock for the db_calls file
db_calls_mock = unittest.mock.MagicMock()
sys.modules['db_calls'] = db_calls_mock

# Configure a mock for the process_emails file
process_emails_mock = unittest.mock.MagicMock()
sys.modules['process_emails'] = process_emails_mock

import processing


class TestProcessing(unittest.TestCase):
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        self.session = unittest.mock.MagicMock()
        configuration_mock.cache_validity_days = 1

    @unittest.mock.patch('processing.db_calls')
    def test_process_alarms_ok_01(self, db_calls_mock) -> None:
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

    @unittest.mock.patch('processing.db_calls')
    @unittest.mock.patch('processing.process_emails')
    def test_process_alarms_ok_02(self, process_emails_mock, db_calls_mock) -> None:
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
        show_titles = models.ShowTitles(123, 'Title 1|Title 2')
        show_titles.insertion_datetime = datetime.datetime.now() - datetime.timedelta(hours=3)

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
        show_session.update_timestamp = datetime.datetime.now() + datetime.timedelta(hours=38)

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
        show_session_2.update_timestamp = datetime.datetime.now() + datetime.timedelta(hours=38)

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

        db_calls_mock.get_show_titles.assert_called_with(self.session, 123)

        db_calls_mock.get_last_update.assert_has_calls([unittest.mock.call(self.session),
                                                        unittest.mock.call(self.session),
                                                        unittest.mock.call(self.session)])

        db_calls_mock.search_show_sessions_data_with_tmdb_id.assert_called_with(self.session, 123, None, None,
                                                                                below_datetime=original_datetime)

        db_calls_mock.get_user_excluded_channels.assert_has_calls([unittest.mock.call(self.session, 933),
                                                                   unittest.mock.call(self.session, 933)])

        db_calls_mock.search_show_sessions_data.assert_has_calls([unittest.mock.call(self.session, '_Title_1_', True,
                                                                                     None, None, False, True,
                                                                                     below_datetime=original_datetime,
                                                                                     ignore_with_tmdb_id=False),
                                                                  unittest.mock.call(self.session, '_Title_2_', True,
                                                                                     None, None, False, True,
                                                                                     below_datetime=original_datetime,
                                                                                     ignore_with_tmdb_id=False)])

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

    @unittest.mock.patch('processing.db_calls')
    def test_process_alarms_ok_03(self, db_calls_mock) -> None:
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
        show_titles = models.ShowTitles(123, 'Title 1|Title 2')
        show_titles.insertion_datetime = datetime.datetime.now() - datetime.timedelta(hours=3)

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
        show_session.update_timestamp = datetime.datetime.now() + datetime.timedelta(hours=38)

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
        show_session_2.update_timestamp = datetime.datetime.now() + datetime.timedelta(hours=38)

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

        db_calls_mock.get_show_titles.assert_called_with(self.session, 123)

        db_calls_mock.get_last_update.assert_has_calls([unittest.mock.call(self.session),
                                                        unittest.mock.call(self.session),
                                                        unittest.mock.call(self.session)])

        db_calls_mock.search_show_sessions_data_with_tmdb_id.assert_called_with(self.session, 123, None, None,
                                                                                below_datetime=original_datetime)

        db_calls_mock.get_user_excluded_channels.assert_has_calls([unittest.mock.call(self.session, 933),
                                                                   unittest.mock.call(self.session, 933)])

        db_calls_mock.search_show_sessions_data.assert_has_calls([unittest.mock.call(self.session, '_Title_1_', True,
                                                                                     None, None, False, True,
                                                                                     below_datetime=original_datetime,
                                                                                     ignore_with_tmdb_id=False),
                                                                  unittest.mock.call(self.session, '_Title_2_', True,
                                                                                     None, None, False, True,
                                                                                     below_datetime=original_datetime,
                                                                                     ignore_with_tmdb_id=False)])

        db_calls_mock.commit.assert_called_with(self.session)


if __name__ == '__main__':
    unittest.main()
