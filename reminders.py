import datetime
from typing import List, Optional

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

    for a in reminder_list:
        response_reminder_list.append(response_models.Reminder(session, a))

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

        # If it is time to fire the reminder
        if datetime.datetime.utcnow() + datetime.timedelta(hours=anticipation_hours) > show_session.date_time:
            user = db_calls.get_user_id(session, reminder.user_id)
            channel = db_calls.get_channel_id(session, show_session.channel_id)

            # Add the channel to the session
            show_session.channel = channel.name

            process_emails.set_language(user.language)
            process_emails.send_alarms_email(user.email, [show_session])

            session.delete(reminder)
            session.commit()
