import csv
import datetime
import os
import re
from typing import Optional, Dict

import openpyxl
import sqlalchemy.orm
import xlrd as xlrd

import auxiliary
import configuration
import db_calls
import get_file_data


class GenericField:
    position: int
    field_format: str

    def __init__(self, position: int, field_format: str):
        self.position = position
        self.field_format = field_format


class GenericXlsx(get_file_data.ChannelInsertion):
    channels_file = {'(New) Nat Geo Wild': ('Nat Geo Wild', 'new_nat_geo_wild.csv'),
                     'Nat Geo Wild': ('Nat Geo Wild', 'nat_geo_wild.csv'),
                     'National Geographic': ('National Geographic', 'national_geographic.csv'),
                     'FOX': ('FOX', 'fox.csv'), 'FOX Life': ('FOX Life', 'fox.csv'),
                     'FOX Comedy': ('FOX Comedy', 'fox.csv'), 'FOX Crime': ('FOX Crime', 'fox_crime.csv'),
                     'FOX Movies': ('FOX Movies', 'fox_movies.csv'),
                     'Disney Junior': ('Disney Junior', 'disney_junior.csv'),
                     'Disney Channel': ('Disney Channel', 'disney_junior.csv'),
                     '(New) FOX Crime': ('FOX Crime', 'fox.csv'),
                     '(New) FOX Movies': ('FOX Movies', 'new_fox_movies.csv'),
                     'Hollywood': ('Hollywood', 'hollywood.csv'), 'Blast': ('Blast', 'blast.csv'),
                     'História': ('História', 'historia.csv')}
    channels = list(channels_file.keys())

    @staticmethod
    def process_configuration(channel_name: str) -> Optional[Dict[str, GenericField]]:
        """
        Process the configurations file corresponding to the channel name in parameter.

        :param channel_name: the name of the channel in parameter.
        :return: a dictionary with the fields of interest, or None if invalid.
        """

        file_name = GenericXlsx.channels_file[channel_name][1]

        fields = dict()

        with open(os.path.join(configuration.base_dir, 'file_parsers', file_name)) as csvfile:
            content = csv.reader(csvfile, delimiter=';')

            # Skip the headers
            next(content, None)

            for row in content:
                fields[row[0]] = GenericField(int(row[1]), row[2])

        # Check if the essential fields are present
        if 'date' not in fields and 'date_time' not in fields:
            print('%s does not have a definition for \'date\' nor \'date_time\'!' % channel_name)
            return None

        if 'time' not in fields and 'date_time' not in fields:
            print('%s does not have a definition for \'time\' nor \'date_time\'!' % channel_name)
            return None

        if 'original_title' not in fields:
            print('%s does not have a definition for \'original_title\'!' % channel_name)

        if 'year' not in fields:
            print('%s does not have a definition for \'year\'!' % channel_name)

        if 'localized_title' not in fields:
            print('%s does not have a definition for \'localized_title\'!\nThe \'original_title\' will be used.'
                  % channel_name)
            fields['localized_title'] = fields['original_title']

        if 'localized_synopsis' not in fields:
            print('%s does not have a definition for \'localized_synopsis\'!' % channel_name)

            if 'synopsis_english' in fields:
                print('The \'synopsis_english\' will be used.')
                fields['localized_synopsis'] = fields['synopsis_english']

        if 'subgenre' not in fields:
            print('%s does not have a definition for \'subgenre\'!' % channel_name)

            if 'subgenre_english' in fields:
                print('The \'subgenre_english\' will be used.')
                fields['subgenre'] = fields['subgenre_english']

        return fields

    @staticmethod
    def process_title(title: str, title_format: str, is_movie: bool) -> str:
        """
        Process the title, removing the year.

        :param title: the title as is in the file.
        :param title_format: the format of the title.
        :param is_movie: whether this entry is a movie.
        :return: the title.
        """

        if not is_movie:
            if 'S_season_at_the_end' in title_format:
                series = re.search(r'S[0-9]+', title.strip())

                if series is not None:
                    title = title[:series.span(0)[0]]
            elif 'season_at_the_end' in title_format:
                series = re.search(r'^(.*) [0-9]+$', title.strip())

                if series is not None:
                    title = series.group(1)
            elif 'season_and_episode_at_the_end' in title_format:
                series = re.search(r'^(.*) T[0-9]+, ?[0-9]+$', title.strip())

                if series is not None:
                    title = series.group(1)

        if 'has_year' in title_format:
            # From the last position of the parenthesis
            search_result = auxiliary.search_chars(title, ['(', ')'])

            for i in range(len(search_result[0]) - 1, -1, -1):
                start_pos = search_result[0][i]
                end_pos = search_result[1][i]

                text = title[start_pos + 1:end_pos]

                # Check if it has an year
                if re.search(r'[0-9]{4}', text.strip()):
                    pass
                else:
                    continue

                # Remove the parenthesis and its context
                title = title[:search_result[0][i]] + title[search_result[1][i] + 1:]

        # Replace all quotation marks for the same quotation mark
        return re.sub('[´`]', '\'', title.strip())

    @staticmethod
    def process_date(date_value: str, date_field_format: str) -> str:
        """
        Process the date, removing unnecessary data.

        :param date_value: the data as is in the file.
        :param date_field_format: the format of the date, as in the configuration file.
        :return: the date as string.
        """

        if date_field_format == 'day_space_date':
            date_value = date_value.split(' ')[-1]
        else:
            print('The date field format: %s is not recognized!' % date_field_format)
            date_value = None

        return date_value

    @staticmethod
    def parse_time(time_value, time_format: str, file_format: str, book: xlrd.book.Book) -> Optional[datetime.time]:
        """
        Parse the time.

        :param time_value: the time as is in the file.
        :param time_format: the format of the time, as in the configuration file.
        :param file_format: the format of the file.
        :param book: the book, of the file (when it is a .xls file).
        :return: the parsed time.
        """

        try:
            if file_format == '.xls':
                try:
                    #  If the time comes in the time format
                    time = xlrd.xldate_as_datetime(time_value, book.datemode)
                except TypeError:
                    # If the time comes as text
                    time = datetime.datetime.strptime(time_value, time_format)
            else:
                try:
                    time = datetime.datetime.strptime(time_value, time_format)
                except TypeError:
                    try:
                        #  If the time already comes in the time format
                        time = time_value
                    except TypeError:
                        time = None
        except ValueError:
            time = None

        return time

    @staticmethod
    def parse_date(date_value, date_format: str, file_format: str, book: xlrd.book.Book) -> Optional[datetime.date]:
        """
        Parse the date.

        :param date_value: the date as is in the file.
        :param date_format: the format of the date, as in the configuration file.
        :param file_format: the format of the file.
        :param book: the book, of the file (when it is a .xls file).
        :return: the parsed date.
        """

        if file_format == '.xls':
            try:
                #  If the date comes in the date format
                date = xlrd.xldate_as_datetime(date_value, book.datemode)
            except TypeError:
                date = None
        else:
            date = None

        if date is None:
            try:
                # If the date comes as text
                date = datetime.datetime.strptime(date_value, date_format)
            except (TypeError, ValueError):
                #  If the date already comes in the date format
                date: datetime.date = date_value

        return date

    @staticmethod
    def add_file_data(db_session: sqlalchemy.orm.Session, filename: str, channel_name: str) \
            -> Optional[get_file_data.InsertionResult]:
        """
        Add the data, in the file, to the DB.

        :param db_session: the DB session.
        :param filename: the path to the file.
        :param channel_name: the name of the channel.
        :return: the InsertionResult.
        """

        # Get the position and format of the fields for this channel
        fields = GenericXlsx.process_configuration(channel_name)
        channel_name = GenericXlsx.channels_file[channel_name][0]

        # If it is invalid
        if fields is None:
            return None

        if '_file_format' in fields:
            file_format = fields['_file_format'].field_format
        else:
            file_format = '.xlsx'

        if file_format == '.xls':
            book = xlrd.open_workbook(filename)
            sheet = book.sheets()[0]
            rows = sheet.nrows
        else:
            # Remark: setting the read_only to true, changes the number of rows
            book = openpyxl.load_workbook(filename, data_only=True)
            sheet = book.active
            rows = sheet.max_row

        insertion_result = get_file_data.InsertionResult()

        first_event_datetime = None
        date_time = None
        date = None

        today_00_00 = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        for rx in range(rows):
            if file_format == '.xls':
                row = sheet.row(rx)
            else:
                row = sheet[rx + 1]

            if row[fields['time'].position].value is not None and row[fields['time'].position].value:
                # Parse time
                time = GenericXlsx.parse_time(row[fields['time'].position].value, fields['time'].field_format,
                                              file_format, book)
            else:
                time = None

            # If the date is in a separate row
            if '_date_separate_line' in fields:
                # While we don't have a date, skip rows where the date is empty
                if date is None:
                    if row[fields['date'].position].value is None or not row[fields['date'].position].value:
                        continue

                # If there's a date, update the current date
                if row[fields['date'].position].value is not None and row[fields['date'].position].value:
                    date_value = GenericXlsx.process_date(row[fields['date'].position].value,
                                                          fields['_date_separate_line'].field_format)

                    # Parse date, and skip the row
                    date = GenericXlsx.parse_date(date_value, fields['date'].field_format, file_format, book)
                    continue

            # Get the date_time
            if 'date_time' in fields:
                date_time = datetime.datetime.strptime(row[fields['date_time'].position].value,
                                                       fields['date_time'].field_format)
            else:
                if time is None:
                    continue

                if '_date_separate_line' not in fields:
                    date = GenericXlsx.parse_date(row[fields['date'].position].value, fields['date'].field_format,
                                                  file_format, book)

                if date is None:
                    continue

                # Combine the date with the time
                date_time = date.replace(hour=time.hour, minute=time.minute)

            if 'year' in fields:
                # Skip the rows in which the year is invalid
                if row[fields['year'].position].value is None:
                    continue

                try:
                    year = int(row[fields['year'].position].value)
                except ValueError:
                    continue
            else:
                year = None

            # Add the Lisbon timezone info, then convert it to UTC
            # and then remove the timezone info
            date_time = auxiliary.convert_datetime_to_utc(auxiliary.get_datetime_with_tz_offset(date_time)) \
                .replace(tzinfo=None)

            # Ignore old sessions
            if date_time < (today_00_00 - datetime.timedelta(days=configuration.show_sessions_validity_days)):
                continue

            if 'original_title' in fields:
                original_title = str(row[fields['original_title'].position].value)
            else:
                original_title = None

            localized_title = str(row[fields['localized_title'].position].value)

            # If it is a placeholder show or temporary program
            if '_temporary_program' in fields:
                if str(fields['_temporary_program'].field_format) in original_title:
                    continue

            if 'localized_synopsis' in fields:
                synopsis = str(row[fields['localized_synopsis'].position].value).strip()
            else:
                synopsis = None

            if 'cast' in fields:
                cast = row[fields['cast'].position].value

                if cast is not None:
                    cast = cast.strip()

                    if len(cast) == 0:
                        cast = None
            else:
                cast = None

            if 'directors' in fields:
                directors = row[fields['directors'].position].value

                # Process the directors
                if directors is not None:
                    if re.match('^ *$', directors):
                        directors = None
                    else:
                        directors = directors.split(',')

                # If the name of the directors is actually a placeholder
                if '_ignore_directors' in fields and directors:
                    if directors[0].strip() == fields['_ignore_directors'].field_format:
                        directors = None
            else:
                directors = None

            if 'creators' in fields:
                creators = row[fields['creators'].position].value

                # Process the creators
                if creators is not None:
                    if re.match('^ *$', creators):
                        creators = None
                    else:
                        creators = creators.split(',')
            else:
                creators = None

            if 'countries' in fields:
                countries = row[fields['countries'].position].value.strip()
            else:
                countries = None

            # Duration
            if 'duration' in fields:
                if fields['duration'].field_format == 'seconds':
                    duration = int(int(row[fields['duration'].position].value) / 60)
                else:
                    if file_format == '.xls':
                        try:
                            duration = xlrd.xldate_as_datetime(row[fields['duration'].position].value, book.datemode)
                        except TypeError:
                            duration = datetime.datetime.strptime(row[fields['duration'].position].value,
                                                                  fields['duration'].field_format)
                    else:
                        try:
                            duration = datetime.datetime.strptime(row[fields['duration'].position].value,
                                                                  fields['duration'].field_format)
                        except TypeError:
                            duration_time: datetime.time = row[fields['duration'].position].value
                            duration = datetime.datetime(1, 1, 1, duration_time.hour, duration_time.minute)

                    duration = duration.hour * 60 + duration.minute
            else:
                duration = None

            if 'age_classification' in fields:
                age_classification = str(row[fields['age_classification'].position].value).strip()
            else:
                age_classification = None

            if 'subgenre' in fields:
                subgenre = row[fields['subgenre'].position].value.strip()
            else:
                subgenre = None

            # Process the audio language of the session
            session_audio_language = None

            if 'session_audio_language' in fields:
                session_audio_language = row[fields['session_audio_language'].position].value

                if session_audio_language == 'VP':
                    session_audio_language = 'pt'
                else:
                    session_audio_language = None

            # Get the first event's datetime
            if first_event_datetime is None:
                first_event_datetime = date_time

            if 'season' not in fields or 'episode' not in fields:
                season = None
                episode = None
            else:
                if fields['season'].field_format == 'season_starts_with_T':
                    season_str = row[fields['season'].position].value

                    if season_str is not None:
                        season = re.search(r'^T([0-9]+)$', str(row[fields['season'].position].value).strip())

                        if season is not None:
                            season = int(season.group(1))
                    else:
                        season = None
                else:
                    try:
                        season = int(row[fields['season'].position].value)
                    except ValueError:
                        try:
                            # There are entries with a season 2.5, which will be converted to 2
                            season = int(float(row[fields['season'].position].value))
                        except ValueError:
                            season = None

                    # Some files use 0 as a placeholder
                    if season == 0:
                        season = None

                    episode = None

                if fields['episode'].field_format == 'int':
                    try:
                        episode = int(row[fields['episode'].position].value)
                    except ValueError:
                        episode = None
                elif 'title_with_Ep.' in fields['episode'].field_format:
                    series = re.search(r'Ep\. [0-9]+', row[fields['episode'].position].value.strip())

                    if series is not None:
                        episode = int(series.group(0)[4:])

                if season == 0:
                    season = None

            # Determine whether it is a movie
            is_movie = season is None or episode is None

            # Make sure the season and episode are None for movies
            if is_movie:
                season = None
                episode = None

            # Take care of the localized episode synopsis
            if 'localized_episode_synopsis' in fields:
                if is_movie:
                    synopsis = str(row[fields['localized_episode_synopsis'].position].value).strip()
                else:
                    synopsis = None

            # Genre is movie, series, documentary, news...
            genre = 'Movie' if is_movie else 'Series'

            # Process the titles
            if original_title is not None:
                original_title = GenericXlsx.process_title(original_title, fields['original_title'].field_format,
                                                           is_movie)

            localized_title = GenericXlsx.process_title(localized_title, fields['localized_title'].field_format,
                                                        is_movie)

            channel_id = db_calls.get_channel_name(db_session, channel_name).id

            # Process file entry
            insertion_result = get_file_data.process_file_entry(db_session, insertion_result, original_title,
                                                                localized_title, is_movie, genre, date_time, channel_id,
                                                                year, directors, subgenre, synopsis, season, episode,
                                                                cast=cast, duration=duration, countries=countries,
                                                                age_classification=age_classification,
                                                                creators=creators,
                                                                session_audio_language=session_audio_language)

            if insertion_result is None:
                return None

        if insertion_result.total_nb_sessions_in_file != 0:
            db_calls.commit(db_session)

            # Delete old sessions for the same time period
            file_start_datetime = first_event_datetime - datetime.timedelta(minutes=5)
            file_end_datetime = date_time + datetime.timedelta(minutes=5)

            nb_deleted_sessions = get_file_data.delete_old_sessions(db_session, file_start_datetime, file_end_datetime,
                                                                    [channel_name])

            # Set the remaining information
            insertion_result.nb_deleted_sessions = nb_deleted_sessions
            insertion_result.start_datetime = file_start_datetime
            insertion_result.end_datetime = file_end_datetime

            return insertion_result
        else:
            return None
