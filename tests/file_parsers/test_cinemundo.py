import unittest.mock

import file_parsers.cinemundo_parser


class TestCinemundo(unittest.TestCase):
    def test_Cinemundo_process_title_01(self) -> None:
        """ Test the function Cinemundo.process_title with nothing in particular. """

        # The expected result
        expected_result = ('Mortadela e Salamão: Missão Não Possível', True, None)

        # Call the function
        actual_result = file_parsers.cinemundo_parser.CinemundoParser.process_title('Mortadela e Salamão: Missão Não Possível VP')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_Cinemundo_process_title_02(self) -> None:
        """ Test the function Cinemundo.process_title with quotation marks. """

        # The expected result
        expected_result = ('Je m\'appelle Bernadette', False, None)

        # Call the function
        actual_result = file_parsers.cinemundo_parser.CinemundoParser.process_title('Je m´appelle Bernadette')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_Cinemundo_process_title_03(self) -> None:
        """ Test the function Cinemundo.process_title with season. """

        # The expected result
        expected_result = ('True Justice', False, 2)

        # Call the function
        actual_result = file_parsers.cinemundo_parser.CinemundoParser.process_title('True Justice S2: Vengeance is Mine')

        # Verify the result
        self.assertEqual(expected_result, actual_result)
