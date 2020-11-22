import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, List, Set

import configuration


class TraktShow(object):
    """The class that will represent the data in the response from a search to trakt."""

    id: int
    slug: str
    is_movie: bool
    title: str
    language: str
    country: str
    available_translations: List[str]

    def __init__(self, show_json_object, show_type: str):
        show = show_json_object[show_type]
        ids = show['ids']

        self.id = ids['trakt']
        self.slug = ids['slug']
        self.is_movie = show_type == 'movie'
        self.title = show['title']
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


def search_trakt_id(trakt_id: int, is_movie: bool) -> Optional[TraktShow]:
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


def collect_titles_trakt(trakt_id: int, is_movie: bool) -> Set[str]:
    """
    Get all trakt titles for a trakt id.

    :param trakt_id: the trakt id of the show.
    :param is_movie: true if it is a movie.
    :return a set with the titles from a show.
    """

    # Get the show's information from trakt
    trakt_show = search_trakt_id(trakt_id, is_movie)

    # If no result is found
    if trakt_show is None:
        return set()

    titles = set(trakt_show.title)

    # If the show has no translations of interest
    if 'en' not in trakt_show.available_translations and 'pt' not in  trakt_show.available_translations:
        return set(trakt_show.title)

    # Add the titles in the translations
    trakt_translation_list = get_show_translations(trakt_show.slug, trakt_show.is_movie)

    for t in trakt_translation_list:
        if t.language == 'en' or t.language == 'pt':
            titles.add(t.title)

    # Add the titles in the aliases
    trak_alias_list = get_show_aliases(trakt_show.slug, trakt_show.is_movie)

    for a in trak_alias_list:
        if a.country == 'us' or a.country == 'pt' or a.country == trakt_show.country:
            titles.add(a.title)

    return titles


def search_show_information_by_type(search_text: str, show_type: str, language: str):
    """
    Uses trakt and omdb to search for shows, of a given type, using a given search text.

    :param search_text: the search text introduced by the user.
    :param show_type: 'show' for tv shows and 'movie' for movies.
    :param language: the language of interest.
    :return: the list of results.
    """

    results = []

    # Make the request
    shows_request = urllib.request.Request(
        'https://api.trakt.tv/search/%s?extended=full&query=%s' % (show_type, urllib.parse.quote(search_text)))
    shows_request.add_header('trakt-api-key', configuration.trakt_key)

    shows_json = urllib.request.urlopen(shows_request).read()

    # Parse the list of shows from the request
    shows = json.loads(shows_json)

    is_movie = show_type == 'movie'

    for s in shows:
        imdb_id = s[show_type]['ids']['imdb']

        show_dict = {'is_movie': is_movie, 'show_title': s[show_type]['title'], 'show_year': s[show_type]['year'],
                     'show_image': 'N/A', 'show_slug': s[show_type]['ids']['slug'],
                     'show_overview': s[show_type]['overview'], 'language': s[show_type]['language'],
                     'available_translations': s[show_type]['available_translations']}

        # Get the translation of the overview
        if language != s[show_type]['language']:
            available_translations = s[show_type]['available_translations']

            if language in available_translations:
                translated_overview = get_translated_overview(s[show_type]['ids']['slug'], show_type, language)

                if translated_overview is not None:
                    show_dict['show_overview'] = translated_overview

        # Check if we can get the poster
        if imdb_id is None or configuration.omdb_key is None:
            results.append(show_dict)
            continue

        show_json = urllib.request.urlopen(
            'http://www.omdbapi.com/?apikey=%s&i=%s' % (configuration.omdb_key, imdb_id)).read()

        # Parse the show from the request
        show = json.loads(show_json)

        # When the omdb can't find the information
        if show['Response'] == 'False':
            results.append(show_dict)
            continue

        show_dict['show_image'] = show['Poster']

        results.append(show_dict)

    return results


def get_translated_overview(trakt_slug: str, show_type: str, language: str):
    """
    Get the translated overview of a show.

    :param trakt_slug: the selected title.
    :param show_type: 'show' for tv shows and 'movie' for movies.
    :param language: the language of the translation.
    :return: the translated overview.
    """

    translations_request = urllib.request.Request(
        'https://api.trakt.tv/%ss/%s/translations/%s' % (show_type, trakt_slug, language))
    translations_request.add_header('trakt-api-key', configuration.trakt_key)

    try:
        translations_json = urllib.request.urlopen(translations_request).read()
    except urllib.error.HTTPError:
        print('Slug was not found!')
        return None

    # Parse the list of translations from the request
    translations = json.loads(translations_json)

    for t in translations:
        if t['overview'] != '':
            return t['overview']

    return None
