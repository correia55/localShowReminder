import json
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Optional, Tuple

import sqlalchemy.orm

import configuration
import db_calls
from response_models import TmdbShow, TmdbTranslation, TmdbAlias, TmdbCrewMember


def search_shows_by_text(session: sqlalchemy.orm.Session, search_text: str, language: str = None, is_movie: bool = None,
                         page: int = 1, show_adult: bool = False, year: int = None) -> Tuple[int, List[TmdbShow]]:
    """
    Search shows by text, using TMDB.

    :param session: the db session.
    :param search_text: the search text.
    :param is_movie: if the show is a movie.
    :param language: the language in which we want the response (pt-PT, en-US...).
    :param page: the page to obtain.
    :param show_adult: whether to show adult results or not.
    :param year: the year of the show.
    :return: a tuple with the total number of pages and the list of TmdbShow.
    """

    if is_movie is None:
        show_type = 'multi'
    else:
        if is_movie:
            show_type = 'movie'
        else:
            show_type = 'tv'

    # The values need to be like this
    if show_adult:
        include_adult = 'true'
    else:
        include_adult = 'false'

    cache_key = 'tmdb|text|%s-%s-%s-%s-%s-%s' % (show_type, language, search_text, include_adult, page, year)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Create the url
        url = 'https://api.themoviedb.org/3/search/%s?api_key=%s&language=%s&query=%s&include_adult=%s' \
              % (show_type, configuration.tmdb_key, language, urllib.parse.quote(search_text), include_adult)

        if year is not None:
            url += '&year=%d' % year

        # Make the request
        search_request = urllib.request.Request(url)

        # Add the page, when it exists
        if page:
            search_request.full_url = '%s&page=%d' % (search_request.full_url, page)

        try:
            response = urllib.request.urlopen(search_request).read()
        except urllib.error.HTTPError:
            return 0, []

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the response
    response_dict = json.loads(response)

    # Create a TmdbShow for each entry
    tmdb_shows = []

    for entry in response_dict['results']:
        # TODO: Need to change this, if I want to allow for searches to include people
        if show_type != 'multi' or entry['media_type'] == 'tv' or entry['media_type'] == 'movie':
            tmdb_show = TmdbShow()
            tmdb_show.fill_from_dict(entry, is_movie)

            tmdb_shows.append(tmdb_show)
        elif entry['media_type'] == 'person':
            # Get the "known for" entries in the people found
            for show in entry['known_for']:
                tmdb_show = TmdbShow()
                tmdb_show.fill_from_dict(show, is_movie, entry['known_for_department'])

                tmdb_shows.append(tmdb_show)

    return response_dict['total_pages'], tmdb_shows


def get_show_using_id(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool, language: str = None) \
        -> Optional[TmdbShow]:
    """
    Get a show's information, from TMDB.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param is_movie: if the show is a movie.
    :param language: the language in which we want the response (pt-PT, en-US...).
    :return: the TmdbShow.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'tv'

    cache_key = 'tmdb|id|%s-%s-%s' % (show_type, language, tmdb_id)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        url = 'https://api.themoviedb.org/3/%s/%s?api_key=%s' % (show_type, tmdb_id, configuration.tmdb_key)

        if language is not None:
            url += '&language=%s' % language

        show_request = urllib.request.Request(url)

        try:
            response = urllib.request.urlopen(show_request).read()
        except urllib.error.HTTPError:
            return None

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the response to json
    response_dict = json.loads(response)

    tmdb_show = TmdbShow()
    tmdb_show.fill_from_dict(response_dict, is_movie)

    return tmdb_show


def get_show_translations(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool) \
        -> List[TmdbTranslation]:
    """
    Search for a show's translations, using TMDB.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param is_movie: if the show is a movie.
    :return: the list of TmdbTranslation.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'tv'

    cache_key = 'tmdb|translations|%s-%s' % (show_type, tmdb_id)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        request = urllib.request.Request('https://api.themoviedb.org/3/%s/%s/translations?api_key=%s'
                                         % (show_type, tmdb_id, configuration.tmdb_key))

        try:
            response = urllib.request.urlopen(request).read()
        except urllib.error.HTTPError:
            return []

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the response
    response_dict = json.loads(response)

    # Create a TmdbTranslation for each entry
    tmdb_translations = []

    for entry in response_dict['translations']:
        tmdb_translation = TmdbTranslation()
        tmdb_translation.fill_from_dict(tmdb_id, entry, is_movie)

        tmdb_translations.append(tmdb_translation)

    return tmdb_translations


def get_show_aliases(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool) \
        -> List[TmdbAlias]:
    """
    Search for a show's aliases, using TMDB.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param is_movie: if the show is a movie.
    :return: the list of TmdbAlias.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'tv'

    cache_key = 'tmdb|aliases|%s-%s' % (show_type, tmdb_id)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        request = urllib.request.Request('https://api.themoviedb.org/3/%s/%s/alternative_titles?api_key=%s'
                                         % (show_type, tmdb_id, configuration.tmdb_key))

        try:
            response = urllib.request.urlopen(request).read()
        except urllib.error.HTTPError:
            return []

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the response
    response_dict = json.loads(response)

    # Create a TmdbTranslation for each entry
    tmdb_aliases = []

    if is_movie:
        for entry in response_dict['titles']:
            tmdb_alias = TmdbAlias()
            tmdb_alias.fill_from_dict(tmdb_id, entry)

            tmdb_aliases.append(tmdb_alias)
    else:
        for entry in response_dict['results']:
            tmdb_alias = TmdbAlias()
            tmdb_alias.fill_from_dict(tmdb_id, entry)

            tmdb_aliases.append(tmdb_alias)

    return tmdb_aliases


def get_show_crew_members(tmdb_id: int, is_movie: bool) \
        -> List[TmdbCrewMember]:
    """
    Search for a show's crew members, using TMDB.
    It does not save to the cache.

    :param tmdb_id: the tmdb id of the show.
    :param is_movie: if the show is a movie.
    :return: the list of TmdbCrewMembers.
    """

    if is_movie:
        show_type = 'movie'
        resource = 'credits'
    else:
        show_type = 'tv'
        resource = 'aggregate_credits'

    # Make the request
    request = urllib.request.Request('https://api.themoviedb.org/3/%s/%s/%s?api_key=%s'
                                     % (show_type, tmdb_id, resource, configuration.tmdb_key))

    try:
        response = urllib.request.urlopen(request).read()
    except urllib.error.HTTPError:
        return []

    # Parse the response
    response_dict = json.loads(response)

    # Create a TmdbCrewMember for each entry
    tmdb_crew_members = []

    for entry in response_dict['crew']:
        tmdb_crew_member = TmdbCrewMember()
        tmdb_crew_member.fill_from_dict(entry, is_movie)

        tmdb_crew_members.append(tmdb_crew_member)

    return tmdb_crew_members


def collect_titles(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool) -> List[str]:
    """
    Get all tmdb titles for a tmdb id.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param is_movie: true if it is a movie.
    :return a list with the titles from a show.
    """

    # Get the show's information from tmdb
    tmdb_show = get_show_using_id(session, tmdb_id, is_movie)

    # If no result is found
    if tmdb_show is None:
        return []

    titles = set()
    titles.add(tmdb_show.title)

    # Add the titles in the translations
    tmdb_translation_list = get_show_translations(session, tmdb_id, is_movie)

    for t in tmdb_translation_list:
        if (t.language_country.startswith('en') or t.language_country == 'pt-PT') \
                and t.title is not None and t.title != '':
            titles.add(t.title)

    # Add the titles in the aliases
    tmdb_alias_list = get_show_aliases(session, tmdb_id, is_movie)

    for a in tmdb_alias_list:
        if (a.country == 'US' or a.country == 'PT' or (not is_movie and a.country == tmdb_show.origin_country)) \
                and a.title is not None and a.title != '':
            titles.add(a.title)

    return list(titles)
