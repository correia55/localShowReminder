import urllib.request
import urllib.error
import urllib.parse
import json
import datetime
import re

import configuration


def get_channel_list(ignore_hd=True):
    """
    Make a request for the channel list and add them to the db.

    :param ignore_hd: true when we're supposed to ignore HD channels.
    """

    print('Get channel list!')

    # Request the list of channels
    channels_json = urllib.request.urlopen(
        'https://tvnetvoz.vodafone.pt/sempre-consigo/datajson/epg/channels.jsp').read()

    # Parse the list of channels from the request
    channels = json.loads(channels_json)['result']['channels']

    # Add the list of channels to the database
    for c in channels:
        if ignore_hd and 'HD' not in c['name']:
            channel = configuration.models.Channel(c['id'], c['name'])

            configuration.session.add(channel)

    configuration.session.commit()


def update_show_list():
    """Make a request for the show list and update the db."""

    print('Updating show list...')

    # Get list of all channels from the db
    db_channels = configuration.session.query(configuration.models.Channel).all()

    # If the list of channels in the db is empty
    if db_channels == []:
        get_channel_list()

        db_channels = configuration.session.query(configuration.models.Channel).all()

    # Get the date of the last update
    db_last_update = configuration.session.query(configuration.models.LastUpdate).first()

    # If this is the first update set yesterday's date
    if db_last_update is None:
        db_last_update = configuration.models.LastUpdate(datetime.date.today() - datetime.timedelta(1))

        configuration.session.add(db_last_update)

    # For each day until six days from today
    while db_last_update.date < datetime.date.today() + datetime.timedelta(6):
        db_last_update.date += datetime.timedelta(1)

        # Create the shows' info request
        shows_url = 'https://tvnetvoz.vodafone.pt/sempre-consigo/epg.do?action=getPrograms&chanids='

        first = True

        for c in db_channels:
            if first:
                first = False
                shows_url += str(c.pid)
            else:
                shows_url += ',' + str(c.pid)

        shows_url += '&day=' + db_last_update.date.strftime('%Y-%m-%d')

        print(shows_url)

        # Get the shows info for our list of channels
        shows_json = urllib.request.urlopen(shows_url).read()

        # Parse the list of channels from the request
        channels = json.loads(shows_json)['result']['channels']

        for c in channels:
            channel_shows = c['programList']
            channel_id = configuration.session.query(configuration.models.Channel).filter(
                configuration.models.Channel.pid == c['id']).first().id

            for s in channel_shows:
                program_title = s['programTitle']
                pos = program_title.find(':T')

                # If it's referent to a show from a different day
                if s['date'] != db_last_update.date.strftime('%d-%m-%Y'):
                    continue

                # If it is an episode of a series
                if pos != -1:
                    show_title = program_title[:pos]
                    show_rem = program_title[pos + 2:].split()

                    show_season = int(show_rem[0])

                    # Some shows seem to be missing the episode info
                    try:
                        show_episode = int(show_rem[1][3:])
                    except:
                        print(program_title)
                        show_episode = 0
                else:
                    show_title = program_title
                    show_season = 0
                    show_episode = 0

                show_datetime = db_last_update.date.strftime('%Y-%m-%d ') + s['startTime']

                # Remove the last character in order to find the results for both SD and HD
                if s['serid'] is not None:
                    series_id = s['serid'][:-1]
                else:
                    series_id = None

                # Remove the first character in order to find the results for both SD and HD
                pid = s['pid'][1:]

                # Add the show to the db
                show = configuration.models.Show(pid, series_id, show_title, show_season, show_episode,
                                                 s['programDetails'], show_datetime, s['duration'], channel_id)

                configuration.session.add(show)

        configuration.session.commit()

    print('Update to show lists is complete!')


def search_show_information(search_text):
    """
    Request a search to trakt and return the results.

    :param search_text: the search text introduced by the user.
    :return: the list of results.
    """

    shows_request = urllib.request.Request('https://api.trakt.tv/search/show?query=' + urllib.parse.quote(search_text))
    shows_request.add_header('trakt-api-key', configuration.trakt_key)

    shows_json = urllib.request.urlopen(shows_request).read()

    # Parse the list of shows from the request
    shows = json.loads(shows_json)

    movies_request = urllib.request.Request(
        'https://api.trakt.tv/search/movie?query=' + urllib.parse.quote(search_text))
    movies_request.add_header('trakt-api-key', configuration.trakt_key)

    movies_json = urllib.request.urlopen(movies_request).read()

    # Parse the list of movies from the request
    movies = json.loads(movies_json)

    results = []

    for s in shows:
        imdb_id = s['show']['ids']['imdb']

        if imdb_id is None or configuration.omdb_key is None:
            results.append(
                {'is_show': True, 'show_title': s['show']['title'], 'show_year': s['show']['year'], 'show_image': 'N/A',
                 'show_slug': s['show']['ids']['slug']})
            continue

        show_json = urllib.request.urlopen(
            'http://www.omdbapi.com/?apikey=' + configuration.omdb_key + '&i=' + s['show']['ids']['imdb']).read()

        # Parse the show from the request
        show = json.loads(show_json)

        # When the omdb can't find the information
        if show['Response']:
            results.append(
                {'is_show': True, 'show_title': s['show']['title'], 'show_year': s['show']['year'], 'show_image': 'N/A',
                 'show_slug': s['show']['ids']['slug']})
            continue

        results.append(
            {'is_show': True, 'show_title': s['show']['title'], 'show_year': s['show']['year'],
             'show_image': show['Poster'],
             'show_slug': s['show']['ids']['slug']})

    for m in movies:
        imdb_id = m['movie']['ids']['imdb']

        if imdb_id is None or configuration.omdb_key is None:
            results.append(
                {'is_show': False, 'show_title': m['movie']['title'], 'show_year': m['movie']['year'],
                 'show_image': 'N/A',
                 'show_slug': m['movie']['ids']['slug']})
            continue

        movie_json = urllib.request.urlopen(
            'http://www.omdbapi.com/?apikey=' + configuration.omdb_key + '&i=' + m['movie']['ids']['imdb']).read()

        # Parse the movie from the request
        movie = json.loads(movie_json)

        # When the omdb can't find the information
        if movie['Response']:
            results.append(
                {'is_show': False, 'show_title': m['movie']['title'], 'show_year': m['movie']['year'],
                 'show_image': 'N/A',
                 'show_slug': m['movie']['ids']['slug']})
            continue

        results.append(
            {'is_show': False, 'show_title': m['movie']['title'], 'show_year': m['movie']['year'],
             'show_image': movie['Poster'],
             'show_slug': m['movie']['ids']['slug']})

    return results


def get_titles(trakt_slug, is_show):
    """
    Get the various possible titles for the selected title, in both english and portuguese.

    :param trakt_slug: the selected title.
    :param is_show: true if it is a show.
    :return: the various possible titles.
    """

    if is_show:
        translations_request = urllib.request.Request('https://api.trakt.tv/shows/' + trakt_slug + '/translations')
    else:
        translations_request = urllib.request.Request('https://api.trakt.tv/movies/' + trakt_slug + '/translations')

    translations_request.add_header('trakt-api-key', configuration.trakt_key)

    try:
        translations_json = urllib.request.urlopen(translations_request).read()
    except urllib.error.HTTPError:
        print('Slug was not found!')
        return []

    # Parse the list of translations from the request
    translations = json.loads(translations_json)

    results = set()

    for t in translations:
        if t['language'] == 'en' or t['language'] == 'pt':
            results.add(t['title'])

    if is_show:
        aliases_request = urllib.request.Request('https://api.trakt.tv/shows/' + trakt_slug + '/aliases')
    else:
        aliases_request = urllib.request.Request('https://api.trakt.tv/movies/' + trakt_slug + '/aliases')

    aliases_request.add_header('trakt-api-key', configuration.trakt_key)

    try:
        aliases_json = urllib.request.urlopen(aliases_request).read()
    except urllib.error.HTTPError:
        print('Slug was not found!')
        return []

    # Parse the list of translations from the request
    aliases = json.loads(aliases_json)

    for t in aliases:
        if t['country'] == 'us' or t['country'] == 'pt':
            results.add(t['title'])

    return results


def search_db(search_list, only_between=True):
    """
    Get the results of the search in the DB, using all the texts from the search list.

    :param search_list: the list of texts to search for in the DB.
    :param only_between: true when other characters can only be between words.
    :return: results of the search in the DB.
    """

    results = set()

    for search_text in search_list:
        print('Original search text: %s' % search_text)

        # Split the search text into a list of words
        search_words = re.compile('[^0-9A-Za-zÀ-ÿ.]+').split(search_text)

        print('List of words obtained from the search text: %s' % str(search_words))

        # Create a search pattern to search the DB
        search_pattern = ''

        for w in search_words:
            if w != '':
                if search_pattern == '' and only_between:
                    search_pattern += '%s' % w
                else:
                    search_pattern += '%%%s' % w

        if only_between:
            search_pattern = '%s' % search_pattern
        else:
            search_pattern = '%s%%' % search_pattern

        print('Search pattern: %s' % search_pattern)

        db_shows = configuration.session.query(configuration.models.Show).filter(
            configuration.models.Show.show_title.ilike(search_pattern)).all()

        for s in db_shows:
            results.add(s)

    return results


def search_db_id(show_id, is_show):
    """
    Get the results of the search in the DB, using show id (either series_id or pid).

    :param show_id: the id to search for.
    :param is_show: true if it is a show.
    :return: results of the search in the DB.
    """

    if is_show:
        return configuration.session.query(configuration.models.Show).filter(
            configuration.models.Show.series_id == show_id).all()
    else:
        return configuration.session.query(configuration.models.Show).filter(
            configuration.models.Show.pid == show_id).all()


def register_reminder(show_id, is_show, reminder_type, show_season, show_episode):
    """
    Create a reminder for the given data.

    :param show_id: the id to search for.
    :param is_show: true if it is a show.
    :param reminder_type: 0 if it's a DB and 1 otherwise.
    :param show_season: show season for the reminder.
    :param show_episode: show episode for the reminder.
    """

    configuration.session.add(
        configuration.models.ShowReminder(show_id, is_show, reminder_type, show_season, show_episode))

    configuration.session.commit()


def remove_reminder(reminder_id):
    """
    Delete an id, if the request was sent by the owner.

    :param reminder_id: the id of the reminder.
    """

    reminder = configuration.session.query(configuration.models.ShowReminder).filter(configuration.models.ShowReminder.id == reminder_id).first()
    configuration.session.delete(reminder)

    configuration.session.commit()


def process_reminders():
    """Process the reminders that exist in the DB."""

    reminders = configuration.session.query(configuration.models.ShowReminder).all()

    for r in reminders:
        if r.reminder_type == 0:
            db_shows = search_db_id(r.show_id, r.is_show)
        else:
            titles = get_titles(r.show_id, r.is_show)

            db_shows = search_db(titles)

        # TODO: Send notification with shows found


def main():
    # update_show_list()

    search_text = 'blindspot'

    db_shows = search_db([search_text])

    print('Found %d results:' % len(db_shows))

    for s in db_shows:
        print(s)

    # shows = search_show_information(search_text)
    #
    # for s in shows:
    #     print(s)
    #
    # translations = ['Holmes']

    # translations = get_translations('sicario-day-of-the-soldado-2018', False)
    #
    # db_shows = search_db(translations)
    #
    # for s in db_shows:
    #     print(s)


if __name__ == "__main__":
    main()
