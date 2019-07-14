from enum import Enum

import jwt
import datetime

import models
import configuration


class TokenType(Enum):
    AUTHENTICATION = 0
    ACCESS = 1


def generate_access_token(auth_token: bytearray):
    """
    Generate an access token, when the authentication token is valid.

    :param auth_token: the authentication token.
    :return: whether the authentication token is valid or not (and the generated access token when valid or an error
    message otherwise).
    """

    valid, msg = validate_token(auth_token, TokenType.AUTHENTICATION)

    if valid:
        return True, generate_token(msg, TokenType.ACCESS)
    else:
        return False, 'Invalid token. Please log in again.'


def generate_token(user_id: int, token_type: TokenType) -> any:
    """
    Source: https://realpython.com/token-based-authentication-with-flask/
    Generate a token of the given type, for the specified user.

    :param user_id: the id of the user that owns the token.
    :param token_type: the type of the token.
    :return: the generated token.
    """

    try:
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1, seconds=5),
            'iat': datetime.datetime.utcnow(),
            'user': user_id,
            'type': token_type.name
        }

        token = jwt.encode(payload, configuration.secret_key, algorithm='HS256')

        # If it's an authentication token, save it on the db
        if token_type == TokenType.AUTHENTICATION:
            configuration.session.add(models.Token(token.decode()))
            configuration.session.commit()

        return token

    except Exception as e:
        print(e)
        return e


def validate_token(auth_token: bytearray, token_type: TokenType):
    """
    Source: https://realpython.com/token-based-authentication-with-flask/

    Decode and validate the token.

    :param auth_token: the authentication token.
    :param token_type: the type of the token.
    :return: whether or not the token is valid and a message or the user_id.
    """

    try:
        payload = jwt.decode(auth_token, configuration.secret_key)

        # When the token is of the incorrect type
        if payload['type'] != token_type.name:
            return False, 'Invalid token. Please log in again.'
        else:
            # When it's an authentication token, it needs to be validated in the db
            if token_type == TokenType.AUTHENTICATION:
                token = configuration.session.query(models.Token).filter(
                    models.Token.token == auth_token.decode()).first()

                if token is None:
                    return False, 'Invalid token. Please log in again.'

            return True, payload['user']
    except jwt.ExpiredSignatureError:
        return False, 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        return False, 'Invalid token. Please log in again.'
