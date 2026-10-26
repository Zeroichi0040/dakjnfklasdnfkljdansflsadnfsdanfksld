"""Server-rendered HTTP adapters; prices and state changes live in service.py."""

import uuid

import click
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, fresh_login_required, login_required
from sqlalchemy.exc import OperationalError

from backend.common.security import admin_required
from backend.modules.bakery import service
from database import db
from database.models.bakery import Category, Order, Product

bp = Blueprint("bakery", __name__)


@bp.app_template_filter("peso")
def peso(value):
    return f"₱{value:,.2f}"


@bp.app_context_processor
def bakery_values():
    cart = session.get("bakery_cart", {})
    return {
        "cart_count": sum(v for v in cart.values() if type(v) is int) if isinstance(cart, dict) else 0,
        "payment_methods": service.METHODS,
        "payment_scenarios": service.SCENARIOS,
        "order_transitions": service.TRANSITIONS,
    }


@bp.cli.command("seed")
def seed_command():
    """Add sample categories/products once; preserve existing inventory and accounts."""
    from backend.modules.bakery.seed import seed

    count = seed()
    click.echo(f"Bakery sample catalogue ready ({count} products added). No accounts created.")


def categories():
    return db.session.scalars(db.select(Category).order_by(Category.name)).all()


def fail(error):
    db.session.rollback()
    flash(
        str(error) if isinstance(error, service.BakeryError) else "The database is busy. Please reload and try again.",
        "error",
    )


@bp.get("/products")
def products():
    query = db.select(Product).where(Product.active.is_(True))
    search = request.args.get("q", "").strip()[:100]
    category = request.args.get("category", "")
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Product.name.ilike("%" + escaped + "%", escape="\\"))
    if category:
        query = query.join(Category).where(Category.slug == category)
    sort = request.args.get("sort", "name")
    ordering = {"name": Product.name.asc(), "price_asc": Product.price.asc(), "price_desc": Product.price.desc()}
    pagination = db.paginate(
        query.order_by(ordering.get(sort, Product.name.asc()), Product.id),
        page=max(1, request.args.get("page", 1, type=int)),
        per_page=12,
        error_out=False,
    )
    return render_template(
        "bakery/products.html",
        pagination=pagination,
        categories=categories(),
        q=search,
        selected_category=category,
        sort=sort,
    )


@bp.get("/products/<int:product_id>")
def product(product_id):
    record = db.first_or_404(db.select(Product).where(Product.id == product_id, Product.active.is_(True)))
    related = db.session.scalars(
        db.select(Product)
        .where(Product.category_id == record.category_id, Product.active.is_(True), Product.id != record.id)
        .order_by(Product.name)
        .limit(3)
    ).all()
    return render_template("bakery/product.html", product=record, related=related)


@bp.get("/cart")
def cart():
    try:
        rows, total = service.cart_summary(session.get("bakery_cart", {}))
    except service.BakeryError as error:
        fail(error)
        rows, total = [], 0
    return render_template("bakery/cart.html", rows=rows, total=total)


@bp.post("/cart/<int:product_id>")
def cart_change(product_id):
    try:
        raw = service.normalize_cart(session.get("bakery_cart", {}))
        action = request.form.get("action", "add")
        key = str(product_id)
        if action == "remove":
            raw.pop(key, None)
        else:
            if action not in {"add", "update"}:
                raise service.BakeryError("Unknown cart action.")
            record = db.get_or_404(Product, product_id)
            quantity = service.integer(request.form.get("quantity"))
            quantity = quantity + raw.get(key, 0) if action == "add" else quantity
            if quantity > 99 or not record.active or quantity > record.stock:
                raise service.BakeryError("Requested quantity exceeds available stock or the 99-item limit.")
            raw[key] = quantity
            service.normalize_cart(raw)
        session["bakery_cart"] = raw
        session.pop("bakery_checkout_token", None)
        flash("Cart updated.", "success")
    except service.BakeryError as error:
        fail(error)
    return redirect(url_for("bakery.cart"), code=303)


@bp.post("/cart/clear")
def cart_clear():
    session.pop("bakery_cart", None)
    session.pop("bakery_checkout_token", None)
    flash("Cart cleared.", "success")
    return redirect(url_for("bakery.cart"), code=303)


@bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    if request.method == "POST":
        token = request.form.get("checkout_token", "")
        # Already-created receipts may be retrieved on a retry, but only by their owner.
        existing = db.session.scalar(
            db.select(Order).where(Order.user_id == current_user.id, Order.checkout_token == token)
        )
        if existing:
            return redirect(url_for("bakery.order", order_id=existing.id), code=303)
        if token != session.get("bakery_checkout_token") or not token:
            abort(409, description="Checkout changed or expired. Reload the checkout page.")
        try:
            record = service.checkout(current_user.id, session.get("bakery_cart", {}), request.form, token)
        except (service.BakeryError, OperationalError) as error:
            fail(error)
        else:
            session.pop("bakery_cart", None)
            session.pop("bakery_checkout_token", None)
            flash("Order recorded. This is a payment demonstration; no money moved.", "success")
            return redirect(url_for("bakery.order", order_id=record.id), code=303)
    try:
        rows, total = service.cart_summary(session.get("bakery_cart", {}))
    except service.BakeryError as error:
        fail(error)
        return redirect(url_for("bakery.cart"), code=303)
    if not rows:
        flash("Add a product before checking out.", "info")
        return redirect(url_for("bakery.products"), code=303)
    token = session.setdefault("bakery_checkout_token", str(uuid.uuid4()))
    return render_template(
        "bakery/checkout.html", rows=rows, total=total, token=token, values=request.form
    ), 422 if request.method == "POST" else 200


@bp.get("/orders")
@login_required
def orders():
    pagination = db.paginate(
        db.select(Order).where(Order.user_id == current_user.id).order_by(Order.id.desc()),
        page=max(1, request.args.get("page", 1, type=int)),
        per_page=20,
        error_out=False,
    )
    return render_template("bakery/orders.html", pagination=pagination, administration=False)


def owned_order(identifier):
    query = db.select(Order).where(Order.id == identifier)
    if not current_user.is_admin:
        query = query.where(Order.user_id == current_user.id)
    return db.first_or_404(query)


@bp.get("/orders/<int:order_id>")
@login_required
def order(order_id):
    return render_template("bakery/order.html", order=owned_order(order_id))


@bp.post("/orders/<int:order_id>/cancel")
@login_required
def cancel(order_id):
    record = owned_order(order_id)
    if record.user_id != current_user.id:
        abort(403)
    try:
        service.transition(current_user.id, order_id, "cancelled", request.form.get("version"), customer=True)
        flash("Order cancelled. Stock restored; any paid simulation is marked refunded.", "success")
    except (service.BakeryError, OperationalError) as error:
        fail(error)
    return redirect(url_for("bakery.order", order_id=order_id), code=303)


@bp.get("/admin/bakery")
@fresh_login_required
@admin_required
def admin_dashboard():
    return render_template("bakery/admin.html", stats=service.financial_summary())


@bp.get("/admin/bakery/orders")
@fresh_login_required
@admin_required
def admin_orders():
    query = db.select(Order)
    status = request.args.get("status", "")
    if status in service.TRANSITIONS:
        query = query.where(Order.status == status)
    pagination = db.paginate(
        query.order_by(Order.id.desc()),
        page=max(1, request.args.get("page", 1, type=int)),
        per_page=30,
        error_out=False,
    )
    return render_template("bakery/orders.html", pagination=pagination, administration=True, selected_status=status)


@bp.post("/admin/bakery/orders/<int:order_id>")
@fresh_login_required
@admin_required
def admin_order_update(order_id):
    db.get_or_404(Order, order_id)
    try:
        if request.form.get("action") == "collect":
            service.collect_cash(current_user.id, order_id, request.form.get("version"))
        else:
            service.transition(current_user.id, order_id, request.form.get("status"), request.form.get("version"))
        flash("Order updated.", "success")
    except (service.BakeryError, OperationalError) as error:
        fail(error)
    return redirect(url_for("bakery.order", order_id=order_id), code=303)


@bp.get("/admin/bakery/products")
@fresh_login_required
@admin_required
def inventory():
    pagination = db.paginate(
        db.select(Product).order_by(Product.name),
        page=max(1, request.args.get("page", 1, type=int)),
        per_page=30,
        error_out=False,
    )
    return render_template("bakery/inventory.html", pagination=pagination)


@bp.route("/admin/bakery/products/new", methods=["GET", "POST"])
@bp.route("/admin/bakery/products/<int:product_id>", methods=["GET", "POST"])
@fresh_login_required
@admin_required
def edit_product(product_id=None):
    record = db.get_or_404(Product, product_id) if product_id else None
    if request.method == "POST":
        try:
            service.save_product(current_user.id, request.form, product_id)
        except (service.BakeryError, OperationalError) as error:
            fail(error)
        else:
            flash("Product saved.", "success")
            return redirect(url_for("bakery.inventory"), code=303)
    values = (
        request.form
        if request.method == "POST"
        else ({c.name: getattr(record, c.name) for c in Product.__table__.columns} if record else {})
    )
    return render_template(
        "bakery/product_form.html", product=record, values=values, categories=categories(), images=service.IMAGES
    ), 422 if request.method == "POST" else 200
