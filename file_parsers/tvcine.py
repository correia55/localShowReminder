import datetime
import re
from typing import Optional

import openpyxl
import sqlalchemy.orm

import auxiliary
import configuration
import db_calls
import get_file_data


class TVCine(get_file_data.ChannelInsertion):
    channels = ['TVCine Top', 'TVCine Edition', 'TVCine Emotion', 'TVCine Action']

    @staticmethod
    def fix_title_order(title: str):
        """
        Fix the unordered parts of the title, if any.

        :param title: the title as is in the file.
        :return: the final title.
        """

        building = False
        start = 0

        for i in range(len(title)):
            if title[i] == ',':
                building = True
                start = i
            elif building:
                if re.match('[0-9a-zA-Z ]', title[i]) is None:
                    building = False

                    if title[start + 1:i].strip().lower() in get_file_data.unordered_words:
                        title = (' '.join([title[start + 1:i].strip(), title[:start].strip(), title[i:].strip()]))
                        break

        if building and title[start + 1:].strip().lower() in get_file_data.unordered_words:
            title = (' '.join([title[start + 1:].strip(), title[:start].strip()]))

        return title

    @staticmethod
    def process_title(title: str) -> [str, bool, bool]:
        """
        Process the title, removing special markers and reformatting the title:
        - (VP) - for portuguese audio;
        - (VO) - for original audio;
        - (extended cut) or (versão alargada) - for extended cut;
        - some of the words come unordered, thus the unordered list of words.

        :param title: the title as is in the file.
        :return: a tuple with the clean title, whether or not it is a session with the portuguese voice and whether or
        not it is a session with the extended cut.
        """

        # Replace all quotation marks for the same quotation mark
        title = re.sub('[´`]', '\'', title)

        search_result = auxiliary.search_chars(title, ['(', ')'])
        vp = False
        extended_cut = False

        # If the number of opening parenthesis is not the same as the closing ones
        if len(search_result[0]) != len(search_result[1]):
            return title.strip(), vp

        # From the last position of the parenthesis
        for i in range(len(search_result[0]) - 1, -1, -1):
            start_pos = search_result[0][i]
            end_pos = search_result[1][i]

            text = title[start_pos + 1:end_pos]

            if text == 'VP':
                vp = True
            elif text == 'VO':
                vp = False
            elif text == 'versão alargada' or text == 'extended cut':
                extended_cut = True
            elif re.search(r'[0-9]{4}', text.strip()):
                pass
            else:
                continue

            # Remove the parenthesis and its context
            title = title[:search_result[0][i]] + title[search_result[1][i] + 1:]

        return TVCine.fix_title_order(title).strip(), vp, extended_cut

    @staticmethod
    def add_file_data(db_session: sqlalchemy.orm.Session, filename: str, channel_name: str) \
            -> Optional[get_file_data.InsertionResult]:
        """
        Add the data, in the file, to the DB.

        :param db_session: the DB session.
        :param filename: the path to the file.
        :param channel_name: the name of the channel (invalid in this case).
        :return: the InsertionResult.
        """

        wb = openpyxl.load_workbook(filename)

        insertion_result = get_file_data.InsertionResult()

        first_event_datetime = None
        date_time = None

        today_00_00 = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

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
            genre = row[6].value
            duration = int(row[7].value)
            languages = row[8].value
            countries = row[9].value
            synopsis = row[10].value
            directors = row[11].value
            cast = row[12].value
            localized_title = str(row[13].value)
            # episode_title = row[14].value

            # Combine the date with the time
            date_time = date.replace(hour=time.hour, minute=time.minute)

            # Add the Lisbon timezone info, then convert it to UTC
            # and then remove the timezone info
            date_time = auxiliary.convert_datetime_to_utc(auxiliary.get_datetime_with_tz_offset(date_time)) \
                .replace(tzinfo=None)

            # Ignore old sessions
            if date_time < (today_00_00 - datetime.timedelta(days=configuration.show_sessions_validity_days)):
                continue

            # Get the first event's datetime
            if first_event_datetime is None:
                first_event_datetime = date_time

            # Check if it matches the regex of a series
            series = re.search('(.+) T([0-9]+),[ ]+([0-9]+)', localized_title.strip())

            # If it is a series, extract it's season and episode
            if series:
                localized_title = series.group(1)
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

                is_movie = True

            # Process the titles
            localized_title, vp, extended_cut = TVCine.process_title(localized_title)
            audio_language = 'pt' if vp else None

            original_title, _, _ = TVCine.process_title(original_title)

            # Sometimes the cast is switched with the director
            if cast is not None and directors is not None:
                cast_commas = auxiliary.search_chars(cast, [','])[0]
                director_commas = auxiliary.search_chars(directors, [','])[0]

                # When that happens, switch them
                if len(cast_commas) < len(director_commas):
                    aux = cast
                    cast = directors
                    directors = aux

            # Process the directors
            if directors is not None:
                directors = directors.split(',')

            # Genre is movie, series, documentary, news...
            if 'Document' not in genre:
                subgenre = genre  # Subgenre is in portuguese
                genre = 'Movie' if is_movie else 'Series'
            else:
                genre = 'Documentary'
                subgenre = None

            channel_name = 'TVCine ' + channel_name.strip().split()[1]
            channel_id = db_calls.get_channel_name(db_session, channel_name).id

            # Process file entry
            insertion_result = get_file_data.process_file_entry(db_session, insertion_result, original_title,
                                                                localized_title,
                                                                is_movie, genre, date_time, channel_id, year, directors,
                                                                subgenre,
                                                                synopsis, season, episode, cast=cast, duration=duration,
                                                                countries=countries,
                                                                age_classification=age_classification,
                                                                audio_languages=languages,
                                                                session_audio_language=audio_language,
                                                                extended_cut=extended_cut)

            if insertion_result is None:
                return None

        if insertion_result.total_nb_sessions_in_file != 0:
            db_calls.commit(db_session)

            # Delete old sessions for the same time period
            file_start_datetime = first_event_datetime - datetime.timedelta(minutes=5)
            file_end_datetime = date_time + datetime.timedelta(minutes=5)

            nb_deleted_sessions = get_file_data.delete_old_sessions(db_session, file_start_datetime, file_end_datetime,
                                                                    TVCine.channels)

            # Set the remaining information
            insertion_result.nb_deleted_sessions = nb_deleted_sessions
            insertion_result.start_datetime = file_start_datetime
            insertion_result.end_datetime = file_end_datetime

            return insertion_result
        else:
            return None
