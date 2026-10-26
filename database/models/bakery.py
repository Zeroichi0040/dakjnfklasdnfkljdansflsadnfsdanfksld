"""Bakery relational model. Money is Decimal-backed; receipts retain purchase snapshots."""

from database import db
from database.models.user import utcnow


class Category(db.Model):
    __tablename__ = "bakery_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    slug = db.Column(db.String(60), unique=True, nullable=False)


class Product(db.Model):
    __tablename__ = "bakery_products"
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("bakery_categories.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    image = db.Column(db.String(30), nullable=False, default="bread")
    version = db.Column(db.Integer, nullable=False, default=1)
    category = db.relationship(Category)
    __table_args__ = (
        db.CheckConstraint("price > 0 AND price <= 999999.99", name="bakery_product_price"),
        db.CheckConstraint("stock >= 0", name="bakery_product_stock"),
    )


class Order(db.Model):
    __tablename__ = "bakery_orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    checkout_token = db.Column(db.String(36), nullable=False)
    customer_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(24), nullable=False)
    pickup_note = db.Column(db.String(300), nullable=False, default="")
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    total = db.Column(db.Numeric(14, 2), nullable=False)
    stock_restored = db.Column(db.Boolean, nullable=False, default=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    items = db.relationship("OrderItem", cascade="all, delete-orphan", lazy="selectin")
    payment = db.relationship("Payment", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    customer = db.relationship("User")
    __table_args__ = (
        db.UniqueConstraint("user_id", "checkout_token", name="bakery_checkout_once"),
        db.CheckConstraint("total > 0", name="bakery_order_total"),
        db.CheckConstraint(
            "status IN ('pending','preparing','ready','completed','cancelled')", name="bakery_order_status"
        ),
    )


class OrderItem(db.Model):
    __tablename__ = "bakery_order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("bakery_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("bakery_products.id"), nullable=False, index=True)
    product_name = db.Column(db.String(120), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    __table_args__ = (
        db.CheckConstraint("quantity > 0 AND quantity <= 99", name="bakery_item_quantity"),
        db.CheckConstraint("unit_price > 0", name="bakery_item_price"),
        db.UniqueConstraint("order_id", "product_id", name="bakery_item_product_once"),
    )

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class Payment(db.Model):
    __tablename__ = "bakery_payments"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("bakery_orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    scenario = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    __table_args__ = (
        db.CheckConstraint("method IN ('gcash','card','cash')", name="bakery_payment_method"),
        db.CheckConstraint("status IN ('paid','unpaid','failed','cancelled','refunded')", name="bakery_payment_status"),
        db.CheckConstraint(
            "scenario IN ('success','declined','insufficient','cancelled')", name="bakery_payment_scenario"
        ),
        db.CheckConstraint("amount > 0", name="bakery_payment_amount"),
    )
