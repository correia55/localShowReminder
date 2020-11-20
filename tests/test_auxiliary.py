import unittest

import auxiliary


class TestAuxiliary(unittest.TestCase):
    def test_strip_accents(self) -> None:
        """ Test the function strip_accents. """

        # The expected result
        expected_result = 'aaaaaAAAAAoooOOOeeeEEErt'

        # Call the function
        text = 'aàáãâAÁÀÃÂoóôOÓÔeéêEÉÊrt'
        actual_result = auxiliary.strip_accents(text)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_remove_quote(self) -> None:
        """ Test the function remove_quote. """

        # The expected result
        expected_result = 'schits, schits, schits'

        # Call the function
        text = 'schit\'s, schit`s, schit´s'
        actual_result = auxiliary.remove_quote(text)

        # Verify the result
        self.assertEqual(expected_result, actual_result)


if __name__ == '__main__':
    unittest.main()
