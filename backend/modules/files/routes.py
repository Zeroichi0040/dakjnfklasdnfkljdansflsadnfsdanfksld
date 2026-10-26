from io import BytesIO

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from sqlalchemy.orm import defer
from wtforms import SubmitField

from backend.common.forms import ActionForm
from backend.extensions import limiter
from backend.modules.files.service import owned_attachment, remove_image, store_image
from database import db
from database.models import Attachment

bp = Blueprint("files", __name__, url_prefix="/files")


class UploadForm(FlaskForm):
    file = FileField("Image", validators=[FileRequired()])
    submit = SubmitField("Upload image")


@bp.route("", methods=["GET", "POST"])
@login_required
@limiter.limit("20 per hour", methods=["POST"])
def index():
    form = UploadForm()
    if form.validate_on_submit():
        store_image(current_user.id, form.file.data)
        flash("Image uploaded. Only your account can download it.", "success")
        return redirect(url_for("files.index"), code=303)
    statement = (
        db.select(Attachment)
        .options(defer(Attachment.data))
        .where(Attachment.user_id == current_user.id)
        .order_by(Attachment.created_at.desc())
    )
    pagination = db.paginate(
        statement, page=max(1, request.args.get("page", 1, type=int)), per_page=20, error_out=False
    )
    return render_template(
        "files/index.html", form=form, action_form=ActionForm(), pagination=pagination
    ), 422 if request.method == "POST" else 200


@bp.get("/<uuid:identifier>/download")
@login_required
def download(identifier):
    attachment = owned_attachment(current_user.id, str(identifier))
    response = send_file(
        BytesIO(attachment.data),
        mimetype=attachment.content_type,
        as_attachment=True,
        download_name=attachment.filename,
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.post("/<uuid:identifier>/delete")
@login_required
def delete(identifier):
    if not ActionForm().validate_on_submit():
        abort(400)
    remove_image(current_user.id, str(identifier))
    flash("Image deleted.", "success")
    return redirect(url_for("files.index"), code=303)
