from FoxyApp import app
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer


def get_account_token(name, password, address, city, state, zipcode, phone, email):
    s = Serializer(app.secret_key)
    token = s.dumps({'name': name, 'password': password, 'address': address, 'city': city, 'state': state, 'zipcode': zipcode, 'phone': phone, 'email': email})
    return token


def approve_account_token(token):
    s = Serializer(app.secret_key)
    try:
        user_id = s.loads(token)
    except:
        return None
    return user_id