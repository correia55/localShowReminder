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
    channels_file = {'Nat Geo Wild': 'nat_geo_wild.csv', 'National Geographic': 'national_geographic.csv',
                     'FOX': 'fox.csv', 'FOX Life': 'fox.csv', 'FOX Crime': 'fox_crime.csv'}
    channels = list(channels_file.keys())

    @staticmethod
    def process_configuration(channel_name: str) -> Optional[Dict[str, GenericField]]:
        """
        Process the configurations file corresponding to the channel name in parameter.

        :param channel_name: the name of the channel in parameter.
        :return: a dictionary with the fields of interest, or None if invalid.
        """

        file_name = GenericXlsx.channels_file[channel_name]

        fields = dict()

        with open(os.path.join(configuration.base_dir, 'file_parsers', file_name)) as csvfile:
            content = csv.reader(csvfile, delimiter=';')

            # Skip the headers
            next(content, None)

            for row in content:
                fields[row[0]] = GenericField(int(row[1]), row[2])

        # Check if the essential fields are present
        if 'original_title' not in fields:
            print('%s does not have a definition for \'original_title\'!' % channel_name)
            return None

        if 'date' not in fields and 'date_time' not in fields:
            print('%s does not have a definition for \'date\' nor \'date_time\'!' % channel_name)
            return None

        if 'time' not in fields and 'date_time' not in fields:
            print('%s does not have a definition for \'time\' nor \'date_time\'!' % channel_name)
            return None

        if 'year' not in fields:
            print('%s does not have a definition for \'year\'!' % channel_name)
            return None

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
    def process_title(title: str, title_format: str) -> str:
        """
        Process the title, removing the year.

        :param title: the title as is in the file.
        :param title_format: the format of the title.
        :return: the title.
        """

        if 'season_at_the_end' in title_format:
            series = re.search(r'^(.*) [0-9]+$', title.strip())

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
            book = openpyxl.load_workbook(filename)
            sheet = book.active
            rows = sheet.max_row

        insertion_result = get_file_data.InsertionResult()

        first_event_datetime = None
        date_time = None

        today_00_00 = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        row_skipped = False

        for rx in range(rows):
            if file_format == '.xls':
                row = sheet.row(rx)
            else:
                row = sheet[rx + 1]

            # Skip row 1, with the headers
            if not row_skipped:
                row_skipped = True
                continue

            # Skip the rows in which the year is not a number (header rows)
            if row[fields['year'].position].value is None:
                continue

            try:
                year = int(row[fields['year'].position].value)
            except ValueError:
                continue

            # Get the date_time
            if 'date_time' in fields:
                date_time = datetime.datetime.strptime(row[fields['date_time'].position].value,
                                                       fields['date_time'].field_format)
            else:
                if file_format == '.xls':
                    date = xlrd.xldate_as_datetime(row[fields['date'].position].value, book.datemode)
                    time = xlrd.xldate_as_datetime(row[fields['time'].position].value, book.datemode)
                else:
                    date = datetime.datetime.strptime(row[fields['date'].position].value, fields['date'].field_format)
                    time = datetime.datetime.strptime(row[fields['time'].position].value, fields['time'].field_format)

                # Combine the date with the time
                date_time = date.replace(hour=time.hour, minute=time.minute)

            # Add the Lisbon timezone info, then convert it to UTC
            # and then remove the timezone info
            date_time = auxiliary.convert_datetime_to_utc(auxiliary.get_datetime_with_tz_offset(date_time)) \
                .replace(tzinfo=None)

            # Ignore old sessions
            if date_time < (today_00_00 - datetime.timedelta(days=configuration.show_sessions_validity_days)):
                continue

            original_title = str(row[fields['original_title'].position].value)
            localized_title = str(row[fields['localized_title'].position].value)

            if 'localized_synopsis' in fields:
                synopsis = str(row[fields['localized_synopsis'].position].value).strip()
            else:
                synopsis = None

            if 'cast' in fields:
                cast = row[fields['cast'].position].value
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
                if file_format == '.xls':
                    duration = xlrd.xldate_as_datetime(row[fields['duration'].position].value, book.datemode)
                else:
                    duration = datetime.datetime.strptime(row[fields['duration'].position].value,
                                                          fields['duration'].field_format)

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

            # Get the first event's datetime
            if first_event_datetime is None:
                first_event_datetime = date_time

            if 'season' not in fields or 'episode' not in fields:
                season = None
                episode = None
            else:
                try:
                    season = int(row[fields['season'].position].value)
                except ValueError:
                    try:
                        # There are entries with a season 2.5, which will be converted to 2
                        season = int(float(row[fields['season'].position].value))
                    except ValueError:
                        season = None

                episode = int(row[fields['episode'].position].value)

                if season == 0:
                    season = None

            # Determine whether or not it is a movie
            is_movie = season is None or episode is None

            # Make sure the season and episode are None for movies
            if is_movie:
                season = None
                episode = None

            # Genre is movie, series, documentary, news...
            genre = 'Movie' if is_movie else 'Series'

            # Process the title
            original_title = GenericXlsx.process_title(original_title, fields['original_title'].field_format)
            localized_title = GenericXlsx.process_title(localized_title, fields['localized_title'].field_format)

            channel_id = db_calls.get_channel_name(db_session, channel_name).id

            # Process file entry
            insertion_result = get_file_data.process_file_entry(db_session, insertion_result, original_title,
                                                                localized_title, is_movie, genre, date_time, channel_id,
                                                                year, directors, subgenre, synopsis, season, episode,
                                                                cast=cast, duration=duration, countries=countries,
                                                                age_classification=age_classification,
                                                                creators=creators)

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
