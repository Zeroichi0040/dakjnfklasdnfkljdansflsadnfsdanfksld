"""Generate real HTML and JSON CRUD endpoints from a Resource definition."""

import csv
from io import StringIO

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, stream_with_context, url_for
from flask_login import current_user, login_required

from backend.common.errors import ValidationError
from backend.common.forms import ActionForm, VersionForm
from backend.extensions import limiter
from backend.framework import services
from backend.framework.forms import form_class
from database import db


def pagination_values():
    try:
        page = int(request.args.get("page", "1"))
        size = int(request.args.get("per_page", "20"))
    except ValueError:
        raise ValidationError({"pagination": ["Use integer page and per_page values."]}) from None
    if page < 1 or not 1 <= size <= 50:
        raise ValidationError({"pagination": ["page must be positive; per_page must be 1-50."]})
    return page, size


def json_payload():
    value = request.get_json()
    if not isinstance(value, dict):
        raise ValidationError({"body": ["Send a JSON object."]})
    return value


def build_html(resource):
    bp = Blueprint(resource.key, __name__, url_prefix=f"/app/{resource.key}")
    ResourceForm = form_class(resource)

    @bp.get("")
    @login_required
    def index():
        page, size = pagination_values()
        q, sort = request.args.get("q", "").strip()[:120], request.args.get("sort", "-id")
        records = db.paginate(
            services.query(resource, current_user, q, sort), page=page, per_page=size, error_out=False
        )
        return render_template(resource.list_template, resource=resource, pagination=records, q=q, sort=sort)

    def edit_form(record=None):
        resource.policy.authorize(current_user, "update" if record else "create")
        form = ResourceForm(obj=record)
        if form.validate_on_submit():
            values = {field.name: getattr(form, field.name).data for field in resource.fields}
            try:
                if record:
                    values["version"] = form.version.data
                    saved = services.update(resource, current_user, record.id, values)
                else:
                    saved = services.create(resource, current_user, values)
            except ValidationError as error:
                for name, messages in error.errors.items():
                    if hasattr(form, name):
                        getattr(form, name).errors.extend(messages)
            else:
                flash(f"{resource.singular} saved.", "success")
                return redirect(url_for(resource.key + ".detail", identifier=saved.id), code=303)
        return render_template(
            "framework/resource_form.html", resource=resource, form=form, record=record
        ), 422 if request.method == "POST" else 200

    @bp.route("/new", methods=["GET", "POST"])
    @login_required
    @limiter.limit("60 per minute", methods=["POST"])
    def create_page():
        return edit_form()

    @bp.get("/<int:identifier>")
    @login_required
    def detail(identifier):
        record = services.get_record(resource, current_user, identifier)
        return render_template(
            "framework/resource_detail.html", resource=resource, record=record, action_form=ActionForm()
        )

    @bp.route("/<int:identifier>/edit", methods=["GET", "POST"])
    @login_required
    @limiter.limit("60 per minute", methods=["POST"])
    def edit_page(identifier):
        return edit_form(services.get_record(resource, current_user, identifier))

    @bp.post("/<int:identifier>/delete")
    @login_required
    def delete_page(identifier):
        form = VersionForm()
        if not form.validate_on_submit():
            raise ValidationError(form.errors)
        services.delete(resource, current_user, identifier, form.version.data)
        flash(f"{resource.singular} deleted.", "success")
        return redirect(url_for(resource.key + ".index"), code=303)

    @bp.get("/export.csv")
    @login_required
    @limiter.limit("10 per hour")
    def export():
        statement = services.query(
            resource, current_user, request.args.get("q", "").strip()[:120], request.args.get("sort", "-id")
        ).limit(5000)
        names = ["id", *(f.name for f in resource.fields), "created_at", "updated_at", "version"]

        def rows():
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(names)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            for record in db.session.scalars(statement.execution_options(yield_per=100)):
                values = [services.encode(getattr(record, name)) for name in names]
                writer.writerow(
                    [
                        "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v
                        for v in values
                    ]
                )
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

        response = Response(stream_with_context(rows()), content_type="text/csv; charset=utf-8")
        response.headers["Content-Disposition"] = f'attachment; filename="{resource.key}.csv"'
        response.headers["X-Export-Limit"] = "5000"
        return response

    return bp


def build_api(resource):
    bp = Blueprint(resource.key + "_api", __name__, url_prefix=f"/api/v1/{resource.key}")

    @bp.get("")
    @login_required
    def index():
        page, size = pagination_values()
        records = db.paginate(
            services.query(
                resource, current_user, request.args.get("q", "").strip()[:120], request.args.get("sort", "-id")
            ),
            page=page,
            per_page=size,
            error_out=False,
        )
        return jsonify(
            data=[services.serialize(resource, r) for r in records.items],
            pagination={"page": page, "per_page": size, "total": records.total, "pages": records.pages},
        )

    @bp.post("")
    @login_required
    @limiter.limit("60 per minute")
    def create():
        saved = services.create(resource, current_user, json_payload())
        response = jsonify(data=services.serialize(resource, saved))
        response.status_code = 201
        response.headers["Location"] = url_for(resource.key + "_api.detail", identifier=saved.id)
        return response

    @bp.get("/<int:identifier>")
    @login_required
    def detail(identifier):
        record = services.get_record(resource, current_user, identifier)
        response = jsonify(data=services.serialize(resource, record))
        response.set_etag(str(record.version))
        return response

    @bp.patch("/<int:identifier>")
    @login_required
    @limiter.limit("60 per minute")
    def update(identifier):
        record = services.update(resource, current_user, identifier, json_payload())
        return jsonify(data=services.serialize(resource, record))

    @bp.delete("/<int:identifier>")
    @login_required
    @limiter.limit("60 per minute")
    def delete(identifier):
        data = json_payload()
        if set(data) != {"version"}:
            raise ValidationError({"body": ["Send only the current version."]})
        services.delete(resource, current_user, identifier, data["version"])
        return "", 204

    return bp
