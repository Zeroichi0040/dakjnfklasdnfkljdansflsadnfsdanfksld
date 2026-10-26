from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(check_deliverability=False), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])
    submit = SubmitField("Sign in")


class RegisterForm(FlaskForm):
    display_name = StringField("Your name", validators=[DataRequired(), Length(min=1, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(check_deliverability=False), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=12, max=128)])
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Create account")


class ForgotForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(check_deliverability=False), Length(max=254)])
    submit = SubmitField("Request password reset")


class ResetForm(FlaskForm):
    password = PasswordField("New password", validators=[DataRequired(), Length(min=12, max=128)])
    confirm = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Set new password")
