import unittest.mock

import file_parsers.fox_life


class TestFoxLife(unittest.TestCase):
    def test_process_title_01(self) -> None:
        """ Test the function FoxLife.process_title with a simple movie. """

        # The expected result
        expected_result = 'Home By Spring'

        # Call the function
        actual_result = file_parsers.fox_life.FoxLife.process_title('Home By Spring', True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_02(self) -> None:
        """ Test the function FoxLife.process_title with a simple series. """

        # The expected result
        expected_result = 'Private Practice'

        # Call the function
        actual_result = file_parsers.fox_life.FoxLife.process_title('Private Practice 1', False)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_03(self) -> None:
        """ Test the function FoxLife.process_title with year in the title of the series. """

        # The expected result
        expected_result = 'New Amsterdam'

        # Call the function
        actual_result = file_parsers.fox_life.FoxLife.process_title('New Amsterdam (2018) 3', False)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_process_title_04(self) -> None:
        """ Test the function FoxLife.process_title with re-release in the title of a movie. """

        # The expected result
        expected_result = 'Titanic'

        # Call the function
        actual_result = file_parsers.fox_life.FoxLife.process_title('Titanic (re-release 2012)', True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)
