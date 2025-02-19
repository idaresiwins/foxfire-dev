from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from FoxyApp.models import User
from wtforms import StringField, PasswordField, SubmitField, BooleanField, EmailField, IntegerField, TextAreaField, RadioField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError


def no_http_characters(form, field):
    disallowed_characters = {'<', '>', '"', '&',"|", "\\", "!", "@", "#", "$", "%", "^", "*",
                             "_", "+", "=", "{", "}", "[", "]", ";", ",", "/",
                             ":", "?", "`", "~"}
    for char in disallowed_characters:
        if char in field.data:
            raise ValidationError(f"Input contains disallowed character: {char}, Please do not use \" < > & | \\ ! / @ # $ % ^ * _ + = {{ }} [ ] ; , : ? ` ~ ")


class RegistrationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=3, max=20), no_http_characters])
    email = EmailField("Email", validators=[DataRequired(), Email()])
    address = StringField("Address", validators=[DataRequired(), no_http_characters])
    city = StringField("City", validators=[DataRequired(), no_http_characters])
    state = StringField("State", validators=[DataRequired(), no_http_characters])
    zipcode = StringField("Zip Code", validators=[DataRequired(), no_http_characters])
    phone = StringField("Phone Number", validators=[DataRequired(), no_http_characters])
    route = RadioField('How did you hear about us?:', choices=[('In Person','We met in person.'),('Boyle Farmers Market','Boyle Farmers Market'),('Brochure','Brochure'),('other','other')], validators=[DataRequired()])
    prepaid = BooleanField("Prepaid")
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
    name = StringField("Name", validators=[Length(min=3, max=20), no_http_characters])
    email = EmailField("Email", validators=[Email()])
    address = StringField("Address", validators=[Length(min=3, max=200), no_http_characters])
    city = StringField("City", validators=[Length(min=1, max=20), no_http_characters])
    state = StringField("State", validators=[Length(min=2, max=20), no_http_characters])
    zipcode = StringField("Zip Code", validators=[Length(min=5, max=10), no_http_characters])
    phone = StringField("Phone Number", validators=[Length(min=7, max=20), no_http_characters])
    dlt = BooleanField("Delete account permanently?")
    submit = SubmitField("Update")

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')



class EditAccountForm(FlaskForm):
    name = StringField("Name", validators=[Length(min=3, max=20), no_http_characters])
    email = EmailField("Email", validators=[Email()])
    address = StringField("Address", validators=[Length(min=3, max=200), no_http_characters])
    city = StringField("City", validators=[Length(min=1, max=20), no_http_characters])
    state = StringField("State", validators=[Length(min=2, max=20), no_http_characters])
    zipcode = StringField("Zip Code", validators=[Length(min=5, max=10), no_http_characters])
    phone = StringField("Phone Number", validators=[Length(min=7, max=20), no_http_characters])
    dlt = BooleanField("Delete account permanently?")
    prepaid = BooleanField("Prepaid")
    submit = SubmitField("Update")


class NewProductForm(FlaskForm):
    veg_name = StringField("Product Name", validators=[DataRequired()])
    veg_price = StringField("Product Price", validators=[DataRequired()])
    veg_image = FileField("Product Image", validators=[FileAllowed(["jpg", "png"])])
    veg_url = StringField("Product URL")
    veg_weight = IntegerField("Weight (Whole numbers only.)")
    veg_vol = FloatField("Decimal part of a box (1.0 equals one full box)")
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


class LocationForm(FlaskForm):
    short_name = StringField('Short Name (This is what will show up on the label)', validators=[DataRequired()])
    long_name = StringField('Long Name (This is what the client will get)', validators=[DataRequired()])
    description = StringField('Description (This is what will show on the website)', validators=[DataRequired()])
    submit = SubmitField('Submit')
    active = BooleanField("Is this pickup site active?")


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
