"""Shared form fields. WTForms validates on the server; CSRF is enabled globally."""

from flask_wtf import FlaskForm
from wtforms import HiddenField, SubmitField
from wtforms.validators import DataRequired, Regexp


class ActionForm(FlaskForm):
    submit = SubmitField("Confirm")


class VersionForm(ActionForm):
    version = HiddenField(validators=[DataRequired(), Regexp(r"^[1-9][0-9]*$")])
