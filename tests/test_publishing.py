from tests.conftest import api_request, login, post_form


def test_cms_requires_admin_and_private_drafts_stay_private(app, client, users):
    login(client)
    assert client.get("/app/pages").status_code == 403
    assert (
        api_request(
            client, "POST", "/api/v1/pages", {"title": "Spam", "slug": "spam", "body": "Bad", "published": True}
        ).status_code
        == 403
    )
    admin = app.test_client()
    login(admin, "owner@example.com")
    result = api_request(
        admin,
        "POST",
        "/api/v1/pages",
        {"title": "Company story", "slug": "our-story", "body": "Content from the database.", "published": False},
    )
    assert result.status_code == 201
    record = result.json["data"]
    assert app.test_client().get("/pages/our-story").status_code == 404
    assert b"Company story" not in app.test_client().get("/").data
    assert client.get(f"/api/v1/pages/{record['id']}").status_code == 403
    assert (
        api_request(admin, "PATCH", f"/api/v1/pages/{record['id']}", {"version": 1, "published": True}).status_code
        == 200
    )
    visitor = app.test_client()
    assert b"Content from the database." in visitor.get("/pages/our-story").data
    assert b"Company story" in visitor.get("/").data
    assert (
        api_request(admin, "PATCH", f"/api/v1/pages/{record['id']}", {"version": 2, "published": False}).status_code
        == 200
    )
    assert visitor.get("/pages/our-story").status_code == 404


def test_publish_form_and_slug_constraints(app, client, users):
    login(client, "owner@example.com")
    assert (
        post_form(
            client,
            "/app/pages/new",
            title="Welcome",
            slug="welcome",
            body="Published by an administrator.",
            published="y",
        ).status_code
        == 303
    )
    assert app.test_client().get("/pages/welcome").status_code == 200
    for slug in ["welcome", "BAD SPACE", "../secret"]:
        result = api_request(
            client, "POST", "/api/v1/pages", {"title": "Another", "slug": slug, "body": "Text", "published": True}
        )
        assert result.status_code in (409, 422)
    assert (
        api_request(
            client,
            "POST",
            "/api/v1/pages",
            {"title": "Another", "slug": "another", "body": "Text", "published": "true"},
        ).status_code
        == 422
    )


def test_resource_discovery_and_navigation_obey_policy(app, client, users):
    login(client)
    keys = [x["key"] for x in client.get("/api/v1/resources").json["data"]]
    assert keys == ["notes"]
    assert b"Website pages" not in client.get("/app").data
    admin = app.test_client()
    login(admin, "owner@example.com")
    assert "pages" in [x["key"] for x in admin.get("/api/v1/resources").json["data"]]
    assert b"Website pages" in admin.get("/app").data
    spec = client.get("/api/openapi.json").json
    assert "patch" in spec["paths"]["/api/v1/notes/{record_id}"]
    assert spec["components"]["schemas"]["pagesCreate"]["properties"]["published"]["type"] == "boolean"
