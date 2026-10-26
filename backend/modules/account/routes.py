from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, fresh_login_required

from backend.modules.account.forms import PasswordForm, ProfileForm
from backend.modules.auth.service import change_password, start_session
from database import db
from database.models import AuditEvent

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.route("/profile", methods=["GET", "POST"])
@fresh_login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.display_name = form.display_name.data.strip()
        db.session.add(AuditEvent(user_id=current_user.id, action="account.profile_updated", subject="Profile updated"))
        db.session.commit()
        flash("Profile saved.", "success")
        return redirect(url_for("account.profile"), code=303)
    return render_template("account/profile.html", form=form), 422 if request.method == "POST" else 200


@bp.route("/password", methods=["GET", "POST"])
@fresh_login_required
def password():
    form = PasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            form.current_password.errors.append("Current password is incorrect.")
        else:
            change_password(current_user, form.password.data)
            start_session(current_user)
            flash("Password changed. Other sessions were signed out.", "success")
            return redirect(url_for("account.profile"), code=303)
    return render_template("account/password.html", form=form), 422 if request.method == "POST" else 200
