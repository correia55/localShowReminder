import auxiliary
import configuration
import models


def update_searchable_titles_db():
    """ Update the searchable titles in the DB. """

    session = configuration.Session()

    shows = session.query(models.Show).all()

    for show in shows:
        show.search_title = auxiliary.make_searchable_title(show.title)

    session.commit()
