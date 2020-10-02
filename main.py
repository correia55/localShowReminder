import datetime
import threading
from enum import Enum

import flask
import flask_httpauth as fh
import flask_limiter as fl
import flask_restful as fr
import webargs
import webargs.flaskparser as fp
from flask_cors import CORS

import authentication
import configuration
import get_data
import models
import processing
from processing import ChangeType
from response_models import ReminderType


def daily_tasks():
    """Run the daily tasks."""

    # Delete old shows from the DB
    processing.clear_show_list()

    # Get the date of the last update
    last_update_date = processing.get_last_update()

    # Update the list of shows in the DB
    if get_data.configuration.selected_epg == 'MEPG':
        get_data.MEPG.update_show_list()

    # Search the shows for the existing reminders
    # The date needs to be the day after because it is at 00:00
    processing.process_reminders(last_update_date + datetime.timedelta(days=1))

    # Schedule the new update
    next_update = datetime.datetime.now() + datetime.timedelta(days=1)
    next_update = next_update.replace(hour=10, minute=0)
    threading.Timer((next_update - datetime.datetime.now()).seconds, daily_tasks).start()


class FlaskApp(flask.Flask):
    def __init__(self, *args, **kwargs):
        threading.Timer(10, daily_tasks).start()
        super(FlaskApp, self).__init__(*args, **kwargs)


basic_auth = fh.HTTPBasicAuth()
token_auth = fh.HTTPTokenAuth()
app = FlaskApp(__name__)
CORS(app, supports_credentials=True, resources={r'*': {'origins': configuration.application_link}})
api = fr.Api(app)

# Limit the number of requests that can be made in a certain time period
limiter = fl.Limiter(
    app,
    key_func=fl.util.get_remote_address,
    default_limits=['5 per second', '50 per minute', '1000 per day']
)


@basic_auth.error_handler
@token_auth.error_handler
def unauthorized():
    """The response of the server when getting unauthorized."""

    return flask.make_response('Unauthorized Access', 403)  # Should be 503


@basic_auth.verify_password
def verify_login_credentials(username, password):
    """
    Verify if the credentials are valid.

    :param username: the username.
    :param password: the password.
    :return: whether or not the credentials are valid.
    """

    return processing.check_login(username, password)


@token_auth.verify_token
def verify_access_token(token):
    """
    Verify if the access token is valid.

    :param token: the token used in the authentication.
    :return: whether or not the token is valid.
    """

    valid, user_id = authentication.validate_token(token.encode(), authentication.TokenType.ACCESS)

    return valid


# TODO: REMOVE THIS SECTION, ONLY BEING USED FOR DEBUGGING PURPOSES
# region Argument debugging
from webargs import flaskparser

parser = flaskparser.FlaskParser()


@parser.error_handler
def handle_error(error, req, schema, status_code, headers):
    return flask.make_response('Unprocessable entity: ' + error, 422)


# endregion


class LoginEP(fr.Resource):
    decorators = [basic_auth.login_required]

    def __init__(self):
        super(LoginEP, self).__init__()

    def post(self):
        """Login made by the user, generating an authentication token."""

        auth = flask.request.authorization
        user = processing.get_user_by_email(auth['username'])

        if user is not None:
            if user.verified:
                refresh_token = authentication.generate_token(user.id, authentication.TokenType.REFRESH).decode()
                username = auth['username'][:auth['username'].index('@')] if auth['username'].find('@') != -1 else auth[
                    'username']

                return flask.make_response(flask.jsonify({'token': str(refresh_token), 'username': username, **processing.get_settings(user.id)}), 200)
            else:
                return flask.make_response('Unverified Account', 400)

        # This should never happen
        else:
            print('ERROR: The user passed the decorator verification!')
            return flask.make_response('Unauthorized Access', 403)  # Should be 503


class LogoutEP(fr.Resource):
    def __init__(self):
        super(LogoutEP, self).__init__()

    logout_args = \
        {
            'refresh_token': webargs.fields.Str(required=True)
        }

    @fp.use_args(logout_args)
    def post(self, args):
        """Logout of a user's account."""

        refresh_token = args['refresh_token']

        processing.logout(refresh_token)

        return flask.make_response('', 200)


class RecoverPasswordEP(fr.Resource):
    def __init__(self):
        super(RecoverPasswordEP, self).__init__()

    recover_args = \
        {
            'token': webargs.fields.Str(required=True),
            'password': webargs.fields.Str(required=True)
        }

    @fp.use_args(recover_args)
    def put(self, args):
        """Change the password after a password recovery."""

        token = args['token']
        password = args['password']

        if processing.recover_password(token, password):
            return flask.make_response('', 200)
        else:
            return flask.make_response('Invalid Token', 400)


class RemindersEP(fr.Resource):
    decorators = [token_auth.login_required]

    def __init__(self):
        super(RemindersEP, self).__init__()

    def get(self):
        """Get the list of reminders of the user."""

        # Get the user id from the token
        token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
        user_id = authentication.get_token_field(token.encode(), 'user')

        reminders = processing.get_reminders(user_id)

        return flask.make_response(flask.jsonify({'reminder_list': processing.list_to_json(reminders)}), 200)

    register_args = \
        {
            'show_name': webargs.fields.Str(required=True),
            'is_movie': webargs.fields.Bool(required=True),
            'type': webargs.fields.Str(required=True),
            'show_season': webargs.fields.Int(),
            'show_slug': webargs.fields.Str(),
            'show_episode': webargs.fields.Int(),
            'show_language': webargs.fields.Str(),
            'show_available_translations': webargs.fields.List(webargs.fields.Str())
        }

    @fp.use_args(register_args)
    def post(self, args):
        """Register a reminder."""

        show_name = args['show_name']
        is_movie = args['is_movie']
        reminder_type = args['type']
        show_slug = None
        show_season = None
        show_episode = None
        show_language = None
        show_available_translations = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'show_season':
                show_season = v
            elif k == 'show_episode':
                show_episode = v
            elif k == 'show_slug':
                show_slug = v
            elif k == 'show_language':
                show_language = v
            elif k == 'show_available_translations':
                show_available_translations = v

        try:
            reminder_type = ReminderType[reminder_type]
        except KeyError:
            return flask.make_response('Invalid Reminder Type', 400)

        if reminder_type == ReminderType.DB and show_slug is None:
            return flask.make_response('Missing Show Slug', 400)

        if not is_movie and (show_season is None or show_episode is None):
            return flask.make_response('Missing Season Episode', 400)

        # Get the user id from the token
        token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
        user_id = authentication.get_token_field(token.encode(), 'user')

        if processing.register_reminder(show_name, is_movie, reminder_type, show_slug, show_season, show_episode,
                                        user_id, show_language, show_available_translations):
            return flask.make_response(
                flask.jsonify({'reminder_list': processing.list_to_json(processing.get_reminders(user_id))}), 201)
        else:
            return flask.make_response('Reminder Already Exists', 400)

    update_args = \
        {
            'reminder_id': webargs.fields.Int(required=True),
            'show_season': webargs.fields.Int(required=True),
            'show_episode': webargs.fields.Int(required=True)
        }

    @fp.use_args(update_args)
    def put(self, args):
        """Update a reminder."""

        reminder_id = args['reminder_id']
        show_season = args['show_season']
        show_episode = args['show_episode']

        # Get the user id from the token
        token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
        user_id = authentication.get_token_field(token.encode(), 'user')

        if processing.update_reminder(reminder_id, show_season, show_episode, user_id):
            return flask.make_response(
                flask.jsonify({'reminder_list': processing.list_to_json(processing.get_reminders(user_id))}), 201)
        else:
            return flask.make_response('', 404)

    delete_args = \
        {
            'reminder_id': webargs.fields.Int(required=True)
        }

    @fp.use_args(delete_args)
    def delete(self, args):
        """Delete a reminder."""

        reminder_id = args['reminder_id']

        # Get the user id from the token
        token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
        user_id = authentication.get_token_field(token.encode(), 'user')

        processing.remove_reminder(reminder_id, user_id)

        return flask.make_response(
            flask.jsonify({'reminder_list': processing.list_to_json(processing.get_reminders(user_id))}), 200)


class SendEmailEP(fr.Resource):
    decorators = [token_auth.login_required]

    def __init__(self):
        super(SendEmailEP, self).__init__()

    class EmailType(Enum):
        DELETION = 0
        CHANGE_OLD = 1

    email_args = \
        {
            'type': webargs.fields.Str(required=True)
        }

    @fp.use_args(email_args)
    def post(self, args):
        """Send settings email."""

        token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
        email_type = args['type']

        # Get the user id from the token
        user_id = authentication.get_token_field(token.encode(), 'user')

        # If it is a user's deletion email request
        if email_type == SendEmailEP.EmailType.DELETION.name:
            if processing.send_deletion_email(user_id):
                return flask.make_response('', 200)
            else:
                return flask.make_response('', 400)

        # If it is an email change email request
        elif email_type == SendEmailEP.EmailType.CHANGE_OLD.name:
            if processing.send_change_email_old(user_id):
                return flask.make_response('', 200)
            else:
                return flask.make_response('', 400)

        # If something else is sent
        else:
            return flask.make_response('', 400)


class SendChangeEmailEP(fr.Resource):
    def __init__(self):
        super(SendChangeEmailEP, self).__init__()

    email_args = \
        {
            'change_token': webargs.fields.Str(required=True),
            'new_email': webargs.fields.Str(required=True)
        }

    @fp.use_args(email_args)
    def post(self, args):
        """Send 'change email' email to new email address."""

        change_token = args['change_token']
        new_email = args['new_email']

        success, already_exists = processing.send_change_email_new(change_token, new_email)

        if success or already_exists:
            # Even though this means it's a failure
            # returning a different message from success would result in revealing that there's an associated account
            if already_exists:
                # TODO: SEND WARNING EMAIL
                pass

            return flask.make_response('', 200)
        else:
            return flask.make_response('', 400)


class SendPasswordRecoveryEmailEP(fr.Resource):
    def __init__(self):
        super(SendPasswordRecoveryEmailEP, self).__init__()

    logout_args = \
        {
            'email': webargs.fields.Str(required=True),
        }

    @fp.use_args(logout_args)
    def post(self, args):
        """Logout of a user's account."""

        email = args['email']
        user = processing.get_user_by_email(email)

        if user is not None:
            processing.send_password_recovery_email(user.id)

        return flask.make_response('', 200)


class SendVerificationEmailEP(fr.Resource):
    def __init__(self):
        super(SendVerificationEmailEP, self).__init__()

    send_args = \
        {
            'email': webargs.fields.Str(required=True)
        }

    @fp.use_args(send_args)
    def post(self, args):
        """Send verification email."""

        email = args['email']

        user = processing.get_user_by_email(email)

        if user is not None and not user.verified:
            if processing.send_verifcation_email(user):
                return flask.make_response('', 200)
            else:
                return flask.make_response('', 400)
        else:
            return flask.make_response('', 400)


class SessionEP(fr.Resource):
    def __init__(self):
        super(SessionEP, self).__init__()

    access_args = \
        {
            'refresh_token': webargs.fields.Str(required=True)
        }

    @fp.use_args(access_args)
    def post(self, args):
        """Getting a new access token."""

        refresh_token = args['refresh_token']

        valid, access_token = authentication.generate_access_token(refresh_token.encode())

        if valid:
            return flask.make_response(flask.jsonify({'token': str(access_token.decode())}), 200)
        else:
            return flask.make_response('Invalid Token', 403)  # Should be 503


class ShowsEP(fr.Resource):
    def __init__(self):
        super(ShowsEP, self).__init__()

    search_args = \
        {
            'search_text': webargs.fields.Str(required=True),
            'is_movie': webargs.fields.Bool(),
            'language': webargs.fields.Str(required=True)
        }

    @fp.use_args(search_args)
    def get(self, args):
        """Get search results for the search_text, using the Trakt API."""

        search_text = args['search_text']
        language = args['language']
        is_movie = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'is_movie':
                is_movie = v

        if len(search_text) < 2:
            return flask.make_response('Search Text Too Small', 400)

        shows = processing.search_show_information(search_text, is_movie, language)

        return flask.make_response(flask.jsonify({'show_list': shows}), 200)


class ShowsSessionsEP(fr.Resource):
    def __init__(self):
        super(ShowsSessionsEP, self).__init__()

    search_args = \
        {
            'search_text': webargs.fields.Str(required=True)
        }

    @fp.use_args(search_args)
    def get(self, args):
        """Get search results for the search_text in the listings."""

        search_text: str = args['search_text'].strip()

        if len(search_text) < 2:
            return flask.make_response({'Search Text Too Small'}, 400)

        search_adult = False

        # Get the user settings of whether it should look in channels with adult content or not
        if 'HTTP_AUTHORIZATION' in flask.request.headers.environ:
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            user = configuration.session.query(models.User).filter(models.User.id == user_id).first()
            search_adult = user.show_adult if user is not None else False

        db_shows = processing.search_db([search_text], complete_title=False, search_adult=search_adult)

        if len(db_shows) != 0:
            return flask.make_response(flask.jsonify({'show_list': db_shows}), 200)

        return flask.make_response('Not Found', 404)


class UsersEP(fr.Resource):
    def __init__(self):
        super(UsersEP, self).__init__()

    registration_args = \
        {
            'email': webargs.fields.Email(required=True),
            'password': webargs.fields.Str(required=True),
            'language': webargs.fields.Str()
        }

    @fp.use_args(registration_args)
    def post(self, args):
        """Create a new user's account."""

        email = args['email']
        password = args['password']

        language = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'language':
                language = v

        if processing.register_user(email, password, language):
            return flask.make_response('', 200)
        else:
            return flask.make_response('', 400)

    update_args = \
        {
            'change_token': webargs.fields.Str(),
            'verification_token': webargs.fields.Str(),
            'current_email': webargs.fields.Str(),
            'new_email': webargs.fields.Str()
        }

    @fp.use_args(update_args)
    def put(self, args):
        """Change user's settings that require a token."""

        change_token = None
        verification_token = None
        current_email = None
        new_email = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'change_token':
                change_token = v
            elif k == 'verification_token':
                verification_token = v
            elif k == 'current_email':
                current_email = v
            elif k == 'new_email':
                new_email = v

        # Update something, that requires email confirmation, on the account
        if change_token is not None:
            if processing.change_user_settings_token(change_token):
                return flask.make_response('', 200)
            else:
                return flask.make_response('Invalid Token', 400)

        # Verify the account
        elif verification_token is not None:
            verified = processing.verify_user(verification_token)

            if verified:
                return flask.make_response('', 200)
            else:
                return flask.make_response('Invalid Token', 400)

        # Correct email before verification
        elif current_email is not None and new_email is not None:
            user = processing.get_user_by_email(current_email)

            # No user was found with that email
            # or user has already verified its account
            if user is None or user.verified:
                return flask.make_response('', 400)

            if processing.change_user_settings({ChangeType.NEW_EMAIL.value: new_email}, user.id):
                if processing.send_verifcation_email(user):
                    return flask.make_response('', 200)
                else:
                    return flask.make_response('Invalid email', 400)

            else:
                return flask.make_response('', 400)

        # No parameters
        else:
            return flask.make_response('Missing Parameter', 400)

    deletion_args = \
        {
            'deletion_token': webargs.fields.Str(required=True)
        }

    @fp.use_args(deletion_args)
    def delete(self, args):
        """Delete a user's account."""

        deletion_token = args['deletion_token']

        if processing.delete_user(deletion_token):
            return flask.make_response('', 200)
        else:
            return flask.make_response('Invalid Token', 400)


class UsersSettingsEP(fr.Resource):
    decorators = [token_auth.login_required]

    def __init__(self):
        super(UsersSettingsEP, self).__init__()

    def get(self):
        """Get the user's settings, that don't require anything."""

        # Get the user id from the token
        token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
        user_id = authentication.get_token_field(token.encode(), 'user')

        settings = processing.get_settings(user_id)

        if settings != {}:
            return flask.make_response(flask.jsonify(settings), 200)
        else:
            return flask.make_response('', 404)

    update_args = \
        {
            'include_adult_channels': webargs.fields.Bool(),
            'language': webargs.fields.Str(),
        }

    @fp.use_args(update_args)
    def put(self, args):
        """Change user's settings, that don't require anything."""

        include_adult_channels = None
        language = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'include_adult_channels':
                include_adult_channels = v
            elif k == 'language':
                language = v

        # Get the user id from the token
        token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
        user_id = authentication.get_token_field(token.encode(), 'user')

        changes = {}

        # Update include_adult_channels
        if include_adult_channels is not None:
            changes[ChangeType.INCLUDE_ADULT_CHANNELS.value] = include_adult_channels

        # Update language
        if language is not None and language in models.AVAILABLE_LANGUAGES:
            changes[ChangeType.LANGUAGE.value] = language

        # If there are changes to be made
        if changes != {}:
            if processing.change_user_settings(changes, user_id):
                return flask.make_response(flask.jsonify(processing.get_settings(user_id)), 200)
            else:
                return flask.make_response('', 400)

        # If there are no changes to be made
        else:
            return flask.make_response('Invalid Parameters', 400)


class UsersBASettingsEP(fr.Resource):
    decorators = [token_auth.login_required]

    def __init__(self):
        super(UsersBASettingsEP, self).__init__()

    update_args = \
        {
            'password': webargs.fields.Str(required=True),
            'new_password': webargs.fields.Str()
        }

    @fp.use_args(update_args)
    def put(self, args):
        """Change user's settings, that require the password to be sent."""

        password = args['password']

        new_password = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'new_password':
                new_password = v

        # Get the user id from the token
        token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
        user_id = authentication.get_token_field(token.encode(), 'user')

        user = configuration.session.query(models.User).filter(models.User.id == user_id).first()

        # Check if the password is valid
        valid = verify_login_credentials(user.email, password)

        if not valid:
            return flask.make_response('Unauthorized Access', 403)  # Should be 503

        # Update new_password
        if new_password is not None:
            if password == new_password:
                return flask.make_response('Same Password', 400)

            if processing.change_user_settings({ChangeType.NEW_PASSWORD.value: new_password}, user_id):
                return flask.make_response('', 200)
            else:
                return flask.make_response('', 400)

        # No parameters
        else:
            return flask.make_response('Missing Parameter', 400)


# Functions
api.add_resource(LoginEP, '/login', endpoint='login')
api.add_resource(LogoutEP, '/logout', endpoint='logout')
api.add_resource(RecoverPasswordEP, '/recover-password', endpoint='recover_password')
api.add_resource(SendEmailEP, '/send-email', endpoint='send_email')
api.add_resource(SendChangeEmailEP, '/send-change-email', endpoint='send_change_email')
api.add_resource(SendPasswordRecoveryEmailEP, '/send-password-recovery-email', endpoint='send_password_recovery_email')
api.add_resource(SendVerificationEmailEP, '/send-verification-email', endpoint='send_verification_email')

# Resources
api.add_resource(RemindersEP, '/reminders', endpoint='reminders')
api.add_resource(SessionEP, '/session', endpoint='session')
api.add_resource(ShowsEP, '/shows', endpoint='shows')
api.add_resource(ShowsSessionsEP, '/shows-sessions', endpoint='shows_sessions')
api.add_resource(UsersEP, '/users', endpoint='users')
api.add_resource(UsersSettingsEP, '/users-settings', endpoint='users-settings')
api.add_resource(UsersBASettingsEP, '/users-ba-settings', endpoint='users-ba-settings')

if __name__ == '__main__':
    app.run(debug=True, threaded=True, use_reloader=False)
