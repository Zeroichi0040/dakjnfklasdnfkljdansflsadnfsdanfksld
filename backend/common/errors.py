"""BACKEND: HTML errors for pages and JSON errors for the API."""

from flask import Response, current_app, g, jsonify, make_response, render_template, request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from werkzeug.exceptions import HTTPException, SecurityError

from database import db


class ValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Please check the submitted values.")


def response_error(status, message, fields=None):
    if request.path.startswith("/api/"):
        return jsonify(
            error={
                "status": status,
                "message": message,
                "fields": fields or {},
                "request_id": getattr(g, "request_id", ""),
            }
        ), status
    return render_template("errors/error.html", status=status, message=message, fields=fields or {}), status


def install_errors(app):
    @app.errorhandler(ValidationError)
    def validation(error):
        db.session.rollback()
        return response_error(422, str(error), error.errors)

    @app.errorhandler(HTTPException)
    def http(error):
        db.session.rollback()
        if isinstance(error, SecurityError):
            # A rejected Host has no URL adapter; do not build template links.
            return "Bad request.", error.code, {"Content-Type": "text/plain; charset=utf-8"}
        response = make_response(response_error(error.code, error.description))
        for key, value in error.get_headers():
            if key.lower() not in {"content-type", "content-length"}:
                response.headers[key] = value
        return response

    @app.errorhandler(StaleDataError)
    def stale(error):
        db.session.rollback()
        return response_error(409, "This record changed in another request. Reload and try again.")

    @app.errorhandler(IntegrityError)
    def conflict(error):
        db.session.rollback()
        return response_error(409, "That value is already in use or the record changed. Reload and try again.")

    @app.errorhandler(Exception)
    def unexpected(error):
        db.session.rollback()
        current_app.logger.exception("Unhandled application error request_id=%s", getattr(g, "request_id", ""))
        message = "Something went wrong. Please try again or contact the administrator."
        if request.path.startswith("/api/"):
            return response_error(500, message)
        # Avoid user/template context processors: the database itself may be down.
        return Response(
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>Temporarily unavailable</title>"
            '<link rel="stylesheet" href="/static/css/tokens.css">'
            '<link rel="stylesheet" href="/static/css/app.css">'
            '<main class="main-content prose error-page"><h1>Please try again</h1>'
            f'<p>{message}</p><a href="/">Go home</a></main></html>',
            status=500,
            mimetype="text/html",
        )
