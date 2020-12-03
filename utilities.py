import auxiliary
import configuration
import models


def auto_str(cls):
    """
    Automatically generate the method __str__ for a class.
    Source: https://stackoverflow.com/questions/32910096/is-there-a-way-to-auto-generate-a-str-implementation-in-python#33800620
    """

    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    cls.__str__ = __str__
    return cls


def update_searchable_titles_db():
    """ Update the searchable titles in the DB. """

    session = configuration.Session()

    shows = session.query(models.ShowSession).all()

    for show in shows:
        show.search_title = auxiliary.make_searchable_title(show.title)

    session.commit()
