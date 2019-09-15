import urllib.parse
import urllib.request
import datetime
import json
import xml.etree.ElementTree as ET
import re

import configuration
import models


class VEPG:
    @staticmethod
    def update_channel_list(ignore_hd=True):
        """
        Make a request for the channel list and add them to the db.

        :param ignore_hd: true when we're supposed to ignore HD channels.
        """

        # Request the list of channels
        channels_json = urllib.request.urlopen(configuration.channels_url).read()

        # Parse the list of channels from the request
        channels = json.loads(channels_json)['result']['channels']

        # Add the list of channels to the database
        for c in channels:
            if not ignore_hd or 'HD' not in c['name']:
                channel = models.Channel(c['id'], c['name'].strip())

                configuration.session.add(channel)

        configuration.session.commit()

    @staticmethod
    def update_show_list():
        """Make a request for the show list and update the DB."""

        # Get list of all channels from the db
        db_channels = configuration.session.query(models.Channel).all()

        # If the list of channels in the db is empty
        if not db_channels:
            VEPG.update_channel_list()

            db_channels = configuration.session.query(models.Channel).all()

        # Get the date of the last update
        db_last_update = configuration.session.query(models.LastUpdate).first()

        # If this is the first update set yesterday's date as the last update
        if db_last_update is None:
            db_last_update = models.LastUpdate(datetime.date.today() - datetime.timedelta(1))

            configuration.session.add(db_last_update)

        # Make sure the variable's date is at least as recent as today
        # so that it does not make requests for older dates that are no longer relevant
        if db_last_update.date < datetime.date.today():
            db_last_update.date = models.LastUpdate(datetime.date.today() - datetime.timedelta(1))

        # For each day until six days from today
        while db_last_update.date < datetime.date.today() + datetime.timedelta(6):
            db_last_update.date += datetime.timedelta(1)

            # Create the shows' info request url
            shows_url = configuration.shows_url

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
                channel_id = configuration.session.query(models.Channel).filter(
                    models.Channel.pid == c['id']).first().id

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
                    show = models.Show(pid, series_id, show_title, show_season, show_episode,
                                       s['programDetails'], show_datetime, s['duration'], channel_id)

                    configuration.session.add(show)

            configuration.session.commit()


class MEPG:
    @staticmethod
    def update_channel_list(ignore_hd=True):
        """
        Make a request for the channel list and add them to the db.

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
            configuration.session.add(channel)

        configuration.session.commit()

    @staticmethod
    def update_show_list_day(db_channels, db_last_update):
        """
        Make the request for the shows of a set of channels on a given day, and add them to the database.

        :param db_channels: list of channels.
        :param db_last_update: a LastUpdate object with the date for the search.
        """

        # Create the shows' info request url
        shows_url = configuration.shows_url + '?channelSiglas='

        first = True

        for c in db_channels:
            pid = urllib.parse.quote(c.pid)

            if first:
                first = False
                shows_url += pid
            else:
                shows_url += ',' + pid

        shows_url += '&startDate=' + db_last_update.date.strftime('%Y-%m-%d') + '%2000:00:01'
        shows_url += '&endDate=' + db_last_update.date.strftime('%Y-%m-%d') + '%2023:59:59'

        print(shows_url)

        # Get the shows info for our list of channels
        shows_xml = urllib.request.urlopen(shows_url).read().decode()

        # Parse the list of channels from the request
        root = ET.fromstring(shows_xml)[0]

        for c in root:
            channel_shows = c[4]
            channel_id = configuration.session.query(models.Channel).filter(
                models.Channel.pid == c[1].text).first().id

            for s in channel_shows:
                show_datetime = s[11].text

                # Skip if it's referent to a show from a different day
                if show_datetime.split()[0] != db_last_update.date.strftime('%Y-%m-%d'):
                    continue

                program_title = s[1].text
                series = re.search('(.+) T([0-9]+) - Ep\. ([0-9]+)', program_title)

                # If it is an episode of a series
                if series:
                    show_title = series.group(1)

                    show_season = int(series.group(2))
                    show_episode = int(series.group(3))
                else:
                    show_title = program_title
                    show_season = 0
                    show_episode = 0

                series_id = None
                pid = s[0].text

                # Add the show to the db
                show = models.Show(pid, series_id, show_title, show_season, show_episode,
                                   s[2].text, show_datetime, int(s[12].text) / 60, channel_id)

                configuration.session.add(show)

        configuration.session.commit()

    @staticmethod
    def update_show_list():
        """Make a request for the show list and update the DB."""

        # Get list of all channels from the db
        db_channels = configuration.session.query(models.Channel).all()

        # If the list of channels in the db is empty
        if not db_channels:
            MEPG.update_channel_list()

            db_channels = configuration.session.query(models.Channel).all()

        # Get the date of the last update
        db_last_update = configuration.session.query(models.LastUpdate).first()

        # If this is the first update set yesterday's date as the last update
        if db_last_update is None:
            db_last_update = models.LastUpdate(datetime.date.today() - datetime.timedelta(1))

            configuration.session.add(db_last_update)

        # Make sure the variable's date is at least as recent as today
        # so that it does not make requests for older dates that are no longer relevant
        if db_last_update.date < datetime.date.today():
            db_last_update.date = datetime.date.today() - datetime.timedelta(1)

        # For each day until six days from today
        while db_last_update.date < datetime.date.today() + datetime.timedelta(6):
            db_last_update.date += datetime.timedelta(1)

            # It is necessary to split the number of channels in a request in order for it to succeed
            current = []

            for i in range(len(db_channels)):
                current.append(db_channels[i])

                if i % 90 == 0 and i > 0:
                    MEPG.update_show_list_day(current, db_last_update)

                    current = []

            if len(current) != 0:
                MEPG.update_show_list_day(current, db_last_update)
