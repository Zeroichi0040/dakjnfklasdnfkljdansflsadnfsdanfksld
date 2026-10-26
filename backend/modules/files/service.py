from io import BytesIO

from flask import current_app
from PIL import Image, UnidentifiedImageError
from sqlalchemy import update
from werkzeug.exceptions import Conflict, NotFound
from werkzeug.utils import secure_filename

from backend.common.errors import ValidationError
from database import db
from database.models import Attachment, AuditEvent, User


def store_image(user_id, uploaded):
    if not uploaded or not uploaded.filename:
        raise ValidationError({"file": ["Choose a PNG, JPEG, or WebP image."]})
    raw = uploaded.read(current_app.config["MAX_IMAGE_BYTES"] + 1)
    if not raw or len(raw) > current_app.config["MAX_IMAGE_BYTES"]:
        raise ValidationError({"file": ["Images must be smaller than 2 MiB."]})
    try:
        with Image.open(BytesIO(raw)) as image:
            fmt = image.format
            if (
                fmt not in {"PNG", "JPEG", "WEBP"}
                or image.width * image.height > 16_000_000
                or getattr(image, "n_frames", 1) != 1
            ):
                raise ValueError
            image.verify()
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
        raise ValidationError(
            {"file": ["Use a valid, non-animated PNG, JPEG, or WebP image up to 16 megapixels."]}
        ) from None
    changed = db.session.execute(
        update(User)
        .where(
            User.id == user_id,
            User.active.is_(True),
            User.storage_bytes + len(raw) <= current_app.config["USER_FILE_QUOTA"],
        )
        .values(storage_bytes=User.storage_bytes + len(raw))
    )
    if changed.rowcount != 1:
        raise ValidationError({"file": ["Your storage quota is full. Delete an image before adding another."]})
    extension, mime = {"PNG": ("png", "image/png"), "JPEG": ("jpg", "image/jpeg"), "WEBP": ("webp", "image/webp")}[fmt]
    stem = secure_filename(uploaded.filename).rsplit(".", 1)[0][:90] or "image"
    attachment = Attachment(user_id=user_id, filename=f"{stem}.{extension}", content_type=mime, size=len(raw), data=raw)
    db.session.add(attachment)
    db.session.add(AuditEvent(user_id=user_id, action="file.uploaded", subject=attachment.filename))
    db.session.commit()
    return attachment


def owned_attachment(user_id, identifier):
    attachment = db.session.scalar(
        db.select(Attachment).where(Attachment.id == identifier, Attachment.user_id == user_id)
    )
    if not attachment:
        raise NotFound("That image is not available to your account.")
    return attachment


def remove_image(user_id, identifier):
    attachment = owned_attachment(user_id, identifier)
    result = db.session.execute(
        update(User)
        .where(User.id == user_id, User.storage_bytes >= attachment.size)
        .values(storage_bytes=User.storage_bytes - attachment.size)
    )
    if result.rowcount != 1:
        raise Conflict("The file list changed. Reload and try again.")
    db.session.add(AuditEvent(user_id=user_id, action="file.deleted", subject=attachment.filename))
    db.session.delete(attachment)
    db.session.commit()
