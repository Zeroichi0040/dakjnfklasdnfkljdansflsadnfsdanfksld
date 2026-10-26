"""Bakery business rules. Every write is committed atomically or rolled back."""

import re
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, update
from sqlalchemy.exc import OperationalError

from database import db
from database.models import AuditEvent, SiteState, User
from database.models.bakery import Category, Order, OrderItem, Payment, Product

METHODS = {"gcash": "GCash · simulation", "card": "Debit / credit card · simulation", "cash": "Cash on pickup"}
SCENARIOS = {
    "success": "Successful payment",
    "declined": "Declined",
    "insufficient": "Insufficient balance",
    "cancelled": "Cancelled",
}
TRANSITIONS = {
    "pending": {"preparing", "cancelled"},
    "preparing": {"ready", "cancelled"},
    "ready": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}
IMAGES = ("bread", "pastry", "cake", "cookie", "bun")


class BakeryError(ValueError):
    """A safe, user-facing domain validation failure."""


def integer(value, label="Quantity", maximum=99):
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]{1,9}", str(value)):
        raise BakeryError(f"{label} must be a whole number.")
    result = int(value)
    if not 1 <= result <= maximum:
        raise BakeryError(f"{label} must be between 1 and {maximum}.")
    return result


def lock_writes(actor=None, admin=False):
    # A real UPDATE serializes on SQLite as well as PostgreSQL. Read current state after this lock.
    if (
        db.session.execute(update(SiteState).where(SiteState.id == 1).values(revision=SiteState.revision + 1)).rowcount
        != 1
    ):
        raise BakeryError("Database is not ready. Apply migrations.")
    if actor is not None:
        person = db.session.get(User, actor, populate_existing=True)
        if not person or not person.active or (admin and not person.is_admin):
            raise BakeryError("Your account is no longer authorized. Please sign in again.")


def normalize_cart(raw):
    if not isinstance(raw, dict) or len(raw) > 20:
        raise BakeryError("A cart may contain at most 20 different products.")
    return {str(integer(k, "Product", 2147483647)): integer(v) for k, v in raw.items()}


def cart_summary(raw, strict=False):
    cart = normalize_cart(raw)
    rows, total = [], Decimal("0.00")
    for key, quantity in cart.items():
        product = db.session.get(Product, int(key), populate_existing=True)
        if not product:
            raise BakeryError("A product in your cart no longer exists. Clear the cart and try again.")
        available = product.active and product.stock >= quantity
        if strict and not available:
            raise BakeryError(f"{product.name} is unavailable in that quantity. Update your cart.")
        subtotal = product.price * quantity
        rows.append({"product": product, "quantity": quantity, "subtotal": subtotal, "available": available})
        total += subtotal
    return rows, total


def audit(actor, action, subject):
    db.session.add(AuditEvent(user_id=actor, action="bakery." + action, subject=subject[:160]))


def restore_stock(order):
    if order.stock_restored:
        return
    for item in order.items:
        db.session.execute(
            update(Product)
            .where(Product.id == item.product_id)
            .values(stock=Product.stock + item.quantity, version=Product.version + 1)
        )
    order.stock_restored = True


def checkout(actor, raw_cart, details, token):
    """Reserve stock, snapshot prices, simulate payment, and commit one transaction."""
    try:
        lock_writes(actor)
        existing = db.session.scalar(db.select(Order).where(Order.user_id == actor, Order.checkout_token == token))
        if existing:
            db.session.rollback()
            return existing
        if not re.fullmatch(r"[a-f0-9-]{36}", str(token)):
            raise BakeryError("Checkout expired. Reload the checkout page.")
        rows, total = cart_summary(raw_cart, strict=True)
        if not rows:
            raise BakeryError("Add at least one product before checking out.")
        name = str(details.get("customer_name", "")).strip()
        phone = str(details.get("phone", "")).strip()
        note = str(details.get("pickup_note", "")).strip()
        if not 1 <= len(name) <= 80 or not re.fullmatch(r"[+0-9 ()-]{7,24}", phone) or len(note) > 300:
            raise BakeryError(
                "Enter a name (1–80 characters), phone (7–24 characters), and a note of at most 300 characters."
            )
        method, scenario = details.get("method"), details.get("scenario")
        if method not in METHODS or scenario not in SCENARIOS:
            raise BakeryError("Choose a valid payment method and demonstration scenario.")
        if method == "cash" and scenario != "success":
            raise BakeryError("Cash on pickup uses the successful reservation scenario; payment remains unpaid.")
        order = Order(
            user_id=actor,
            checkout_token=token,
            customer_name=name,
            phone=phone,
            pickup_note=note,
            total=total,
            status="pending",
        )
        db.session.add(order)
        for row in rows:
            product, quantity = row["product"], row["quantity"]
            reserved = db.session.execute(
                update(Product)
                .where(
                    Product.id == product.id,
                    Product.active.is_(True),
                    Product.stock >= quantity,
                    Product.version == product.version,
                )
                .values(stock=Product.stock - quantity, version=Product.version + 1),
                execution_options={"synchronize_session": False},
            )
            if reserved.rowcount != 1:
                raise BakeryError("Inventory changed during checkout. Please try again.")
            order.items.append(
                OrderItem(product_id=product.id, product_name=product.name, unit_price=product.price, quantity=quantity)
            )
        status = (
            "unpaid"
            if method == "cash"
            else "paid"
            if scenario == "success"
            else ("cancelled" if scenario == "cancelled" else "failed")
        )
        order.payment = Payment(method=method, scenario=scenario, status=status, amount=total)
        if status in {"failed", "cancelled"}:
            order.status = "cancelled"
            restore_stock(order)
        audit(actor, "checkout", f"Order created; payment {status}")
        db.session.commit()
        return order
    except (BakeryError, OperationalError) as error:
        db.session.rollback()
        if isinstance(error, OperationalError):
            raise BakeryError(
                "The database is busy. Retry checkout; your confirmation token prevents duplicates."
            ) from error
        raise
    except Exception:
        db.session.rollback()
        raise


def transition(actor, identifier, target, version, customer=False):
    try:
        lock_writes(actor, admin=not customer)
        order = db.session.get(Order, identifier, populate_existing=True)
        if not order or (customer and order.user_id != actor):
            raise BakeryError("Order not found.")
        if order.version != integer(version, "Version", 2147483647):
            raise BakeryError("This order changed. Reload before trying again.")
        if customer and (target != "cancelled" or order.status != "pending"):
            raise BakeryError("Customers may cancel only pending orders.")
        if target not in TRANSITIONS[order.status]:
            raise BakeryError("That order status transition is not allowed.")
        if target == "completed" and order.payment.status != "paid":
            raise BakeryError("Record the simulated cash collection before completing this order.")
        if target == "cancelled":
            restore_stock(order)
            order.payment.status = "refunded" if order.payment.status == "paid" else "cancelled"
        order.status, order.version = target, order.version + 1
        audit(actor, "status", f"Order {identifier}: {target}")
        db.session.commit()
        return order
    except Exception:
        db.session.rollback()
        raise


def collect_cash(actor, identifier, version):
    try:
        lock_writes(actor, admin=True)
        order = db.session.get(Order, identifier, populate_existing=True)
        if not order or order.version != integer(version, "Version", 2147483647):
            raise BakeryError("Order changed or was not found. Reload the page.")
        if order.status != "ready" or order.payment.method != "cash" or order.payment.status != "unpaid":
            raise BakeryError("Only ready, unpaid cash-on-pickup orders can be collected.")
        order.payment.status = "paid"
        order.version += 1
        audit(actor, "cash_collected", f"Order {identifier}: simulated cash collection")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def save_product(actor, values, identifier=None):
    try:
        lock_writes(actor, admin=True)
        product = db.session.get(Product, identifier, populate_existing=True) if identifier else Product()
        if not product:
            raise BakeryError("Product not found.")
        if identifier and product.version != integer(values.get("version"), "Version", 2147483647):
            raise BakeryError("Inventory changed. Reload before saving.")
        name, description = str(values.get("name", "")).strip(), str(values.get("description", "")).strip()
        if not 1 <= len(name) <= 120 or not 1 <= len(description) <= 3000:
            raise BakeryError("Provide a name (1–120 characters) and description (1–3000 characters).")
        try:
            price = Decimal(str(values.get("price", "")))
            if (
                not price.is_finite()
                or not Decimal("0") < price <= Decimal("999999.99")
                or price != price.quantize(Decimal(".01"))
            ):
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            raise BakeryError("Price must be ₱0.01–₱999,999.99 with at most two decimal places.") from None
        stock_value = str(values.get("stock", ""))
        if not re.fullmatch(r"[0-9]{1,7}", stock_value) or int(stock_value) > 1000000:
            raise BakeryError("Stock must be a whole number from 0 to 1,000,000.")
        category = db.session.get(Category, integer(values.get("category_id"), "Category", 2147483647))
        image = values.get("image")
        if not category or image not in IMAGES:
            raise BakeryError("Choose an existing category and local product illustration.")
        product.name, product.description, product.price = name, description, price
        product.stock, product.category_id, product.image = int(stock_value), category.id, image
        product.active = values.get("active") in {"1", "on", True}
        product.version = product.version + 1 if identifier else 1
        db.session.add(product)
        audit(actor, "product_saved", name)
        db.session.commit()
        return product
    except Exception:
        db.session.rollback()
        raise


def financial_summary():
    # Revenue means completed AND paid. Unpaid cash and cancelled/refunded orders are excluded.
    qualifying = (Order.status == "completed", Payment.status == "paid")
    count, revenue = db.session.execute(
        db.select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0)).join(Payment).where(*qualifying)
    ).one()
    revenue = Decimal(revenue)
    unpaid = db.session.scalar(
        db.select(func.coalesce(func.sum(Order.total), 0))
        .join(Payment)
        .where(Payment.status == "unpaid", Order.status != "cancelled")
    )
    paid_open = db.session.scalar(
        db.select(func.coalesce(func.sum(Order.total), 0))
        .join(Payment)
        .where(Payment.status == "paid", Order.status.in_(["pending", "preparing", "ready"]))
    )
    best = db.session.execute(
        db.select(
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("units"),
            func.sum(OrderItem.unit_price * OrderItem.quantity).label("sales"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .join(Payment, Payment.order_id == Order.id)
        .where(*qualifying)
        .group_by(OrderItem.product_id, OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(8)
    ).all()
    daily = db.session.execute(
        db.select(func.date(Order.created_at).label("day"), func.sum(Order.total).label("sales"))
        .join(Payment)
        .where(*qualifying)
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at).desc())
        .limit(14)
    ).all()
    return {
        "count": count,
        "revenue": revenue,
        "average": revenue / count if count else Decimal("0"),
        "unpaid": unpaid,
        "paid_open": paid_open,
        "best": best,
        "daily": list(reversed(daily)),
    }
