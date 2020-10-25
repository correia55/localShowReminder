import csv
import datetime
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

import requests

import configuration
import models
import processing


def update_channel_list(session):
    """
    Parse the file with the channel data and update the DB.

    :param session: the db session.
    """

    db_channels = session.query(models.Channel).all()

    # Delete channels without shows
    for channel in db_channels:
        if session.query(models.Show).filter(models.Show.channel_id == channel.id).count() == 0:
            session.delete(channel)

    session.commit()

    with open(os.path.join(configuration.base_dir, 'data', 'channels.csv'), newline='') as csvfile:
        content = csv.reader(csvfile, delimiter=';')

        # Skip the headers
        next(content, None)

        for row in content:
            channel_name = row[0]
            channel_adult = row[1] == 'True'
            channel_acronym = row[2]
            channel_search_epg = row[3] == 'True'

            channels = session.query(models.Channel).filter(models.Channel.name == channel_name).all()

            # If channel already exists
            if len(channels) > 0:
                channels[0].adult = channel_adult
                channels[0].acronym = channel_acronym
                channels[0].search_epg = channel_search_epg

            # If it is a new channel
            else:
                channel = models.Channel(channel_acronym, channel_name)
                channel.adult = channel_adult
                channel.search_epg = channel_search_epg

                session.add(channel)

    session.commit()


class MEPG:
    @staticmethod
    def update_channel_list(session, ignore_hd=True):
        """
        Make a request for the channel list and add them to the db.

        :param session: the db session.
        :param ignore_hd: true when we're supposed to ignore HD channels.
        """

        # Request the list of channels
        channels_xml = urllib.request.urlopen(configuration.channels_url).read().decode()

        # Parse the list of channels from the request
        root = ET.fromstring(channels_xml)[0]

        # Create a dictionary without duplicate channels
        channels = {}

        for c in root:
            name = c[0].text

            if not ignore_hd or 'HD' not in name:
                channel = models.Channel(c[1].text, name.strip())

                if name not in channels:
                    channels[name] = channel

        # Add unique channels to list
        for n, channel in channels.items():
            session.add(channel)

        session.commit()

    @staticmethod
    def update_show_list_day(session, db_channels: [models.Channel], db_last_update):
        """
        Make the request for the shows of a set of channels on a given day, and add them to the database.

        :param session: the db session.
        :param db_channels: list of channels.
        :param db_last_update: a LastUpdate object with the date for the search.
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
        ''' % (channels, db_last_update.date.strftime('%Y-%m-%d'),
               (db_last_update.date + datetime.timedelta(days=1)).strftime('%Y-%m-%d'))

        print(payload)

        # Get the shows info for our list of channels
        response_json = requests.post(shows_url, data=payload, headers={'Content-Type': 'application/json'}).json()

        shows_added = False

        for c in response_json['d']['channels']:
            channel_shows = c['programs']
            channel_id = session.query(models.Channel).filter(
                models.Channel.acronym == c['sigla']).first().id

            for s in channel_shows:
                show_date = datetime.datetime.strptime(s['date'], '%d-%m-%Y').strftime('%Y-%m-%d')

                # Skip if it's referent to a show from a different day
                if show_date != db_last_update.date.strftime('%Y-%m-%d'):
                    continue

                show_datetime = '%s %s' % (show_date, s['timeIni'])

                shows_added = True

                program_title = s['name']
                series = re.search('(.+) T([0-9]+) - Ep\. ([0-9]+)', program_title)

                # If it is an episode of a series with season and episode
                if series:
                    show_title = series.group(1)

                    show_season = int(series.group(2))
                    show_episode = int(series.group(3))
                else:
                    series = re.search('(.+) - Ep\. ([0-9]+)', program_title)

                    # If it is an episode of a series but only has episode
                    if series:
                        show_title = series.group(1)

                        show_season = 1
                        show_episode = int(series.group(2))
                    else:
                        show_title = program_title

                        show_season = None
                        show_episode = None

                series_id = None
                pid = s['uniqueId']

                # Add the show to the db
                show = models.Show(pid, series_id, show_title.strip(), show_season, show_episode,
                                   '', show_datetime, 0, channel_id,
                                   processing.make_searchable_title(show_title.strip()))

                session.add(show)

        session.commit()

        if shows_added:
            print('Shows added!')
        else:
            print('No shows were added!')

    @staticmethod
    def update_show_list(session):
        """
        Make a request for the show list and update the DB.

        :param session: the db session.
        """

        # Get list of all channels from the db
        db_channels = session.query(models.Channel).filter(models.Channel.search_epg == True).all()

        # Get the date of the last update
        db_last_update = session.query(models.LastUpdate).first()

        # If this is the first update set yesterday's date as the last update
        if db_last_update is None:
            db_last_update = models.LastUpdate(datetime.date.today() - datetime.timedelta(1))

            session.add(db_last_update)

        # Make sure the variable's date is at least as recent as today
        # so that it does not make requests for older dates that are no longer relevant
        if db_last_update.date < datetime.date.today():
            db_last_update.date = datetime.date.today() - datetime.timedelta(1)

        max_channels_request = int(configuration.max_channels_request)

        # For each day until six days from today
        while db_last_update.date < datetime.date.today() + datetime.timedelta(6):
            db_last_update.date += datetime.timedelta(1)

            # It is necessary to split the number of channels in a request in order for it to succeed
            current = []

            for i in range(len(db_channels)):
                current.append(db_channels[i])

                if i % max_channels_request == 0 and i > 0:
                    MEPG.update_show_list_day(session, current, db_last_update)

                    current = []

            if len(current) != 0:
                MEPG.update_show_list_day(session, current, db_last_update)

        print('Shows list updated!')
