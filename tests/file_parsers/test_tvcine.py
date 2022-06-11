import unittest.mock

import file_parsers.tvcine_parser


class TestTvCine(unittest.TestCase):
    def test_TVCine_process_title_01(self) -> None:
        """ Test the function TvCine.process_title with a title with "(VO)". """

        # The expected result
        expected_result = ('The Angry Birds Movie 2', False, False)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title('Angry Birds Movie 2, The (VO)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_02(self) -> None:
        """ Test the function TvCine.process_title with a title with "(VP)". """

        # The expected result
        expected_result = ('The Angry Birds Movie 2', True, False)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title('Angry Birds Movie 2, The (VP)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_03(self) -> None:
        """ Test the function TvCine.process_title with the year in the title. """

        # The expected result
        expected_result = ('Endings, Beginnings', False, False)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title('Endings, Beginnings (2019)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_04(self) -> None:
        """ Test the function TvCine.process_title with an inverted section at the end. """

        # The expected result
        expected_result = ('A Beautiful Day In The Neighborhood', False, False)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title('Beautiful Day In The Neighborhood, A')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_05(self) -> None:
        """ Test the function TvCine.process_title with year and "VO". """

        # The expected result
        expected_result = ('Abominable', False, False)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title('Abominable (2019) (VO)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_06(self) -> None:
        """ Test the function TvCine.process_title with year and "VP". """

        # The expected result
        expected_result = ('Abominable', True, False)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title('Abominable (2019) (VP)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_07(self) -> None:
        """ Test the function TvCine.process_title with year, "VP" and an inverted section. """

        # The expected result
        expected_result = ('The Addams Family', True, False)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title('Addams Family, The (2019) (VP)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_08(self) -> None:
        """ Test the function TvCine.process_title with the extended cut. """

        # The expected result
        expected_result = ('Furious 7', False, True)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title('Furious 7 (extended cut)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_09(self) -> None:
        """ Test the function TvCine.process_title with a quotation mark. """

        # The expected result
        expected_result = ('Child\'s Play', False, False)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title('Child`s Play (2019)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_10(self) -> None:
        """ Test the function TvCine.process_title with nothing in particular. """

        # The expected result
        expected_result = ('Birds Of Prey (And The Fantabulous Emancipation Of One Harley Quinn)', False, False)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title(
            'Birds Of Prey (And The Fantabulous Emancipation Of One Harley Quinn)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_11(self) -> None:
        """ Test the function TvCine.process_title with parts of the title switched but not at the end. """

        # The expected result
        expected_result = ('The Lost World : Jurassic Park', False, False)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title('Lost World, The: Jurassic Park')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_12(self) -> None:
        """ Test the function TvCine.process_title with parts of the title switched but not at the end. """

        # The expected result
        expected_result = ('Le Ninfee di Monet - Un Incantesimo di Acqua e Luce', False, False)

        # Call the function
        actual_result = file_parsers.tvcine_parser.TVCineParser.process_title(
            'Ninfee di Monet, Le - Un Incantesimo di Acqua e Luce')

        # Verify the result
        self.assertEqual(expected_result, actual_result)
