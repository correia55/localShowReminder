import datetime
import re

import openpyxl

import auxiliary
import configuration
import models


class TVCine:
    channels = ['TVCine Top', 'TVCine Edition', 'TVCine Emotion', 'TVCine Action']

    @staticmethod
    def update_show_list(session, filename: str):
        wb = openpyxl.load_workbook(filename)

        deleted = False

        # Skip row 1, with the headers
        for row in wb.active.iter_rows(min_row=2, max_col=15):
            # Skip rows that contain only the date
            if row[0].value is None:
                continue

            # Get the data
            channel_name = row[0].value
            date = row[1].value
            time = row[2].value
            original_title = row[3].value
            year = row[4].value
            age_classification = row[5].value
            show_type = row[6].value
            duration = row[7].value
            languages = row[8].value
            countries = row[9].value
            synopsis = row[10].value
            director = row[11].value
            cast = row[12].value
            title = row[13].value
            episode_title = row[14].value

            # Delete all shows that already exist for this month
            if not deleted:
                deleted = True
                delete_channels_monthly_data(session, date, TVCine.channels)

            date_time = date.replace(hour=time.hour, minute=time.minute)

            # Check if it matches the regex of a series
            series = re.search('(.+) T([0-9]+),[ ]+([0-9]+)', str(title).strip())

            # If it is a series, extract it's season and episode
            if series:
                title = series.group(1)

                season = int(series.group(2))
                episode = int(series.group(3))
            else:
                title = str(title)

                season = None
                episode = None

            channel_name = 'TVCine ' + channel_name.strip().split()[1]
            channel_id = session.query(models.Channel).filter(models.Channel.name == channel_name).first().id

            search_title = auxiliary.make_searchable_title(title.strip())

            # Insert the instance
            show = models.Show(title, season, episode, synopsis, date_time, duration, channel_id, search_title,
                               original_title, year, show_type, director, cast, languages, countries,
                               age_classification, episode_title)

            session.add(show)

        session.commit()


def delete_channels_monthly_data(session, date, channels):
    """
    Delete all the shows in a given month, in a set of channels.

    :param session: the DB session.
    :param date: a date in the month of interest.
    :param channels: the set of channels.
    """

    start_of_month = date.replace(day=1)

    if start_of_month.month != 12:
        end_of_month = start_of_month.replace(month=start_of_month.month + 1) - datetime.timedelta(seconds=1)
    else:
        end_of_month = start_of_month.replace(year=start_of_month.year, month=1) - datetime.timedelta(seconds=1)

    for channel in channels:
        channel_id = session.query(models.Channel).filter(models.Channel.name == channel).first().id
        shows = session.query(models.Show) \
            .filter(models.Show.channel_id == channel_id) \
            .filter(models.Show.date_time > start_of_month) \
            .filter(models.Show.date_time < end_of_month)
        shows.delete()

    session.commit()


def update_show_list(session, channel_set: int, filename: str) -> ():
    """
    Select the function according to the channel set.

    :param session: the DB session.
    :param channel_set: the set of channels of the file.
    :param filename: the name of the file.
    """

    # TVCine
    if channel_set == 0:
        TVCine.update_show_list(session, filename)


if __name__ == '__main__':
    channel_set = int(input('Choose one channel set for the data being inserted.\n0 - TVCine\n'))
    filename = input('What is the path to the file?\n')

    session = configuration.Session()

    try:
        update_show_list(session, channel_set, filename)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
