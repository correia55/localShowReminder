import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, List, Set

import configuration


class SimpleTraktShow(object):
    """The class that will represent the data in the response from a search to trakt, using text."""

    id: int
    imdb_id: str
    slug: str
    is_movie: bool
    title: str
    year: int

    def __init__(self, show_json_object, show_type: str):
        show = show_json_object[show_type]
        ids = show['ids']

        self.id = ids['trakt']
        self.imdb_id = ids['imdb']
        self.slug = ids['slug']

        self.is_movie = show_type == 'movie'
        self.title = show['title']
        self.year = show['year']


class TraktShow(SimpleTraktShow):
    """The class that will represent the data in the response from a search to trakt, using a trakt id."""

    overview: str
    language: str
    country: str
    available_translations: List[str]

    def __init__(self, show_json_object, show_type: str):
        super().__init__(show_json_object, show_type)

        show = show_json_object[show_type]

        self.overview = show['overview']
        self.language = show['language']
        self.country = show['country']
        self.available_translations = show['available_translations']


class TraktTranslation(object):
    """The class that will represent a trakt translation in the response from trakt."""

    title: str
    overview: str
    language: str

    def __init__(self, show_json_object):
        self.title = show_json_object['title']
        self.overview = show_json_object['overview']
        self.language = show_json_object['language']


class TraktAlias(object):
    """The class that will represent a trakt alias in the response from trakt."""

    title: str
    country: str

    def __init__(self, show_json_object):
        self.title = show_json_object['title']
        self.country = show_json_object['country']


def search_show_by_trakt_id(trakt_id: int, is_movie: bool) -> Optional[TraktShow]:
    """
    Get a show's information, from trakt.

    :param trakt_id: the trakt id of the show.
    :param is_movie: if the show is a movie.
    :return: the TraktShow.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'show'

    show_request = urllib.request.Request('https://api.trakt.tv/search/trakt/%s?extended=full&id_type=trakt&type=%s'
                                          % (trakt_id, show_type))
    show_request.add_header('trakt-api-key', configuration.trakt_key)

    try:
        show_json = urllib.request.urlopen(show_request).read()
    except urllib.error.HTTPError:
        return None

    # Parse the list of translations from the request
    show_json_object = json.loads(show_json)

    # Choose the correct entry from the response
    for entry in show_json_object:
        if entry['type'] != show_type:
            continue

        else:
            return TraktShow(entry, show_type)

    return None


def search_shows_by_text(search_text: str, is_movie: bool) -> List[TraktShow]:
    """
    Search shows by text, using trakt.

    :param search_text: the search text.
    :param is_movie: if the show is a movie.
    :return: the list of TraktShow.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'show'

    search_request = urllib.request.Request('https://api.trakt.tv/search/%s?extended=full&query=%s'
                                            % (show_type, urllib.parse.quote(search_text)))
    search_request.add_header('trakt-api-key', configuration.trakt_key)

    try:
        search_json = urllib.request.urlopen(search_request).read()
    except urllib.error.HTTPError:
        return []

    # Parse the response
    search_json_object = json.loads(search_json)

    # Create a TraktShow for each entry
    trakt_shows = []

    for entry in search_json_object:
        if entry['type'] != show_type:
            continue

        else:
            trakt_shows.append(TraktShow(entry, show_type))

    return trakt_shows


def get_show_translations(trakt_slug: str, is_movie: bool) -> List[TraktTranslation]:
    """
    Get a show's translations.

    :param trakt_slug: the trakt slug of the show.
    :param is_movie: if the show is a movie.
    :return: a list of TraktTranslation.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'show'

    translations_request = urllib.request.Request('https://api.trakt.tv/%ss/%s/translations' % (show_type, trakt_slug))
    translations_request.add_header('trakt-api-key', configuration.trakt_key)

    try:
        translations_json = urllib.request.urlopen(translations_request).read()
    except urllib.error.HTTPError:
        return []

    # Parse the list of translations from the request
    translations_json_object = json.loads(translations_json)

    # Create the list of TraktTranslations
    translations = []

    for entry in translations_json_object:
        translations.append(TraktTranslation(entry))

    return translations


def get_show_aliases(trakt_slug: str, is_movie: bool) -> List[TraktAlias]:
    """
    Get a show's aliases.

    :param trakt_slug: the trakt slug of the show.
    :param is_movie: if the show is a movie.
    :return: a list of TraktAlias.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'show'

    aliases_request = urllib.request.Request('https://api.trakt.tv/%ss/%s/aliases' % (show_type, trakt_slug))
    aliases_request.add_header('trakt-api-key', configuration.trakt_key)

    try:
        aliases_json = urllib.request.urlopen(aliases_request).read()
    except urllib.error.HTTPError:
        print('Slug was not found!')
        return []

    # Parse the list of aliases from the request
    aliases_json_object = json.loads(aliases_json)

    aliases = []

    for entry in aliases_json_object:
        aliases.append(TraktAlias(entry))

    return aliases


def collect_titles_trakt(trakt_id: int, is_movie: bool) -> List[str]:
    """
    Get all trakt titles for a trakt id.

    :param trakt_id: the trakt id of the show.
    :param is_movie: true if it is a movie.
    :return a set with the titles from a show.
    """

    # Get the show's information from trakt
    trakt_show = search_show_by_trakt_id(trakt_id, is_movie)

    # If no result is found
    if trakt_show is None:
        return []

    titles = set()
    titles.add(trakt_show.title)

    # If the show has no translations of interest
    if 'en' not in trakt_show.available_translations and 'pt' not in trakt_show.available_translations:
        return [trakt_show.title]

    # Add the titles in the translations
    trakt_translation_list = get_show_translations(trakt_show.slug, trakt_show.is_movie)

    for t in trakt_translation_list:
        if (t.language == 'en' or t.language == 'pt') and t.title is not None:
            titles.add(t.title)

    # Add the titles in the aliases
    trak_alias_list = get_show_aliases(trakt_show.slug, trakt_show.is_movie)

    for a in trak_alias_list:
        if (a.country == 'us' or a.country == 'pt' or a.country == trakt_show.country) and a.title is not None:
            titles.add(a.title)

    return list(titles)
