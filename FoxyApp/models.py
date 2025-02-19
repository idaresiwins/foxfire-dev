from FoxyApp import db, login_manager, app
from flask_login import UserMixin
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    city = db.Column(db.String(300), nullable=False)
    state = db.Column(db.String(300), nullable=False)
    zipcode = db.Column(db.String(300), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    prepaid = db.Column(db.String(1), nullable=False, default='0')

    def get_reset_token(self):
        s = Serializer(app.secret_key)
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.secret_key)
        try:
            user_id = s.loads(token, max_age=86400)['user_id']
            print(user_id)
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.id}','{self.name}', '{self.address}', '{self.city}', '{self.state}', '{self.zipcode}', '{self.phone}', '{self.email}', '{self.password}')"


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    veg_name = db.Column(db.String(20), nullable=False)
    veg_price = db.Column(db.String(20), nullable=False)
    veg_image = db.Column(db.String(20), nullable=True, default="nia.png")
    veg_url = db.Column(db.String(20), nullable=True)
    veg_sale = db.Column(db.String(20), nullable=False)
    veg_weight = db.Column(db.Integer, nullable=False, default=0)
    veg_vol = db.Column(db.Float, nullable=False, default=0.0)

    def __repr__(self):
        return f"Product('{self.id}','{self.veg_name}', '{self.veg_price}', '{self.veg_image}',  '{self.veg_url}',  '{self.veg_sale}',  '{self.veg_weight}', '{self.veg_vol}')"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    visible = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"


class Picture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    thumbnail = db.Column(db.String(20), nullable=True, default="nia.png")
    image = db.Column(db.String(20), nullable=True, default="nia.png")

    def __repr__(self):
        return f"Picture('{self.id}','{self.name}', '{self.thumbnail}', '{self.image}')"


class Toggle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    set_toggle = db.Column(db.Integer)

    def __repr__(self):
        return f"Picture('{self.id}','{self.name}', '{self.set_toggle}')"


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    short_name = db.Column(db.String(200))
    long_name = db.Column(db.String(200))
    description = db.Column(db.String(200))
    active = db.Column(db.Boolean, default=False)
