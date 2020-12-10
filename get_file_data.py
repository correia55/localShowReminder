import datetime
import re

import openpyxl
import sqlalchemy.orm

import configuration
import db_calls
import models


class TVCine:
    channels = ['TVCine Top', 'TVCine Edition', 'TVCine Emotion', 'TVCine Action']

    @staticmethod
    def update_show_list(db_session: sqlalchemy.orm.Session, filename: str):
        wb = openpyxl.load_workbook(filename)

        deleted = False

        # Skip row 1, with the headers
        for row in wb.active.iter_rows(min_row=2, max_col=15):
            # Skip rows that contain only the date
            if row[0].value is None:
                continue

            # Skip the rows in which the year is not a number (header rows)
            if not isinstance(row[4].value, int):
                continue

            # Get the data
            channel_name = row[0].value
            date = row[1].value
            time = row[2].value
            original_title = str(row[3].value)
            year = int(row[4].value)
            age_classification = row[5].value
            show_type = row[6].value
            duration = int(row[7].value)
            languages = row[8].value
            countries = row[9].value
            synopsis = row[10].value
            director = row[11].value
            cast = row[12].value
            title = str(row[13].value)
            # episode_title = row[14].value

            # Delete all shows that already exist for this month
            if not deleted:
                deleted = True
                delete_channels_monthly_data(db_session, date, TVCine.channels)

            # Combine the date with the time
            date_time = date.replace(hour=time.hour, minute=time.minute)

            # Check if it matches the regex of a series
            series = re.search('(.+) T([0-9]+),[ ]+([0-9]+)', title.strip())

            # If it is a series, extract it's season and episode
            if series:
                title = series.group(1)

                season = int(series.group(2))
                episode = int(series.group(3))

                # episode_synopsis = synopsis
                synopsis = None

                # Also get the original title without the season and episode
                series = re.search('(.+) T([0-9]+),[ ]+([0-9]+)', original_title.strip())

                if series:
                    original_title = series.group(1)
            else:
                season = None
                episode = None
                # episode_synopsis = None

            channel_name = 'TVCine ' + channel_name.strip().split()[1]
            channel_id = db_session.query(models.Channel).filter(models.Channel.name == channel_name).first().id

            # Insert the ShowData, if necessary
            show_data = db_calls.insert_if_missing_show_data(db_session, title, original_title, duration, synopsis,
                                                             year, show_type, director, cast, languages, countries,
                                                             age_classification, not series)

            if show_data is None:
                print('Insertion of Show Data failed!')
                return

            # Insert the instance
            db_calls.register_show_session(db_session, season, episode, date_time, channel_id, show_data.id,
                                           should_commit=False)

        db_calls.commit(db_session)


def delete_channels_monthly_data(db_session, date, channels):
    """
    Delete all the shows in a given month, in a set of channels.

    :param db_session: the DB session.
    :param date: a date in the month of interest.
    :param channels: the set of channels.
    """

    start_of_month = date.replace(day=1)

    if start_of_month.month != 12:
        end_of_month = start_of_month.replace(month=start_of_month.month + 1) - datetime.timedelta(seconds=1)
    else:
        end_of_month = start_of_month.replace(year=start_of_month.year, month=1) - datetime.timedelta(seconds=1)

    for channel in channels:
        channel_id = db_session.query(models.Channel).filter(models.Channel.name == channel).first().id
        shows = db_session.query(models.ShowSession) \
            .filter(models.ShowSession.channel_id == channel_id) \
            .filter(models.ShowSession.date_time > start_of_month) \
            .filter(models.ShowSession.date_time < end_of_month)
        shows.delete()

    db_session.commit()


def update_show_list(db_session: sqlalchemy.orm.Session, channel_set: int, filename: str) -> ():
    """
    Select the function according to the channel set.

    :param db_session: the DB session.
    :param channel_set: the set of channels of the file.
    :param filename: the name of the file.
    """

    # TVCine
    if channel_set == 0:
        TVCine.update_show_list(db_session, filename)


if __name__ == '__main__':
    input_channel_set = int(input('Choose one channel set for the data being inserted.\n0 - TVCine\n'))
    input_filename = input('What is the path to the file?\n')

    session = configuration.Session()

    try:
        update_show_list(session, input_channel_set, input_filename)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
