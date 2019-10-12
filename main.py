import flask
import webargs
import threading
import datetime

from flask_cors import CORS, cross_origin

import flask_restful as fr
import flask_httpauth as fh
import flask_limiter as fl
import webargs.flaskparser as fp

import authentication
import processing
import get_data


def daily_tasks():
    """Run the daily tasks."""

    # Get the date of the last update
    last_update_date = processing.get_last_update()

    processing.clear_show_list()

    if get_data.configuration.selected_epg == 'MEPG':
        get_data.MEPG.update_show_list()

    processing.process_reminders(last_update_date)

    # Schedule the new update
    next_update = datetime.datetime.now() + datetime.timedelta(days=1)
    next_update = next_update.replace(hour=10, minute=0)
    threading.Timer((next_update - datetime.datetime.now()).seconds, daily_tasks).start()


class FlaskApp(flask.Flask):
    def __init__(self, *args, **kwargs):
        # TODO: UNCOMMENT THIS WHEN UPDATE IS NEEDED
        # threading.Timer(10, daily_tasks).start()
        super(FlaskApp, self).__init__(*args, **kwargs)


basic_auth = fh.HTTPBasicAuth()
token_auth = fh.HTTPTokenAuth()
app = FlaskApp(__name__)
CORS(app, support_credentials=True)
api = fr.Api(app)

# Limit the number of requests that can be made in a certain time period
limiter = fl.Limiter(
    app,
    key_func=fl.util.get_remote_address,
    default_limits=['5 per second', '50 per minute', '1000 per day']
)


@basic_auth.error_handler
def unauthorized():
    """The response of the server when getting unauthorized."""

    return flask.make_response('Unauthorized Access', 403)


@basic_auth.verify_password
def verify_login_credentials(username, password):
    """
    Verify if the credentials are valid.

    :param username: the username.
    :param password: the password.
    :return: whether or not the credentials are valid.
    """

    return processing.check_login(username, password)


@token_auth.error_handler
def unauthorized():
    """The response of the server when getting unauthorized."""

    return flask.make_response('Unauthorized Access', 403)


@token_auth.verify_token
def verify_auth_token(token):
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


class RegistrationEP(fr.Resource):
    def __init__(self):
        super(RegistrationEP, self).__init__()

    registration_args = \
        {
            'email': webargs.fields.Str(required=True),
            'password': webargs.fields.Str(required=True)
        }

    @fp.use_args(registration_args)
    @cross_origin(supports_credentials=True)
    def post(self, args):
        """Register a new user."""

        email = args['email']
        password = args['password']

        processing.register_user(email, password)

        return flask.jsonify({'registration': 'The registration was a success, check your email!'})


class LoginEP(fr.Resource):
    decorators = [basic_auth.login_required]

    def __init__(self):
        super(LoginEP, self).__init__()

    @cross_origin(supports_credentials=True)
    def post(self):
        """Login made by the user, generating an authentication token."""

        auth = flask.request.authorization
        user = processing.get_user_by_email(auth['username'])

        if user is not None:
            auth_token = authentication.generate_token(user.id, authentication.TokenType.REFRESH).decode()
            return flask.jsonify({'login': 'The login was a success!', 'token': str(auth_token)})
        else:
            return flask.jsonify({'login': 'The login failed!'})


class LogoutEP(fr.Resource):
    def __init__(self):
        super(LogoutEP, self).__init__()

    logout_args = \
        {
            'auth_token': webargs.fields.Str(required=True)
        }

    @fp.use_args(logout_args)
    @cross_origin(supports_credentials=True)
    def post(self, args):
        """Logout of a user's account."""

        auth_token = args['auth_token']

        processing.logout(auth_token)

        return flask.jsonify({'logout': 'The logout was successful!'})


class AccessEP(fr.Resource):
    def __init__(self):
        super(AccessEP, self).__init__()

    access_args = \
        {
            'refresh_token': webargs.fields.Str(required=True)
        }

    @fp.use_args(access_args)
    @cross_origin(supports_credentials=True)
    def post(self, args):
        """Getting a new access token."""

        auth_token = args['refresh_token']

        valid, access_token = authentication.generate_access_token(auth_token.encode())

        if valid:
            return flask.jsonify({'access': 'valid token', 'token': str(access_token.decode())})
        else:
            return flask.jsonify({'access': 'invalid token', 'token': access_token})


class SearchTraktEP(fr.Resource):
    def __init__(self):
        super(SearchTraktEP, self).__init__()

    search_args = \
        {
            'search_text': webargs.fields.Str(required=True)
        }

    @fp.use_args(search_args)
    @cross_origin(supports_credentials=True)
    def get(self, args):
        """Get search results for the search_text, using the Trakt API."""

        search_text = args['search_text']

        if len(search_text) < 3:
            return flask.jsonify({'search_trakt': 'Search text needs at least three characters!'})

        shows = processing.search_show_information(search_text)

        return flask.jsonify({'search_trakt': shows})


class SearchDBTraktIdEP(fr.Resource):
    def __init__(self):
        super(SearchDBEP, self).__init__()

    search_args = \
        {
            'trakt_id': webargs.fields.Str(required=True),
            'show_type': webargs.fields.Str(required=True)
        }

    @fp.use_args(search_args)
    @cross_origin(supports_credentials=True)
    def get(self, args):
        """Get search results for the search_text in the DB."""

        trakt_id = args['trakt_id']
        show_type = args['show_type']

        if show_type != 'show' and show_type != 'movie':
            return flask.jsonify({'search_db': 'The type of show needs to be show or movie!'})

        titles = processing.get_titles(trakt_id, show_type)

        db_shows = processing.search_db(titles, only_between=True, search_adult=True)

        if len(db_shows) != 0:
            return flask.jsonify({'search_db': db_shows})

        return flask.jsonify({'search_db': 'No results found!'})


class SearchDBEP(fr.Resource):
    def __init__(self):
        super(SearchDBEP, self).__init__()

    search_args = \
        {
            'search_text': webargs.fields.Str(required=True),
            'search_adult': webargs.fields.Bool()
        }

    @fp.use_args(search_args)
    @cross_origin(supports_credentials=True)
    def get(self, args):
        """Get search results for the search_text in the DB."""

        search_text: str = args['search_text']
        search_adult: bool = False

        for k, v in args.items():
            if v is None:
                continue

            if k == 'search_adult':
                search_adult = v

        db_shows = processing.search_db([search_text], only_between=False, search_adult=search_adult)

        if len(db_shows) != 0:
            return flask.jsonify({'search_db': db_shows})

        return flask.jsonify({'search_db': 'No results found!'})


class ReminderEP(fr.Resource):
    decorators = [token_auth.login_required]

    def __init__(self):
        super(ReminderEP, self).__init__()

    @cross_origin(supports_credentials=True)
    def get(self):
        """Get the list of reminders of the user."""

        # Get the user id from the token
        token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
        user_id = authentication.access_token_field(token.encode(), 'user')

        reminders = processing.get_reminders(user_id)

        return flask.jsonify({'reminder': processing.list_to_json(reminders)})

    register_args = \
        {
            'show_id': webargs.fields.Str(required=True),
            'is_show': webargs.fields.Bool(required=True),
            'type': webargs.fields.Str(required=True),
            'show_season': webargs.fields.Int(),
            'show_episode': webargs.fields.Int(),
            'comparison_type': webargs.fields.Int()
        }

    @fp.use_args(register_args)
    @cross_origin(supports_credentials=True)
    def post(self, args):
        """Register a reminder."""

        show_id = args['show_id']
        is_show = args['is_show']
        reminder_type = args['type']

        show_season = None
        show_episode = None
        comparison_type = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'show_season':
                show_season = v
            elif k == 'show_episode':
                show_episode = v
            elif k == 'comparison_type':
                comparison_type = v

        if reminder_type == 'DB':
            reminder_type = 0
        elif reminder_type == 'TRAKT':
            reminder_type = 1
        else:
            return flask.jsonify({'reminder': 'Unknown type!'})

        # Get the user id from the token
        token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
        user_id = authentication.access_token_field(token.encode(), 'user')

        processing.register_reminder(show_id, is_show, reminder_type, show_season, show_episode, comparison_type,
                                     user_id)

        return flask.jsonify({'reminder': 'Reminder successfully registered!'})

    delete_args = \
        {
            'reminder_id': webargs.fields.Int(required=True)
        }

    @fp.use_args(delete_args)
    @cross_origin(supports_credentials=True)
    def delete(self, args):
        """Delete a reminder."""

        reminder_id = args['reminder_id']

        processing.remove_reminder(reminder_id)

        return flask.jsonify({'reminder': 'Reminder successfully removed!'})


api.add_resource(RegistrationEP, '/0.1/registration', endpoint='registration')
api.add_resource(LoginEP, '/0.1/login', endpoint='login')
api.add_resource(LogoutEP, '/0.1/logout', endpoint='logout')
api.add_resource(AccessEP, '/0.1/access', endpoint='access')
api.add_resource(SearchTraktEP, '/0.1/search_trakt', endpoint='search_trakt')
api.add_resource(SearchDBEP, '/0.1/search_db', endpoint='search_db')
api.add_resource(ReminderEP, '/0.1/reminder', endpoint='reminder')

if __name__ == '__main__':
    app.run(debug=True, threaded=True, use_reloader=False)
