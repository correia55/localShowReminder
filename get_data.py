import urllib.parse
import urllib.request
import datetime
import xml.etree.ElementTree as ET
import re

import configuration
import models
import processing


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

        shows_added = False

        for c in root:
            channel_shows = c[4]
            channel_id = configuration.session.query(models.Channel).filter(
                models.Channel.pid == c[1].text).first().id

            for s in channel_shows:
                show_datetime = s[11].text

                # Skip if it's referent to a show from a different day
                if show_datetime.split()[0] != db_last_update.date.strftime('%Y-%m-%d'):
                    continue

                shows_added = True

                program_title = s[1].text
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

                series_id = None
                pid = s[0].text

                # Add the show to the db
                show = models.Show(pid, series_id, show_title.strip(), show_season, show_episode,
                                   s[2].text, show_datetime, int(s[12].text) / 60, channel_id,
                                   processing.make_searchable_title(show_title.strip()))

                configuration.session.add(show)

        configuration.session.commit()

        if shows_added:
            print('Shows added!')
        else:
            print('No shows were added!')

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
