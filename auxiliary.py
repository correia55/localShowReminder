import unicodedata

from models import TraktTitle


def strip_accents(text: str):
    """
    Source: https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string

    Strip accents from input String.

    :param text: The input string.
    :returns: The processed String.
    """

    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore')
    text = text.decode("utf-8")

    return str(text)


def get_names_list_from_trakttitles_list(traktitle_list: [TraktTitle]):
    """
    Create a list of strings with the names of each TraktTitle in the entry list.

    :param traktitle_list: the list of TraktTitle.
    :return: the list of names.
    """

    titles = []

    for title in traktitle_list:
        titles.append(title.trakt_title)

    return titles
