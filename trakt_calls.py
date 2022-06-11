import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional, List

import sqlalchemy.orm

import configuration
import db_calls


class SimpleTraktShow(object):
    """The class that will represent the config in the response from a search to trakt, using text."""

    id: int
    imdb_id: str
    slug: str
    is_movie: bool
    title: str
    year: int

    def __init__(self, show_dict: dict, show_type: str):
        show = show_dict[show_type]
        ids = show['ids']

        self.id = ids['trakt']
        self.imdb_id = ids['imdb']
        self.slug = ids['slug']

        self.is_movie = show_type == 'movie'
        self.title = show['title']
        self.year = show['year']


class TraktShow(SimpleTraktShow):
    """The class that will represent the config in the response from a search to trakt, using a trakt id."""

    overview: str
    language: str
    country: str
    available_translations: List[str]

    def __init__(self, show_dict: dict, show_type: str):
        super().__init__(show_dict, show_type)

        show = show_dict[show_type]

        self.overview = show['overview']
        self.language = show['language']
        self.country = show['country']
        self.available_translations = show['available_translations']


class TraktTranslation(object):
    """The class that will represent a trakt translation in the response from trakt."""

    title: str
    overview: str
    language: str

    def __init__(self, translation_dict: dict):
        self.title = translation_dict['title']
        self.overview = translation_dict['overview']
        self.language = translation_dict['language']


class TraktAlias(object):
    """The class that will represent a trakt alias in the response from trakt."""

    title: str
    country: str

    def __init__(self, alias_dict: dict):
        self.title = alias_dict['title']
        self.country = alias_dict['country']


def search_show_by_id(session: sqlalchemy.orm.Session, trakt_id: int, is_movie: bool) -> Optional[TraktShow]:
    """
    Get a show's information, from trakt.

    :param session: the db session.
    :param trakt_id: the trakt id of the show.
    :param is_movie: if the show is a movie.
    :return: the TraktShow.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'show'

    cache_key = 'trakt|id|%s-%s' % (show_type, trakt_id)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        request = urllib.request.Request('https://api.trakt.tv/search/trakt/%s?extended=full&id_type=trakt&type=%s'
                                         % (trakt_id, show_type))
        request.add_header('trakt-api-key', configuration.trakt_key)

        try:
            response = urllib.request.urlopen(request).read()
        except urllib.error.HTTPError:
            return None

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the list of translations from the request
    response_dict = json.loads(response)

    # Choose the correct entry from the response
    for entry in response_dict:
        if entry['type'] != show_type:
            continue

        else:
            return TraktShow(entry, show_type)

    return None


def search_show_by_tmdb_id(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool) -> Optional[TraktShow]:
    """
    Get a show's information, from trakt, using a tmdb id.

    :param session: the db session.
    :param tmdb_id: the trakt id of the show.
    :param is_movie: if the show is a movie.
    :return: the TraktShow.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'show'

    cache_key = 'trakt|tmdb_id|%s-%s' % (show_type, tmdb_id)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        request = urllib.request.Request('https://api.trakt.tv/search/tmdb/%s?extended=full&type=%s'
                                         % (tmdb_id, show_type))
        request.add_header('trakt-api-key', configuration.trakt_key)

        try:
            response = urllib.request.urlopen(request).read()
        except urllib.error.HTTPError:
            return None

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the list of translations from the request
    response_dict = json.loads(response)

    # Choose the correct entry from the response
    for entry in response_dict:
        if entry['type'] != show_type:
            continue

        else:
            return TraktShow(entry, show_type)

    return None


def search_shows_by_text(session: sqlalchemy.orm.Session, search_text: str, is_movie: bool) -> List[TraktShow]:
    """
    Search shows by text, using trakt.

    :param session: the db session.
    :param search_text: the search text.
    :param is_movie: if the show is a movie.
    :return: the list of TraktShow.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'show'

    cache_key = 'trakt|text|%s-%s' % (show_type, search_text)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        request = urllib.request.Request('https://api.trakt.tv/search/%s?extended=full&query=%s'
                                         % (show_type, urllib.parse.quote(search_text)))
        request.add_header('trakt-api-key', configuration.trakt_key)

        try:
            response = urllib.request.urlopen(request).read()
        except urllib.error.HTTPError:
            return []

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the response
    response_dict = json.loads(response)

    # Create a TraktShow for each entry
    trakt_shows = []

    for entry in response_dict:
        if entry['type'] != show_type:
            continue

        else:
            trakt_shows.append(TraktShow(entry, show_type))

    return trakt_shows


def get_show_translations(session: sqlalchemy.orm.Session, trakt_slug: str, is_movie: bool) -> List[TraktTranslation]:
    """
    Get a show's translations.

    :param session: the db session.
    :param trakt_slug: the trakt slug of the show.
    :param is_movie: if the show is a movie.
    :return: a list of TraktTranslation.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'show'

    cache_key = 'trakt|translations|%s-%s' % (show_type, trakt_slug)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        request = urllib.request.Request('https://api.trakt.tv/%ss/%s/translations' % (show_type, trakt_slug))
        request.add_header('trakt-api-key', configuration.trakt_key)

        try:
            response = urllib.request.urlopen(request).read()
        except urllib.error.HTTPError:
            return []

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the list of translations from the request
    response_dict = json.loads(response)

    # Create the list of TraktTranslations
    translations = []

    for entry in response_dict:
        translations.append(TraktTranslation(entry))

    return translations


def get_show_aliases(session: sqlalchemy.orm.Session, trakt_slug: str, is_movie: bool) -> List[TraktAlias]:
    """
    Get a show's aliases.

    :param session: the db session.
    :param trakt_slug: the trakt slug of the show.
    :param is_movie: if the show is a movie.
    :return: a list of TraktAlias.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'show'

    cache_key = 'trakt|aliases|%s-%s' % (show_type, trakt_slug)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        request = urllib.request.Request('https://api.trakt.tv/%ss/%s/aliases' % (show_type, trakt_slug))
        request.add_header('trakt-api-key', configuration.trakt_key)

        try:
            response = urllib.request.urlopen(request).read()
        except urllib.error.HTTPError:
            print('Slug was not found!')
            return []

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the list of aliases from the request
    response_dict = json.loads(response)

    aliases = []

    for entry in response_dict:
        aliases.append(TraktAlias(entry))

    return aliases


def collect_titles(session: sqlalchemy.orm.Session, trakt_id: int, is_movie: bool) -> List[str]:
    """
    Get all trakt titles for a trakt id.

    :param session: the db session.
    :param trakt_id: the trakt id of the show.
    :param is_movie: true if it is a movie.
    :return a set with the titles from a show.
    """

    # Get the show's information from trakt
    trakt_show = search_show_by_id(session, trakt_id, is_movie)

    # If no result is found
    if trakt_show is None:
        return []

    titles = set()
    titles.add(trakt_show.title)

    # If the show has no translations of interest
    if 'en' not in trakt_show.available_translations and 'pt' not in trakt_show.available_translations:
        return [trakt_show.title]

    # Add the titles in the translations
    trakt_translation_list = get_show_translations(session, trakt_show.slug, trakt_show.is_movie)

    for t in trakt_translation_list:
        if (t.language == 'en' or t.language == 'pt') and t.title is not None:
            titles.add(t.title)

    # Add the titles in the aliases
    trak_alias_list = get_show_aliases(session, trakt_show.slug, trakt_show.is_movie)

    for a in trak_alias_list:
        if (a.country == 'us' or a.country == 'pt' or a.country == trakt_show.country) and a.title is not None:
            titles.add(a.title)

    return list(titles)
