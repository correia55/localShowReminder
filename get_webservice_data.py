import csv
import datetime
import os
import re
import time

import requests
import sqlalchemy.orm

import auxiliary
import configuration
import db_calls
import models


def update_channel_list(session: sqlalchemy.orm.Session):
    """
    Parse the file with the channel data and update the DB.

    :param session: the db session.
    """

    db_channels = db_calls.get_channel_list(session)

    # Delete channels without shows
    for channel in db_channels:
        if db_calls.count_channel_sessions(session, channel.id) == 0:
            print('Deleted channel without content: %s!' % channel.name)
            db_calls.delete_channel_show_data(session, channel.id)
            session.delete(channel)

    db_calls.commit(session)

    with open(os.path.join(configuration.base_dir, 'data', 'channels.csv'), newline='') as csvfile:
        content = csv.reader(csvfile, delimiter=';')

        # Skip the headers
        next(content, None)

        for row in content:
            channel_name = row[0]
            channel_adult = row[1] == 'True'
            channel_acronym = row[2]
            channel_search_epg = row[3] == 'True'

            channel = db_calls.get_channel_name(session, channel_name)

            # If channel already exists
            if channel is not None:
                channel.adult = channel_adult
                channel.acronym = channel_acronym
                channel.search_epg = channel_search_epg

            # If it is a new channel
            else:
                channel = models.Channel(channel_acronym, channel_name)
                channel.adult = channel_adult
                channel.search_epg = channel_search_epg

                session.add(channel)

    session.commit()


class MEPG:
    @staticmethod
    def update_show_list_day(session: sqlalchemy.orm.Session, db_channels: [models.Channel],
                             last_update_date: datetime.date):
        """
        Make the request for the shows of a set of channels on a given day, and add them to the database.

        :param session: the db session.
        :param db_channels: list of channels.
        :param last_update_date: the date of the last update.
        """

        # Create the shows' info request url
        shows_url = configuration.shows_url

        channels = ''

        first = True

        for c in db_channels:
            if first:
                first = False
                channels += '"%s"' % c.acronym
            else:
                channels += ',\n\t"%s"' % c.acronym

        payload = '''
{
    "service": "channelsguide",
    "channels": [
    %s
    ],
    "dateStart": "%sT00:00:00.000Z",
    "dateEnd": "%sT00:00:00.000Z",
    "accountID": ""
}
        ''' % (channels, last_update_date.strftime('%Y-%m-%d'),
               (last_update_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d'))

        print(payload)

        # Try the request X times
        tries = 0

        while tries < configuration.max_number_retries:
            try:
                # Get the shows info for our list of channels
                response_json = requests.post(shows_url, data=payload, headers={'Content-Type': 'application/json'},
                                              verify=False).json()
            except:
                # Wait 10 seconds and then retry
                time.sleep(10)

                tries = tries + 1
                continue

            break

        # If it exceeded the number of tries
        if tries == configuration.max_number_retries:
            print("Exceeded maximum number of retries, skipping this call!")
            return

        shows_added = False

        for c in response_json['d']['channels']:
            channel_shows = c['programs']
            channel_id = db_calls.get_channel_acronym(session, c['sigla']).id

            for s in channel_shows:
                show_datetime = datetime.datetime.strptime(s['date'], '%d-%m-%Y')
                show_time = datetime.datetime.strptime(s['timeIni'], '%H:%M')

                # Combine the date and time
                show_datetime = show_datetime.replace(hour=show_time.hour, minute=show_time.minute)

                # Add the Lisbon timezone info, then convert it to UTC
                # and then remove the timezone info
                show_datetime = auxiliary.convert_datetime_to_utc(auxiliary.get_datetime_with_tz_offset(show_datetime)) \
                    .replace(tzinfo=None)

                # Skip if it's referent to a show from a different day
                if show_datetime.date() != last_update_date:
                    continue

                program_title = str(s['name'])
                is_movie = None
                series = re.search('(.+) T([0-9]+) - Ep\. ([0-9]+)', program_title)

                # If it is an episode of a series with season and episode
                if series:
                    show_title = str(series.group(1))

                    show_season = int(series.group(2))
                    show_episode = int(series.group(3))
                    is_movie = False
                else:
                    series = re.search('(.+) - Ep\. ([0-9]+)', program_title)

                    # If it is an episode of a series but only has episode
                    if series:
                        show_title = str(series.group(1))

                        show_season = 1
                        show_episode = int(series.group(2))
                        is_movie = False
                    else:
                        show_title = program_title

                        show_season = None
                        show_episode = None

                # Add the show to the db
                show_data = db_calls.insert_if_missing_show_data(session, show_title.strip(), is_movie=is_movie)[1]

                if show_data is None:
                    print('ERROR: The registration of the show %s failed!' % show_title)
                    continue

                shows_added = True

                db_calls.register_show_session(session, show_season, show_episode, show_datetime, channel_id,
                                               show_data.id, should_commit=False)

        session.commit()

        if shows_added:
            print('Shows added!')
        else:
            print('No shows were added!')

    @staticmethod
    def update_show_list(session: sqlalchemy.orm.Session):
        """
        Make a request for the show list and update the DB.

        :param session: the db session.
        """

        # Get list of all channels from the db that should be requested to the EPG
        db_channels = db_calls.get_epg_channel_list(session)

        # Get the date of the last update
        db_last_update = db_calls.get_last_update(session)

        # If this is the first update set yesterday's date as the last update
        if db_last_update is None:
            db_last_update = models.LastUpdate(datetime.date.today() - datetime.timedelta(days=1),
                                               datetime.datetime.utcnow())

            session.add(db_last_update)

        # Make sure the variable's date is at least as recent as today
        # so that it does not make requests for older dates that are no longer relevant
        if db_last_update.epg_date < datetime.date.today():
            db_last_update.epg_date = datetime.date.today() - datetime.timedelta(days=1)

        max_channels_request = int(configuration.max_channels_request)

        # For each day until six days from today
        while db_last_update.epg_date < datetime.date.today() + datetime.timedelta(days=6):
            db_last_update.epg_date += datetime.timedelta(days=1)

            # It is necessary to split the number of channels in a request in order for it to succeed
            current = []

            for i in range(len(db_channels)):
                current.append(db_channels[i])

                if i % max_channels_request == 0 and i > 0:
                    MEPG.update_show_list_day(session, current, db_last_update.epg_date)

                    current = []

            if len(current) != 0:
                MEPG.update_show_list_day(session, current, db_last_update.epg_date)

        db_calls.commit(session)
