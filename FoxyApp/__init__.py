from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

# Load .env file from the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(dotenv_path=os.path.join(parent_dir, ".env"), override=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("FOX_SECRET_KEY")
app.secret_key = app.config['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'noreply.pwresets.foxfire@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get("FOX_GMAIL_SECRET_KEY")
admins = ['foxfire.farm.ky@gmail.com', 'josh@dinky.pw']
api_key = os.environ.get("FOX_API_KEY")
mail = Mail(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

from FoxyApp import routes, models