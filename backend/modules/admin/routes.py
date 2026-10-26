from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, fresh_login_required
from flask_wtf import FlaskForm
from sqlalchemy import func, update
from wtforms import BooleanField, SelectField, SubmitField
from wtforms.fields import SelectChoice
from wtforms.validators import DataRequired

from backend.common.forms import ActionForm
from backend.common.security import admin_required
from database import db
from database.models import Attachment, AuditEvent, Inquiry, SiteState, User
from database.models.page import Page

bp = Blueprint("admin", __name__, url_prefix="/admin")


class RoleForm(FlaskForm):
    role = SelectField(
        "Role",
        choices=[SelectChoice("member", "Member"), SelectChoice("admin", "Administrator")],
        validators=[DataRequired()],
    )
    active = BooleanField("Account is active")
    submit = SubmitField("Save account")


@bp.get("")
@fresh_login_required
@admin_required
def index():
    counts = {
        "users": db.session.scalar(db.select(func.count(User.id))),
        "pages": db.session.scalar(db.select(func.count(Page.id))),
        "inquiries": db.session.scalar(db.select(func.count(Inquiry.id)).where(Inquiry.resolved.is_(False))),
        "file_bytes": db.session.scalar(db.select(func.coalesce(func.sum(Attachment.size), 0))),
    }
    return render_template("admin/index.html", counts=counts)


@bp.get("/users")
@fresh_login_required
@admin_required
def users():
    pagination = db.paginate(
        db.select(User).order_by(User.id.desc()),
        page=max(1, request.args.get("page", 1, type=int)),
        per_page=20,
        error_out=False,
    )
    return render_template("admin/users.html", pagination=pagination)


@bp.route("/users/<int:user_id>", methods=["GET", "POST"])
@fresh_login_required
@admin_required
def edit_user(user_id):
    target = db.get_or_404(User, user_id)
    form = RoleForm(role=target.role, active=target.active) if request.method == "GET" else RoleForm()
    if form.validate_on_submit():
        if target.id == current_user.id:
            abort(409, description="Ask another administrator to change your own role or account status.")
        # A real database write lock serializes role changes, including on SQLite.
        # Refresh the actor after locking so a concurrent deactivation cannot act.
        locked = db.session.execute(update(SiteState).where(SiteState.id == 1).values(revision=SiteState.revision + 1))
        if locked.rowcount != 1:
            abort(503, description="Run database migrations before managing users.")
        db.session.refresh(current_user._get_current_object())
        if not current_user.is_admin:
            abort(403)
        db.session.refresh(target)
        target.role, target.active = form.role.data, form.active.data
        target.session_version += 1
        db.session.add(
            AuditEvent(
                user_id=current_user.id,
                action="admin.account_changed",
                subject=f"Account {target.id}: role or status changed",
            )
        )
        db.session.commit()
        flash("Account updated. Previous sessions for that user were revoked.", "success")
        return redirect(url_for("admin.users"), code=303)
    return render_template("admin/user_form.html", form=form, target=target), 422 if request.method == "POST" else 200


@bp.get("/inquiries")
@fresh_login_required
@admin_required
def inquiries():
    pagination = db.paginate(
        db.select(Inquiry).order_by(Inquiry.id.desc()),
        page=max(1, request.args.get("page", 1, type=int)),
        per_page=20,
        error_out=False,
    )
    return render_template("admin/inquiries.html", pagination=pagination, form=ActionForm())


@bp.post("/inquiries/<int:inquiry_id>/resolve")
@fresh_login_required
@admin_required
def resolve_inquiry(inquiry_id):
    if not ActionForm().validate_on_submit():
        abort(400)
    inquiry = db.get_or_404(Inquiry, inquiry_id)
    inquiry.resolved = True
    db.session.add(
        AuditEvent(user_id=current_user.id, action="admin.inquiry_resolved", subject=f"Inquiry {inquiry.id}")
    )
    db.session.commit()
    flash("Message marked as resolved.", "success")
    return redirect(url_for("admin.inquiries"), code=303)


@bp.get("/audit")
@fresh_login_required
@admin_required
def audit():
    pagination = db.paginate(
        db.select(AuditEvent).order_by(AuditEvent.id.desc()),
        page=max(1, request.args.get("page", 1, type=int)),
        per_page=30,
        error_out=False,
    )
    return render_template("dashboard/activity.html", pagination=pagination, admin_audit=True)
