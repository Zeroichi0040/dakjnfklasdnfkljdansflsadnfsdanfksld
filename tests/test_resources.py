"""The same resource engine must enforce the same rules through forms and JSON."""

import csv
from dataclasses import replace
from io import StringIO

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from backend.common.errors import ValidationError
from backend.framework import services
from backend.framework.extension import framework
from database import db
from database.models import AuditEvent
from database.models.note import Note
from tests.conftest import api_request, login, post_form


def create_note(client, title="Private note", body="Saved content"):
    result = api_request(client, "POST", "/api/v1/notes", {"title": title, "body": body})
    assert result.status_code == 201, result.get_data(as_text=True)
    return result.json["data"]


def test_resource_crud_defaults_etag_and_version(client, users):
    login(client)
    record = create_note(client)
    assert record["version"] == 1 and record["created_at"].endswith("+00:00")
    assert "user_id" not in record
    assert client.get(f"/api/v1/notes/{record['id']}").headers["ETag"] == '"1"'
    result = api_request(client, "PATCH", f"/api/v1/notes/{record['id']}", {"version": 1, "body": "Changed"})
    assert result.status_code == 200 and result.json["data"]["version"] == 2
    assert (
        api_request(client, "PATCH", f"/api/v1/notes/{record['id']}", {"version": 1, "title": "Late edit"}).status_code
        == 409
    )
    assert api_request(client, "DELETE", f"/api/v1/notes/{record['id']}", {"version": 2}).status_code == 204
    assert client.get(f"/api/v1/notes/{record['id']}").status_code == 404
    assert client.get("/api/v1/notes").json["data"] == []


def test_owner_policy_applies_to_members_and_admins(app, client, users):
    login(client)
    record = create_note(client, "Owner-only data")
    for email in ["grace@example.com", "owner@example.com"]:
        other = app.test_client()
        login(other, email)
        assert other.get("/api/v1/notes").json["data"] == []
        assert other.get(f"/api/v1/notes/{record['id']}").status_code == 404
        assert other.get(f"/app/notes/{record['id']}").status_code == 404
        assert (
            api_request(other, "PATCH", f"/api/v1/notes/{record['id']}", {"version": 1, "title": "Stolen"}).status_code
            == 404
        )
        assert api_request(other, "DELETE", f"/api/v1/notes/{record['id']}", {"version": 1}).status_code == 404
        assert "Owner-only data" not in other.get("/app/notes/export.csv").get_data(as_text=True)


@pytest.mark.parametrize(
    "data",
    [
        {"title": ""},
        {"title": " "},
        {"title": 3},
        {"title": []},
        {"title": "x" * 121},
        {"body": "x" * 10001},
        {"user_id": 42},
        {"id": 1},
        {"role": "admin"},
        {"version": 9},
        {"created_at": "now"},
    ],
)
def test_validation_and_protected_fields(client, users, data):
    login(client)
    result = api_request(client, "POST", "/api/v1/notes", {"title": "Valid", **data})
    assert result.status_code == 422 and result.json["error"]["fields"]
    assert client.get("/api/v1/notes").json["pagination"]["total"] == 0


@pytest.mark.parametrize("version", [None, True, -1, "wrong", [], {}, 1.1])
def test_invalid_versions_are_validation_errors(client, users, version):
    login(client)
    record = create_note(client)
    assert (
        api_request(
            client, "PATCH", f"/api/v1/notes/{record['id']}", {"version": version, "title": "Changed"}
        ).status_code
        == 422
    )


def test_json_shape_pagination_sort_and_search(client, users):
    login(client)
    for value in [[], "text", 42]:
        assert api_request(client, "POST", "/api/v1/notes", value).status_code == 422
    for query in ["page=0", "page=abc", "per_page=10000", "per_page=0", "sort=user_id", "sort=unknown"]:
        assert client.get("/api/v1/notes?" + query).status_code == 422
    for title in ["100% real", "Alpha", "Zulu"]:
        create_note(client, title)
    result = client.get("/api/v1/notes?per_page=2&page=2").json
    assert len(result["data"]) == 1 and result["pagination"]["total"] == 3
    assert client.get("/api/v1/notes", query_string={"q": "%"}).json["data"][0]["title"] == "100% real"
    ordered = client.get("/api/v1/notes?sort=title").json["data"]
    assert [x["title"] for x in ordered] == ["100% real", "Alpha", "Zulu"]
    exported = list(csv.reader(StringIO(client.get("/app/notes/export.csv?q=Alpha").get_data(as_text=True))))
    assert len(exported) == 2 and exported[1][1] == "Alpha"


def test_generated_html_create_edit_detail_delete(client, users):
    login(client)
    result = post_form(client, "/app/notes/new", title="Browser note", body="Original")
    assert result.status_code == 303
    url = result.headers["Location"]
    assert b"Browser note" in client.get(url).data
    record = client.get("/api/v1/notes").json["data"][0]
    assert post_form(client, url + "/edit", title="Edited note", body="New content", version=1).status_code == 303
    assert client.get(f"/api/v1/notes/{record['id']}").json["data"]["body"] == "New content"
    assert post_form(client, url + "/delete", version=2).status_code == 303
    assert client.get(url).status_code == 404


def test_escaping_csv_and_atomic_audit(app, client, users):
    login(client)
    record = create_note(client, "<script>alert(1)</script>")
    html = client.get("/app/notes").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    create_note(client, "=1+1")
    rows = list(csv.reader(StringIO(client.get("/app/notes/export.csv").get_data(as_text=True))))
    assert any(row[1] == "'=1+1" for row in rows[1:])
    assert (
        api_request(client, "PATCH", f"/api/v1/notes/{record['id']}", {"version": 99, "title": "Wrong"}).status_code
        == 409
    )
    with app.app_context():
        assert (
            db.session.scalar(db.select(db.func.count(AuditEvent.id)).where(AuditEvent.action == "notes.updated")) == 0
        )


def test_hook_failure_rolls_back_record_and_audit(app, users):
    with app.app_context():
        from database.models import User

        actor = db.session.get(User, users["ada"])

        def reject(record, actor, creating):
            raise ValidationError({"title": ["A custom business rule rejected this value."]})

        resource = replace(framework().resources["notes"], on_save=reject)
        with pytest.raises(ValidationError):
            services.create(resource, actor, {"title": "Rejected"})
        assert db.session.scalar(db.select(db.func.count(Note.id))) == 0
        assert (
            db.session.scalar(db.select(db.func.count(AuditEvent.id)).where(AuditEvent.action == "notes.created")) == 0
        )


def test_persistence_across_factories_and_database_locking(app, client, users):
    login(client)
    record = create_note(client, "Persistent")
    from backend import create_app

    restarted = create_app(dict(app.config))
    other = restarted.test_client()
    login(other)
    assert other.get(f"/api/v1/notes/{record['id']}").json["data"]["title"] == "Persistent"
    with app.app_context():
        with Session(db.engine) as first, Session(db.engine) as second:
            a, b = first.get(Note, record["id"]), second.get(Note, record["id"])
            a.title = "First"
            first.commit()
            b.title = "Lost update"
            with pytest.raises(StaleDataError):
                second.commit()
            second.rollback()
    with restarted.app_context():
        db.session.remove()
        db.engine.dispose()
