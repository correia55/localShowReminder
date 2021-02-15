from enum import Enum
from typing import Optional

from google.auth.transport import requests
from google.oauth2 import id_token

import configuration


class UserSource(Enum):
    GOOGLE = 0


def external_authentication(token: str, source: str) -> Optional[str]:
    """
    Validate the token and get the user's email.

    :param token: the token from an external source.
    :param source: the name of the source.
    :return: the email of the user, when successful.
    """

    # Get the email from the token
    if source == UserSource.GOOGLE.name:
        return google_authentication(token)
    else:
        return None


def google_authentication(token: str) -> Optional[str]:
    """
    Validate the id token and get the user's email.

    :param token: the id token from Google.
    :return: the email of the user, when successful.
    """

    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), configuration.google_client_id)

        return idinfo['email']
    except ValueError:
        # Invalid token
        return None
