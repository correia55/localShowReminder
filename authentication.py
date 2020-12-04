import datetime
from enum import Enum
from typing import Optional, Mapping

import jwt
import sqlalchemy.orm

import configuration
import db_calls


class TokenType(Enum):
    REFRESH = 0
    ACCESS = 1
    VERIFICATION = 2
    DELETION = 3
    CHANGE_EMAIL_OLD = 4
    CHANGE_EMAIL_NEW = 5
    PASSWORD_RECOVERY = 6


def generate_token(user_id: int, token_type: TokenType, session: sqlalchemy.orm.Session = None,
                   payload_extra: dict = None) -> Optional[bytes]:
    """
    Source: https://realpython.com/token-based-authentication-with-flask/
    Generate a token of the given type, for the specified user.

    :param user_id: the id of the user that owns the token.
    :param token_type: the type of the token.
    :param session: the db session, only needed when the TokenType is REFRESH.
    :param payload_extra: a dictionary with extra information that should be added to the payload of the token.
    :return: the generated token.
    """

    # Set the expiration date based on the type of token
    if token_type == TokenType.REFRESH:
        if not session:
            print('WARNING: Session is null!')
            return None

        exp = datetime.datetime.utcnow() + datetime.timedelta(days=configuration.REFRESH_TOKEN_VALIDITY_DAYS)
    elif token_type == TokenType.ACCESS:
        exp = datetime.datetime.utcnow() + datetime.timedelta(hours=configuration.ACCESS_TOKEN_VALIDITY_HOURS)
    elif token_type == TokenType.VERIFICATION:
        exp = datetime.datetime.utcnow() + datetime.timedelta(days=configuration.VERIFICATION_TOKEN_VALIDITY_DAYS)
    elif token_type == TokenType.DELETION:
        exp = datetime.datetime.utcnow() + datetime.timedelta(days=configuration.DELETION_TOKEN_VALIDITY_DAYS)
    elif token_type == TokenType.CHANGE_EMAIL_OLD:
        exp = datetime.datetime.utcnow() + datetime.timedelta(days=configuration.CHANGE_EMAIL_TOKEN_VALIDITY_DAYS)
    elif token_type == TokenType.CHANGE_EMAIL_NEW:
        exp = datetime.datetime.utcnow() + datetime.timedelta(days=configuration.CHANGE_EMAIL_TOKEN_VALIDITY_DAYS)
    elif token_type == TokenType.PASSWORD_RECOVERY:
        exp = datetime.datetime.utcnow() + datetime.timedelta(days=configuration.PASSWORD_RECOVERY_TOKEN_VALIDITY_DAYS)
    else:
        print('WARNING: Invalid token type!')
        return None

    try:
        payload = {
            'exp': exp,
            'iat': datetime.datetime.utcnow(),
            'user': user_id,
            'type': token_type.name
        }

        if payload_extra:
            payload.update(payload_extra)

        token = jwt.encode(payload, configuration.secret_key, algorithm='HS256')

        # If it's an authentication token, save it on the db
        if token_type == TokenType.REFRESH:
            db_token = db_calls.register_token(session, token)

            if db_token is None:
                print('WARNING: Token registration failed!')
                return None

        return token

    except Exception as e:
        print('WARNING: ' + str(e))
        return None


def generate_change_token(user_id: int, token_type: TokenType, change_dict: dict) \
        -> Optional[bytes]:
    """
    Source: https://realpython.com/token-based-authentication-with-flask/
    Generate a change token of the given type, for the specified user.

    :param user_id: the id of the user that owns the token.
    :param token_type: the type of the token.
    :param change_dict: the dictionary with all of the changes.
    :return: the generated token.
    """

    return generate_token(user_id, token_type, payload_extra=change_dict)


def generate_access_token(session: sqlalchemy.orm.Session, auth_token: bytearray) -> (bool, Optional[bytes]):
    """
    Generate an access token, when the authentication token is valid.

    :param session: the db session.
    :param auth_token: the authentication token.
    :return: whether the authentication token is valid or not (and the generated access token when valid or an error
    message otherwise).
    """

    valid, user_id = validate_token(session, auth_token, TokenType.REFRESH)

    if valid:
        return True, generate_token(user_id, TokenType.ACCESS, session=session)
    else:
        return False, None


def validate_token(session: sqlalchemy.orm.Session, auth_token: bytes, token_type: TokenType) -> (bool, str):
    """
    Source: https://realpython.com/token-based-authentication-with-flask/

    Decode and validate the token.

    :param session: the db session.
    :param auth_token: the authentication token.
    :param token_type: the type of the token.
    :return: whether or not the token is valid and a message or the user_id.
    """

    if not auth_token:
        return False, 'Invalid token. Please log in again.'

    try:
        payload = jwt.decode(auth_token, configuration.secret_key)

        # When the token is of the incorrect type
        if payload['type'] != token_type.name:
            return False, 'Invalid token. Please log in again.'
        else:
            # When it's an authentication token, it needs to be validated in the db
            if token_type == TokenType.REFRESH:
                token = db_calls.get_token(session, auth_token)

                if token is None:
                    return False, 'Invalid token. Please log in again.'

            return True, payload['user']
    except jwt.ExpiredSignatureError:
        return False, 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        return False, 'Invalid token. Please log in again.'


def get_token_payload(auth_token: bytes) -> Optional[Mapping]:
    """
    Get the payload of the token.

    :param auth_token: the token.
    :return: the value of that field or None.
    """

    # TODO: MAKE SURE THIS CANNOT BE CALLED FROM AN UNVALIDATED TOKEN

    try:
        payload = jwt.decode(auth_token, configuration.secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_field(auth_token: bytes, field: str) -> any:
    """
    Get the value of a field inside a token.

    :param auth_token: the token.
    :param field: the name of the field.
    :return: the value of that field or None.
    """

    # TODO: MAKE SURE THIS CANNOT BE CALLED FROM AN UNVALIDATED TOKEN

    payload = get_token_payload(auth_token)

    if payload is None:
        return None
    elif field in payload:
        return payload[field]
    else:
        return None
