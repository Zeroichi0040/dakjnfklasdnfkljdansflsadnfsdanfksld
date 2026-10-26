from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from backend.framework.extension import framework
from database import db
from database.models import Attachment
from database.models.bakery import Order
from database.repositories import events_query

bp = Blueprint("dashboard", __name__)


@bp.get("/app")
@login_required
def index():
    cards = []
    for resource in framework().resources.values():
        if resource.policy.allows(current_user):
            statement = resource.policy.query(resource.model, current_user).subquery()
            cards.append(
                {"resource": resource, "total": db.session.scalar(db.select(func.count()).select_from(statement))}
            )
    file_count = db.session.scalar(db.select(func.count(Attachment.id)).where(Attachment.user_id == current_user.id))
    recent = db.session.scalars(events_query(current_user.id).limit(8)).all()
    orders = db.session.scalars(db.select(Order).where(Order.user_id == current_user.id)
        .order_by(Order.id.desc()).limit(5)).all()
    return render_template("dashboard/index.html", cards=cards, file_count=file_count, recent=recent, orders=orders)


@bp.get("/app/activity")
@login_required
def activity():
    pagination = db.paginate(
        events_query(current_user.id), page=max(1, request.args.get("page", 1, type=int)), per_page=25, error_out=False
    )
    return render_template("dashboard/activity.html", pagination=pagination)
