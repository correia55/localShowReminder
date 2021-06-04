import sys
import unittest.mock

# Configure a mock for the configuration file
configuration_mock = unittest.mock.MagicMock()
sys.modules['configuration'] = configuration_mock

# Configure a mock for the db_calls file
db_calls_mock = unittest.mock.MagicMock()
sys.modules['db_calls'] = db_calls_mock

# Configure a mock for the process_emails file
process_emails_mock = unittest.mock.MagicMock()
sys.modules['process_emails'] = process_emails_mock

import file_parsers.cinemundo


class TestCinemundo(unittest.TestCase):
    def test_Cinemundo_process_title_01(self) -> None:
        """ Test the function Cinemundo.process_title with nothing in particular. """

        # The expected result
        expected_result = ('Mortadela e Salamão: Missão Não Possível', True, None)

        # Call the function
        actual_result = file_parsers.cinemundo.Cinemundo.process_title('Mortadela e Salamão: Missão Não Possível VP')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_Cinemundo_process_title_02(self) -> None:
        """ Test the function Cinemundo.process_title with quotation marks. """

        # The expected result
        expected_result = ('Je m\'appelle Bernadette', False, None)

        # Call the function
        actual_result = file_parsers.cinemundo.Cinemundo.process_title('Je m´appelle Bernadette')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_Cinemundo_process_title_03(self) -> None:
        """ Test the function Cinemundo.process_title with season. """

        # The expected result
        expected_result = ('True Justice', False, 2)

        # Call the function
        actual_result = file_parsers.cinemundo.Cinemundo.process_title('True Justice S2: Vengeance is Mine')

        # Verify the result
        self.assertEqual(expected_result, actual_result)
