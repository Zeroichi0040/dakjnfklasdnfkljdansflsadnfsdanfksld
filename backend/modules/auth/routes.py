import hashlib

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_limiter.util import get_remote_address
from flask_login import current_user, login_required, logout_user

from backend.common.forms import ActionForm
from backend.common.security import safe_next
from backend.extensions import limiter
from backend.modules.auth import service
from backend.modules.auth.forms import ForgotForm, LoginForm, RegisterForm, ResetForm

bp = Blueprint("auth", __name__, url_prefix="/auth")


def login_limit_key():
    values = request.get_json(silent=True) if request.is_json else request.form
    email = str(values.get("email", "") if hasattr(values, "get") else "")[:254].strip().casefold()
    return get_remote_address() + ":" + hashlib.sha256(email.encode()).hexdigest()


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute;50 per hour", key_func=login_limit_key, methods=["POST"])
@limiter.limit("120 per minute", methods=["POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = service.authenticate(form.email.data, form.password.data)
        if user:
            service.start_session(user)
            return redirect(safe_next(request.args.get("next")) or url_for("dashboard.index"), code=303)
        form.password.errors.append("Email or password is incorrect.")
    return render_template("auth/login.html", form=form), 422 if request.method == "POST" else 200


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("30 per minute;120 per hour", methods=["POST"])
def register_page():
    if not current_app.config["SIGNUP_ENABLED"]:
        abort(403, description="New account registration is closed.")
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        from backend.common.errors import ValidationError  # noqa: PLC0415

        try:
            user = service.register_account(form.display_name.data, form.email.data, form.password.data)
        except ValidationError as error:
            form.email.errors.extend(error.errors.get("email", ["Please check your account details."]))
        else:
            service.start_session(user)
            flash("Your account is ready.", "success")
            return redirect(url_for("dashboard.index"), code=303)
    return render_template("auth/register.html", form=form), 422 if request.method == "POST" else 200


@bp.post("/logout")
@login_required
def logout_page():
    form = ActionForm()
    if not form.validate_on_submit():
        abort(400)
    logout_user()
    session.clear()
    return redirect(url_for("public.home"), code=303)


@bp.route("/forgot", methods=["GET", "POST"])
@limiter.limit("3 per hour", key_func=login_limit_key, methods=["POST"])
def forgot_password():
    if current_app.config["MAIL_TRANSPORT"] == "disabled":
        abort(
            503,
            description="Email resets are unavailable on this deployment. Ask the administrator to reset your password.",
        )
    form = ForgotForm()
    if form.validate_on_submit():
        try:
            service.request_reset(form.email.data)
        except (OSError, RuntimeError):
            current_app.logger.error("Password reset delivery failed; no tokens or email addresses logged.")
            abort(503, description="Email delivery is temporarily unavailable.")
        flash("If an active account matches that email, a reset message has been prepared.", "info")
        return redirect(url_for("auth.login_page"), code=303)
    return render_template("auth/forgot.html", form=form), 422 if request.method == "POST" else 200


@bp.route("/reset/<token>", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"])
def reset_password(token):
    if current_app.config["MAIL_TRANSPORT"] == "disabled":
        abort(503, description="Email password resets are disabled.")
    user = service.token_user(token)
    if not user:
        abort(400, description="This password reset link has expired or has already been used.")
    form = ResetForm()
    if form.validate_on_submit():
        service.change_password(user, form.password.data)
        logout_user()
        session.clear()
        flash("Password changed. Sign in with your new password.", "success")
        return redirect(url_for("auth.login_page"), code=303)
    return render_template("auth/reset.html", form=form), 422 if request.method == "POST" else 200
