import datetime
import re
import xml.dom.minidom
from typing import List

import openpyxl
import sqlalchemy.orm

import auxiliary
import configuration
import db_calls
import models
import process_emails
import response_models

unordered_words = ['The', 'A', 'An', 'I', 'Un', 'Le', 'La', 'Les', 'Um']


class TVCine:
    channels = ['TVCine Top', 'TVCine Edition', 'TVCine Emotion', 'TVCine Action']

    @staticmethod
    def process_title(title: str) -> [str, bool]:
        # Replace all quotation marks for the same quotation mark
        title = re.sub('[´`]', '\'', title)

        search_result = auxiliary.search_chars(title, ['(', ')', ','])
        vp = False

        nb_parenthesis = len(search_result[0])

        if nb_parenthesis > 0:
            # Keep only the last two parenthesis
            if nb_parenthesis > 2:
                search_result[0] = search_result[0][nb_parenthesis - 2:]
                search_result[1] = search_result[1][nb_parenthesis - 2:]
                nb_parenthesis = 2

            if nb_parenthesis == 2:
                group_1 = title[search_result[0][0] + 1:search_result[1][0]]
                is_year = re.search(r'[0-9]{4}', group_1.strip())

                # We've got the result
                if is_year:
                    vp = title[search_result[0][1] + 1:search_result[1][1]] == 'VP'
                    title = title[:search_result[0][0]]
                # Keep only the last parenthesis
                else:
                    search_result[0] = search_result[0][-1:]
                    search_result[1] = search_result[1][-1:]
                    nb_parenthesis = 1

            if nb_parenthesis == 1:
                group_1 = title[search_result[0][0] + 1:search_result[1][0]]
                is_year = re.search(r'[0-9]{4}', group_1.strip())

                if is_year:
                    title = title[:search_result[0][0]]
                else:
                    is_vpvo = re.search(r'(VO|VP)', group_1.strip())

                    if is_vpvo:
                        vp = is_vpvo.group(1) == 'VP'
                        title = title[:search_result[0][0]]

        if len(search_result) > 1 and len(search_result[2]) > 0:
            last_comma = search_result[2][-1]

            after_comma = title[last_comma + 1:].strip()

            if after_comma in unordered_words:
                title = after_comma + ' ' + title[:last_comma]

        return title.strip(), vp

    @staticmethod
    def update_show_list(db_session: sqlalchemy.orm.Session, filename: str) -> int:
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

            is_movie = None
            audio_language = None

            # If it is a series, extract it's season and episode
            if series:
                title = series.group(1)
                is_movie = False

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

                # Process the titles
                title, vp = TVCine.process_title(title)
                audio_language = 'pt' if vp else None

                original_title, _ = TVCine.process_title(original_title)

                is_movie = True

            # Sometimes the cast is switched with the director
            if cast is not None and director is not None:
                cast_commas = auxiliary.search_chars(cast, [','])[0]
                director_commas = auxiliary.search_chars(director, [','])[0]

                # When that happens, switch them
                if len(cast_commas) < len(director_commas):
                    aux = cast
                    cast = director
                    director = aux

            channel_name = 'TVCine ' + channel_name.strip().split()[1]
            channel_id = db_session.query(models.Channel).filter(models.Channel.name == channel_name).first().id

            # Insert the ShowData, if necessary
            show_data = db_calls.insert_if_missing_show_data(db_session, title, original_title=original_title,
                                                             duration=duration, synopsis=synopsis, year=year,
                                                             show_type=show_type, director=director, cast=cast,
                                                             audio_languages=languages, countries=countries,
                                                             age_classification=age_classification, is_movie=is_movie)

            if show_data is None:
                print('Insertion of Show Data failed!')
                return 0

            # Insert the instance
            db_calls.register_show_session(db_session, season, episode, date_time, channel_id, show_data.id,
                                           audio_language=audio_language, should_commit=False)

            nb_shows += 1

        if nb_shows > 0:
            db_calls.commit(db_session)

            # Get the start and end of month
            start_of_month = date.replace(day=1)

            if start_of_month.month != 12:
                end_of_month = start_of_month.replace(month=start_of_month.month + 1)
            else:
                end_of_month = start_of_month.replace(year=start_of_month.year, month=1)

            process_channels_updated_data(db_session, start_of_month, end_of_month, TVCine.channels)

        return nb_shows


class Odisseia:
    channels = ['Odisseia']

    @staticmethod
    def update_show_list(db_session: sqlalchemy.orm.Session, filename: str) -> int:
        dom_tree = xml.dom.minidom.parse(filename)
        collection = dom_tree.documentElement

        events = collection.getElementsByTagName('Event')

        first_event_datetime = None

        nb_shows = 0

        for event in events:
            begin_time = event.getAttribute('beginTime')
            date_time = datetime.datetime.strptime(begin_time, '%Y%m%d%H%M%S')

            # Get the first event's datetime
            if first_event_datetime is None:
                first_event_datetime = date_time

            duration = int(int(event.getAttribute('duration')) / 60)

            epg_production = event.getElementsByTagName('EpgProduction')[0]

            genere_list = epg_production.getElementsByTagName('Genere')

            if len(genere_list) > 0:
                category = genere_list[0].firstChild.nodeValue
            else:
                category = None

            show_type = epg_production.getElementsByTagName('Subgenere')[0].firstChild.nodeValue

            epg_text = epg_production.getElementsByTagName('EpgText')[0]

            portuguese_title = epg_text.getElementsByTagName('Name')[0].firstChild.nodeValue
            broadcast_name = epg_text.getElementsByTagName('BroadcastName')[0].firstChild.nodeValue

            episode = None
            # episode_title = None

            if broadcast_name != portuguese_title:
                episode_name = re.search(r'(Ep\.|Episódio) ?([0-9]+)\.?(.*)', broadcast_name)

                if episode_name:
                    episode = episode_name.group(2)
                    # episode_title = episode_name.group(3)

                synopsis = None
                # episode_synopsis = epg_text.getElementsByTagName('ShortDescription')[0].firstChild.nodeValue
            else:
                synopsis = epg_text.getElementsByTagName('ShortDescription')[0].firstChild.nodeValue

            extended_info_elements = epg_text.getElementsByTagName('ExtendedInfo')

            original_title = None
            year = None
            director = None
            countries = None
            season = None

            for extended_info in extended_info_elements:
                attribute = extended_info.getAttribute('name')

                if attribute == 'OriginalEventName' and extended_info.firstChild is not None:
                    original_title = extended_info.firstChild.nodeValue
                elif attribute == 'Year' and extended_info.firstChild is not None:
                    year = int(extended_info.firstChild.nodeValue)
                elif attribute == 'Director' and extended_info.firstChild is not None:
                    director = extended_info.firstChild.nodeValue
                elif attribute == 'Nationality' and extended_info.firstChild is not None:
                    countries = extended_info.firstChild.nodeValue
                elif attribute == 'Cycle' and extended_info.firstChild is not None:
                    season = extended_info.firstChild.nodeValue

            if episode is not None:
                if season is None:
                    season = 1

            channel_name = 'Odisseia'
            channel_id = db_session.query(models.Channel).filter(models.Channel.name == channel_name).first().id

            # Insert the ShowData, if necessary
            show_data = db_calls.insert_if_missing_show_data(db_session, portuguese_title,
                                                             original_title=original_title, duration=duration,
                                                             synopsis=synopsis, year=year, show_type=show_type,
                                                             director=director, countries=countries, category=category,
                                                             is_movie=episode is None)

            if show_data is None:
                print('Insertion of Show Data failed!')
                return 0

            # Insert the instance
            db_calls.register_show_session(db_session, season, episode, date_time, channel_id, show_data.id,
                                           should_commit=False)

            nb_shows += 1

        if nb_shows > 0:
            db_calls.commit(db_session)

            first_day_at_start = first_event_datetime.replace(hour=0, minute=0, second=0)
            end_day_at_start = (date_time + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0) \
                               - datetime.timedelta(seconds=1)

            process_channels_updated_data(db_session, first_day_at_start, end_day_at_start, Odisseia.channels)

        return nb_shows


def process_channels_updated_data(db_session: sqlalchemy.orm.Session, start_datetime: datetime.datetime,
                                  end_datetime: datetime.datetime, channels: List[str]):
    """
    Delete sessions that no longer exist and the new sessions that are a collision to the previous ones.
    Sending an email to the users whose reminders are associated with such sessions.

    :param db_session: the DB session.
    :param start_datetime: the start of the interval of interest.
    :param end_datetime: the end of the interval of interest.
    :param channels: the set of channels.
    """

    print('Shows\' interval from %s to %s.' % (str(start_datetime), str(end_datetime)))
    print('Channels: %s.' % str(channels))

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
            .filter(models.ShowSession.date_time >= start_datetime) \
            .filter(models.ShowSession.date_time <= end_datetime).group_by(models.ShowSession.date_time,
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
                    show_session = db_calls.get_show_session_complete(db_session, s[0])
                    show_result = response_models.LocalShowResult.create_from_show_session(show_session[0],
                                                                                           show_session[1],
                                                                                           show_session[2])

                    # Get the reminders associated with this session
                    reminders = db_calls.get_reminders_session(db_session, s[0])

                    # Warn all users with the reminders for this session
                    for r in reminders:
                        user = db_calls.get_user_id(db_session, r.user_id)

                        process_emails.send_deleted_sessions_email(user.email, [show_result])

                        # Delete the reminders
                        db_session.delete(r)

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

    print('Processing file...')

    nb_shows = 0

    # TVCine
    if channel_set == 0:
        nb_shows = TVCine.update_show_list(db_session, filename)

    # Odisseia
    elif channel_set == 1:
        nb_shows = Odisseia.update_show_list(db_session, filename)

    print('%d show sessions added!\n---------------' % nb_shows)


def execute_data_insertion():
    """ Execute a data insertion. """
    input_channel_set = int(input('Choose one channel set for the data being inserted.\n'
                                  '0 - TVCine\n'
                                  '1 - Odisseia\n'))

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


if __name__ == '__main__':
    execute_data_insertion()
