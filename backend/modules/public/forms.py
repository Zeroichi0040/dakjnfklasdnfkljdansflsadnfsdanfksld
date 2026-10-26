from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, ValidationError


def empty_honeypot(form, field):
    if field.data:
        raise ValidationError("Please leave this field empty.")


class ContactForm(FlaskForm):
    name = StringField("Your name", validators=[DataRequired(), Length(max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(check_deliverability=False), Length(max=254)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(min=10, max=3000)])
    website = StringField("Leave empty", validators=[empty_honeypot])
    submit = SubmitField("Send message")
