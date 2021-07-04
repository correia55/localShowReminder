import sqlalchemy.orm

import configuration
import process_emails
import processing


def weekly_tasks(db_session: sqlalchemy.orm.Session):
    """
    Run the weekly tasks.

    :param db_session: the db session.
    """

    processing.calculate_highlights(db_session)
    print('Highlights calculated!')


def main():
    configuration.initialize()
    process_emails.initialize()

    session = configuration.Session()

    try:
        weekly_tasks(session)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
