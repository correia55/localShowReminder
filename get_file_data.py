import openpyxl

import configuration
import models
import processing


class TVCine:
    @staticmethod
    def update_show_list(session, filename: str):
        wb = openpyxl.load_workbook(filename)

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

            date_time = date.replace(hour=time.hour, minute=time.minute)

            channel_id = session.query(models.Channel).filter(models.Channel.name == channel_name).first().id

            search_title = processing.make_searchable_title(str(title).strip())

            # Insert the instance
            show = models.Show(None, None, title, None, None, synopsis, date_time, duration, channel_id, search_title,
                               original_title, year, show_type, director, cast, languages, countries,
                               age_classification,
                               episode_title)

            session.add(show)

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

    update_show_list(session, channel_set, filename)
