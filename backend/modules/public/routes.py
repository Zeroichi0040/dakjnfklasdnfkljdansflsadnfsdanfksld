from flask import Blueprint, flash, redirect, render_template, request, url_for

from backend.extensions import limiter
from backend.modules.public.forms import ContactForm
from database import db
from database.models import Inquiry
from database.models.bakery import Category, Product
from database.models.page import Page

bp = Blueprint("public", __name__)


@bp.get("/")
def home():
    pages = db.session.scalars(
        db.select(Page).where(Page.published.is_(True)).order_by(Page.updated_at.desc()).limit(12)
    ).all()
    featured = db.session.scalars(db.select(Product).where(Product.active.is_(True), Product.stock > 0)
        .order_by(Product.id).limit(4)).all()
    categories = db.session.scalars(db.select(Category).order_by(Category.name)).all()
    return render_template("public/home.html", pages=pages, featured=featured, categories=categories)


@bp.get("/pages/<slug>")
def page(slug):
    record = db.first_or_404(db.select(Page).where(Page.slug == slug, Page.published.is_(True)))
    return render_template("public/page.html", page=record)


@bp.route("/contact", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        db.session.add(
            Inquiry(
                name=form.name.data.strip(), email=form.email.data.strip().casefold(), message=form.message.data.strip()
            )
        )
        db.session.commit()
        flash("Your message was received.", "success")
        return redirect(url_for("public.contact"), code=303)
    return render_template("public/contact.html", form=form), 422 if request.method == "POST" else 200


@bp.get("/privacy")
def privacy():
    return render_template("public/privacy.html")
