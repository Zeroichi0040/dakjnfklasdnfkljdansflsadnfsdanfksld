from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length


class ProfileForm(FlaskForm):
    display_name = StringField("Your name", validators=[DataRequired(), Length(min=1, max=80)])
    submit = SubmitField("Save profile")


class PasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired(), Length(max=128)])
    password = PasswordField("New password", validators=[DataRequired(), Length(min=12, max=128)])
    confirm = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Change password")
