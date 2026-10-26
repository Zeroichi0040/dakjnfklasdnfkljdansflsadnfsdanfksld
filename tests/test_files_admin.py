from io import BytesIO

from PIL import Image

from database import db
from database.models import Attachment, Inquiry, User
from tests.conftest import csrf, login, post_form


def image_bytes():
    stream = BytesIO()
    Image.new("RGB", (4, 4), "#173d35").save(stream, format="PNG")
    return stream.getvalue()


def upload(client, raw=None, filename="my-image.png"):
    return client.post(
        "/files",
        data={"csrf_token": csrf(client), "file": (BytesIO(raw if raw is not None else image_bytes()), filename)},
        content_type="multipart/form-data",
    )


def test_private_image_upload_download_delete_and_quota(app, client, users):
    login(client)
    raw = image_bytes()
    assert upload(client, raw, "../../private.png").status_code == 303
    with app.app_context():
        attachment = db.session.scalar(db.select(Attachment))
        identifier = attachment.id
        assert attachment.filename == "private.png" and attachment.data == raw
        assert db.session.get(User, users["ada"]).storage_bytes == len(raw)
    assert client.get("/files").status_code == 200
    downloaded = client.get(f"/files/{identifier}/download")
    assert downloaded.data == raw and "attachment" in downloaded.headers["Content-Disposition"]
    assert downloaded.headers["Cache-Control"] == "no-store"
    second = app.test_client()
    login(second, "grace@example.com")
    assert second.get(f"/files/{identifier}/download").status_code == 404
    assert post_form(second, f"/files/{identifier}/delete").status_code == 404
    assert app.test_client().get(f"/files/{identifier}/download").status_code == 302
    assert post_form(client, f"/files/{identifier}/delete").status_code == 303
    assert client.get(f"/files/{identifier}/download").status_code == 404
    with app.app_context():
        assert db.session.get(User, users["ada"]).storage_bytes == 0


def test_image_verification_size_and_quota_fail_atomically(app, client, users):
    login(client)
    assert upload(client, b"<svg onload='alert(1)'></svg>", "fake.png").status_code == 422
    app.config["MAX_IMAGE_BYTES"] = 20
    assert upload(client).status_code == 422
    app.config["MAX_IMAGE_BYTES"] = 2 * 1024 * 1024
    app.config["USER_FILE_QUOTA"] = len(image_bytes()) - 1
    assert upload(client).status_code == 422
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(Attachment.id))) == 0
        assert db.session.get(User, users["ada"]).storage_bytes == 0


def test_large_pixel_and_animated_images_are_rejected(client, users):
    login(client)
    large = BytesIO()
    Image.new("1", (4001, 4000)).save(large, format="PNG")
    assert upload(client, large.getvalue(), "large.png").status_code == 422
    animated = BytesIO()
    Image.new("RGB", (2, 2), "red").save(
        animated, format="PNG", save_all=True, append_images=[Image.new("RGB", (2, 2), "blue")], duration=100, loop=0
    )
    assert upload(client, animated.getvalue(), "animated.png").status_code == 422


def test_member_is_denied_all_admin_pages(client, users):
    login(client)
    for path in ("/admin", "/admin/users", "/admin/inquiries", "/admin/audit", f"/admin/users/{users['grace']}"):
        assert client.get(path).status_code == 403
    assert post_form(client, f"/admin/users/{users['grace']}", role="admin", active="y").status_code == 403


def test_admin_role_changes_revoke_sessions_and_protect_self(app, client, users):
    second = app.test_client()
    login(second, "grace@example.com")
    login(client, "owner@example.com")
    assert client.get("/admin").status_code == 200
    assert client.get("/admin/users").status_code == 200
    assert post_form(client, f"/admin/users/{users['admin']}", role="member").status_code == 409
    assert post_form(client, f"/admin/users/{users['grace']}", role="admin", active="y").status_code == 303
    assert second.get("/api/v1/me").status_code == 401
    login(second, "grace@example.com")
    assert second.get("/admin").status_code == 200
    assert post_form(client, f"/admin/users/{users['grace']}", role="member").status_code == 303
    assert second.get("/api/v1/me").status_code == 401
    with app.app_context():
        target = db.session.get(User, users["grace"])
        assert target.active is False and target.role == "member"


def test_contact_form_honeypot_and_admin_resolution(app, client, users):
    values = {"name": "Visitor", "email": "visitor@example.com", "message": "Please tell me more about this project."}
    assert post_form(client, "/contact", **values, website="spam.example").status_code == 422
    assert post_form(client, "/contact", **values).status_code == 303
    with app.app_context():
        inquiry = db.session.scalar(db.select(Inquiry))
        identifier = inquiry.id
        assert not inquiry.resolved
    login(client, "owner@example.com")
    assert b"Please tell me more" in client.get("/admin/inquiries").data
    assert post_form(client, f"/admin/inquiries/{identifier}/resolve").status_code == 303
    with app.app_context():
        assert db.session.get(Inquiry, identifier).resolved
