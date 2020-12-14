import datetime
import re

import openpyxl
import sqlalchemy.orm

import configuration
import db_calls
import models
import process_emails
import response_models


class TVCine:
    channels = ['TVCine Top', 'TVCine Edition', 'TVCine Emotion', 'TVCine Action']

    @staticmethod
    def update_show_list(db_session: sqlalchemy.orm.Session, filename: str):
        wb = openpyxl.load_workbook(filename)

        nb_shows = 0

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

            nb_shows += 1

        db_calls.commit(db_session)

        print('%d show sessions added!' % nb_shows)

        process_channels_updated_data(session, date, TVCine.channels)


def process_channels_updated_data(db_session, date, channels):
    """
    Delete sessions that no longer exist and the new sessions that are a collision to the previous ones.
    Sending an email to the users whose reminders are associated with such sessions.

    :param db_session: the DB session.
    :param date: a date in the month of interest.
    :param channels: the set of channels.
    """

    # Get the start and end of month
    start_of_month = date.replace(day=1)

    if start_of_month.month != 12:
        end_of_month = start_of_month.replace(month=start_of_month.month + 1) - datetime.timedelta(seconds=1)
    else:
        end_of_month = start_of_month.replace(year=start_of_month.year, month=1) - datetime.timedelta(seconds=1)

    nb_shows_maintained = 0
    nb_shows_deleted = 0
    nb_shows_added = 0

    now = datetime.datetime.now() - datetime.timedelta(hours=1)

    # Get all of the shows of interest
    for channel in channels:
        channel_id = db_session.query(models.Channel).filter(models.Channel.name == channel).first().id
        shows = db_session.query(sqlalchemy.func.max(models.ShowSession.id),
                                 sqlalchemy.func.max(models.ShowSession.update_timestamp),
                                 sqlalchemy.func.count(models.ShowSession.date_time)) \
            .filter(models.ShowSession.channel_id == channel_id) \
            .filter(models.ShowSession.date_time > start_of_month) \
            .filter(models.ShowSession.date_time < end_of_month).group_by(models.ShowSession.date_time,
                                                                          models.ShowSession.show_id).all()

        for s in shows:
            # If the session already existed and continues to exist, then delete the new one
            if s[2] == 2:
                nb_shows_maintained += 1
                db_session.query(models.ShowSession.id).filter(models.ShowSession.id == s[0]).delete()
            else:
                # If it is an old session, then it needs to be deleted and the users warned
                if now > s[1]:
                    nb_shows_deleted += 1

                    # Get the session
                    show_session = db_calls.get_show_session_complete(session, s[0])
                    show_result = response_models.LocalShowResult.create_from_show_session(show_session[0],
                                                                                           show_session[2],
                                                                                           show_session[3],
                                                                                           show_session[1])

                    # Get the reminders associated with this session
                    reminders = db_calls.get_reminders_session(session, s[0])

                    # Warn all users with the reminders for this session
                    for r in reminders:
                        user = db_calls.get_user_id(session, r.user_id)

                        process_emails.send_deleted_sessions_email(user.email, [show_result])

                        # Delete the reminders
                        session.delete(r)

                    db_session.query(models.ShowSession.id).filter(models.ShowSession.id == s[0]).delete()
                # If it is a new session, nothing to do
                else:
                    nb_shows_added += 1

    db_session.commit()

    print('%d show sessions maintained!' % nb_shows_maintained)
    print('%d show sessions deleted!' % nb_shows_deleted)
    print('%d show sessions added!' % nb_shows_added)


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
