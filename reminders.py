import datetime
from typing import List, Optional, Tuple

import sqlalchemy.orm

import db_calls
import models
import process_emails
import response_models


def get_reminders(session, user_id: int) -> List[response_models.Reminder]:
    """
    Get a list of reminders for the user who's id is user_id.

    :param session: the db session.
    :param user_id: the id of the user.
    :return: a list of reminders for the user who's id is user_id.
    """

    if not user_id:
        return []

    reminder_list = db_calls.get_reminders_user(session, user_id)

    # Convert the reminder list to a response reminder list
    response_reminder_list = []

    for r in reminder_list:
        reminder_session_tuple = db_calls.get_show_session_complete(session, r.session_id)
        response_reminder_list.append(response_models.Reminder(session, reminder_session_tuple))

    return response_reminder_list


def register_reminder(session: sqlalchemy.orm.Session, show_session_id: int, anticipation_minutes: int, user_id: int) \
        -> Optional[models.Reminder]:
    """
    Register a reminder.

    :param session: the db session.
    :param show_session_id: the id of the show session.
    :param anticipation_minutes: the minutes before the show's session for the reminder.
    :param user_id: the id of the user.
    :return: the created reminder.
    """

    show_session = db_calls.get_show_session(session, show_session_id)

    # Check if the session exists
    if not show_session:
        return None

    anticipation_hours = int(anticipation_minutes / 60)

    # Check now is at least two hours before the anticipation hours
    if datetime.datetime.now() + datetime.timedelta(hours=anticipation_hours + 2) > show_session.date_time:
        return None

    return db_calls.register_reminder(session, show_session_id, anticipation_minutes, user_id)


def update_reminder(session: sqlalchemy.orm.Session, reminder_id: int, anticipation_minutes: int, user_id: int) \
        -> Tuple[bool, Optional[str]]:
    """
    Update a reminder.

    :param session: the db session.
    :param reminder_id: the id of the reminder.
    :param anticipation_minutes: the minutes before the show's session for the reminder.
    :param user_id: the id of the user.
    :return: a tuple with the success status and an error message.
    """

    # Get the reminder
    reminder = db_calls.get_reminder_id_user(session, reminder_id, user_id)

    # Check if the reminder exists
    if reminder is None:
        return False, 'Not found'

    # Get the corresponding show session
    show_session = db_calls.get_show_session(session, reminder.session_id)

    # Check now is at least two hours before the anticipation hours
    anticipation_hours = int(anticipation_minutes / 60)

    if datetime.datetime.now() + datetime.timedelta(hours=anticipation_hours + 2) > show_session.date_time:
        return False, 'Invalid anticipation time'

    if db_calls.update_reminder(session, reminder, anticipation_minutes):
        return True, None
    else:
        return False, 'Same anticipation time'


def process_reminders(session: sqlalchemy.orm.Session) -> None:
    """
    Process the reminders that exist in the DB, sending an email when the session is within the desired time frame.

    :param session: the db session.
    """

    reminders_sessions = db_calls.get_sessions_reminders(session)

    for a_s in reminders_sessions:
        reminder: models.Reminder = a_s[0]
        show_session: models.ShowSession = a_s[1]

        anticipation_hours = int(reminder.anticipation_minutes / 60)

        # Replace the time minutes and seconds so that it can ensure the anticipation hours
        show_time = show_session.date_time.replace(minute=0, second=0) - datetime.timedelta(minutes=5)

        # If it is time to fire the reminder
        if datetime.datetime.utcnow() + datetime.timedelta(hours=anticipation_hours) > show_time:
            show_session_tuple = db_calls.get_show_session_complete(session, show_session.id)
            user = db_calls.get_user_id(session, reminder.user_id)

            local_show_result = response_models.LocalShowResult.create_from_show_session(show_session_tuple[0],
                                                                                         show_session_tuple[2],
                                                                                         show_session_tuple[3],
                                                                                         show_session_tuple[1])

            process_emails.set_language(user.language)
            process_emails.send_reminders_email(user.email, [local_show_result])

            session.delete(reminder)
            session.commit()
