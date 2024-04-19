from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from FoxyApp.models import User, Product
from wtforms import StringField, PasswordField, SubmitField, BooleanField, EmailField, FloatField, TextAreaField, RadioField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError


class RegistrationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=3, max=20)])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    address = StringField("Address", validators=[DataRequired()])
    city = StringField("City", validators=[DataRequired()])
    state = StringField("State", validators=[DataRequired()])
    zipcode = StringField("Zip Code", validators=[DataRequired()])
    phone = StringField("Phone Number", validators=[DataRequired()])
    route = RadioField('How did you hear about us?:', choices=[('In Person','We met in person.'),('Boyle Farmers Market','Boyle Farmers Market'),('Brochure','Brochure'),('other','other')], validators=[DataRequired()])
    #password = PasswordField("Password", validators=[DataRequired(), Length(min=10, max=128)])
    #confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField("Sign Up")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    remember = BooleanField("Remember me")
    login = SubmitField("Login")


class AccountForm(FlaskForm):
    name = StringField("Name", validators=[Length(min=3, max=20)])
    email = EmailField("Email", validators=[Email()])
    address = StringField("Address", validators=[Length(min=3, max=200)])
    city = StringField("City", validators=[Length(min=1, max=20)])
    state = StringField("State", validators=[Length(min=2, max=20)])
    zipcode = StringField("Zip Code", validators=[Length(min=5, max=10)])
    phone = StringField("Phone Number", validators=[Length(min=7, max=20)])
    dlt = BooleanField("Delete account permanently?")
    submit = SubmitField("Update")

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')

class EditAccountForm(FlaskForm):
    name = StringField("Name", validators=[Length(min=3, max=20)])
    email = EmailField("Email", validators=[Email()])
    address = StringField("Address", validators=[Length(min=3, max=200)])
    city = StringField("City", validators=[Length(min=1, max=20)])
    state = StringField("State", validators=[Length(min=2, max=20)])
    zipcode = StringField("Zip Code", validators=[Length(min=5, max=10)])
    phone = StringField("Phone Number", validators=[Length(min=7, max=20)])
    dlt = BooleanField("Delete account permanently?")
    submit = SubmitField("Update")

class NewProductForm(FlaskForm):
    veg_name = StringField("Product Name", validators=[DataRequired()])
    veg_price = StringField("Product Price", validators=[DataRequired()])
    veg_image = FileField("Product Image", validators=[FileAllowed(["jpg", "png"])])
    veg_url = StringField("Product URL")
    veg_sale = BooleanField("Post for sale immediately?")
    veg_dlt = BooleanField("Delete product permanently?")
    submit = SubmitField("Post!")

class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. You must register first.')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Post')
    visible = BooleanField("Make post visible in Blog?")
    dlt = BooleanField("Delete post permanently?")

class NewPictureForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    image = FileField("Image", validators=[FileAllowed(["jpg", "png"])])
    submit = SubmitField("Upload")


class ToggleForm(FlaskForm):
    set_toggle = BooleanField("Toggle Ordering")
    submit = SubmitField('Toggle')

class CycleForm(FlaskForm):
    set_toggle = BooleanField("Cycle Google Sheets?")
    submit = SubmitField('Cycle')