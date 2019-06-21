import flask
import webargs
import threading
import time

import flask_restful as fr
import flask_httpauth as fh
import flask_limiter as fl
import webargs.flaskparser as fp

import processing

basic_auth = fh.HTTPBasicAuth()
app = flask.Flask(__name__)
api = fr.Api(app)

# Limit the number of requests that can be made in a certain time period
limiter = fl.Limiter(
    app,
    key_func=fl.util.get_remote_address,
    default_limits=['5 per second', '50 per minute', '1000 per day']
)


def list_to_json(list_of_objects):
    result = []

    for o in list_of_objects:
        result.append(o.to_dict())

    return result


def update_list():
    """Update the list of movies every day."""

    while True:
        processing.update_show_list()

        time.sleep(86400)


@app.before_first_request
def start_update_thread():
    thread = threading.Thread(target=update_list)
    thread.start()


class SearchTextEP(fr.Resource):
    def __init__(self):
        super(SearchTextEP, self).__init__()

    search_args = \
        {
            'search_text': webargs.fields.Str(required=True)
        }

    @fp.use_args(search_args)
    def get(self, args):
        """Get search results for the search_text."""

        search_text = args['search_text']

        if len(search_text) < 3:
            return flask.jsonify({'search': 'Search text needs at least three characters!'})

        db_shows = processing.search_db([search_text])

        if len(db_shows) != 0:
            return flask.jsonify({'search': 'shows', 'shows': list_to_json(db_shows)})

        shows = processing.search_show_information(search_text)

        return flask.jsonify({'search': 'trakt', 'shows': shows})


class SearchIdEP(fr.Resource):
    def __init__(self):
        super(SearchIdEP, self).__init__()

    search_args = \
        {
            'search_id': webargs.fields.Str(required=True),
            'is_show': webargs.fields.Bool(required=True)
        }

    @fp.use_args(search_args)
    def get(self, args):
        """Get search results for the search id."""

        search_id = args['search_id']
        is_show = args['is_show']

        translations = processing.get_translations(search_id, is_show)

        db_shows = processing.search_db(translations)

        return flask.jsonify({'search': 'shows', 'shows': list_to_json(db_shows)})


api.add_resource(SearchTextEP, '/0.1/search_text', endpoint='search_text')
api.add_resource(SearchIdEP, '/0.1/search_id', endpoint='search_id')


if __name__ == '__main__':
    app.run(debug=True, threaded=True)
