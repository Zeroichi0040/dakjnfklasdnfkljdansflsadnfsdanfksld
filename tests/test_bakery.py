"""Behaviour tests across the real Flask routes and transactional bakery services."""

import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from flask_migrate import check, downgrade, upgrade
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from backend.config import ROOT
from backend.modules.bakery import service
from backend.modules.bakery.seed import seed
from database import db
from database.models.bakery import Category, Order, OrderItem, Product
from tests.conftest import csrf, login


@pytest.fixture
def catalogue(app):
    with app.app_context():
        category = Category(name="Bread", slug="bread")
        db.session.add(category)
        db.session.flush()
        products = [
            Product(
                category_id=category.id,
                name="Pandesal",
                description="Soft Filipino rolls. Contains wheat.",
                price=Decimal("48.25"),
                stock=10,
                image="bread",
            ),
            Product(
                category_id=category.id,
                name="Sold Out",
                description="Back soon",
                price=Decimal("15.50"),
                stock=0,
                image="cookie",
            ),
        ]
        db.session.add_all(products)
        db.session.commit()
        return {"product": products[0].id, "sold_out": products[1].id, "category": category.id}


def details(**changes):
    return {
        "customer_name": "Ada",
        "phone": "09123456789",
        "pickup_note": "Afternoon pickup",
        "method": "gcash",
        "scenario": "success",
        **changes,
    }


def place(actor, product, quantity=2, **changes):
    return service.checkout(actor, {str(product): quantity}, details(**changes), str(uuid.uuid4()))


def post(client, path, values=None, **kwargs):
    return client.post(path, data={"csrf_token": csrf(client), **(values or {})}, **kwargs)


def browser_checkout(client, product, **changes):
    post(client, f"/cart/{product}", {"quantity": "2"})
    response = client.get("/checkout")
    assert response.status_code == 200
    token = re.search(r'name="checkout_token" value="([^"]+)"', response.text).group(1)
    return post(client, "/checkout", {"checkout_token": token, **details(**changes)})


def test_seed_is_repeatable_and_preserves_inventory(app):
    with app.app_context():
        assert seed() == 12
        item = db.session.scalar(db.select(Product).order_by(Product.id))
        item.stock = 3
        db.session.commit()
        assert seed() == 0
        assert db.session.get(Product, item.id).stock == 3
        assert db.session.scalar(db.select(func.count(Product.id))) == 12
        assert db.session.scalar(db.select(func.count(Category.id))) == 5


def test_catalogue_filters_detail_and_local_assets(client, catalogue):
    assert b"Pandesal" in client.get("/products").data
    assert b"Pandesal" not in client.get("/products?q=Missing").data
    assert b"Pandesal" in client.get("/products?category=bread&sort=price_desc").data
    assert b"Pandesal" not in client.get("/products?category=invalid").data
    assert b"Pandesal" not in client.get("/products?q=%25").data  # literal percent, not a wildcard
    assert client.get(f"/products/{catalogue['product']}").status_code == 200
    assert client.get("/products/99999").status_code == 404
    for image in (*service.IMAGES, "hero"):
        assert client.get(f"/static/images/bakery/{image}.svg").status_code == 200


def test_cart_add_update_remove_totals_and_csrf(client, catalogue):
    product = catalogue["product"]
    assert client.post(f"/cart/{product}", data={"quantity": 1}).status_code == 400
    post(client, f"/cart/{product}", {"quantity": "2"})
    assert "₱96.50" in client.get("/cart").text
    post(client, f"/cart/{product}", {"quantity": "3", "action": "update"})
    assert "₱144.75" in client.get("/cart").text
    post(client, f"/cart/{product}", {"action": "remove"})
    assert "Your basket is waiting" in client.get("/cart").text


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "NaN", "100", "", "99999999999999999999999"])
def test_cart_rejects_invalid_quantity(client, catalogue, value):
    post(client, f"/cart/{catalogue['product']}", {"quantity": value})
    with client.session_transaction() as session:
        assert not session.get("bakery_cart")


def test_cart_stock_limit_and_anonymous_login_preservation(client, users, catalogue):
    post(client, f"/cart/{catalogue['product']}", {"quantity": 10})
    post(client, f"/cart/{catalogue['product']}", {"quantity": 1})
    post(client, f"/cart/{catalogue['sold_out']}", {"quantity": 1})
    login(client)
    with client.session_transaction() as session:
        assert session["bakery_cart"] == {str(catalogue["product"]): 10}
    assert client.get("/checkout").status_code == 200


def test_registration_preserves_anonymous_basket(client, catalogue):
    post(client, f"/cart/{catalogue['product']}", {"quantity": 1})
    response = post(
        client,
        "/auth/register",
        {
            "display_name": "New Baker",
            "email": "new@example.com",
            "password": "A-long-test-password-42",
            "confirm": "A-long-test-password-42",
        },
    )
    # Existing form validation and authentication are also covered in test_auth.py.
    assert response.status_code == 303, response.text
    with client.session_transaction() as session:
        assert session["bakery_cart"] == {str(catalogue["product"]): 1}
    assert client.get("/checkout").status_code == 200


def test_successful_checkout_server_prices_snapshots_and_replay(app, client, users, catalogue):
    login(client)
    response = browser_checkout(client, catalogue["product"], total="0.01", price="0.01", user_id=users["grace"])
    assert response.status_code == 303
    receipt = client.get(response.location)
    assert receipt.status_code == 200 and "₱96.50" in receipt.text and "Payment: Paid" in receipt.text
    with app.app_context():
        order = db.session.scalar(db.select(Order))
        assert order.user_id == users["ada"] and order.total == Decimal("96.50")
        token, identifier = order.checkout_token, order.id
        product = db.session.get(Product, catalogue["product"])
        assert product.stock == 8
        product.price, product.name = Decimal("99.00"), "New name"
        db.session.commit()
        assert db.session.get(Order, identifier).items[0].unit_price == Decimal("48.25")
    replay = post(client, "/checkout", {"checkout_token": token, **details()})
    assert replay.status_code == 303 and replay.location.endswith(f"/orders/{identifier}")
    with app.app_context():
        assert db.session.scalar(db.select(func.count(Order.id))) == 1
        assert db.session.get(Product, catalogue["product"]).stock == 8


@pytest.mark.parametrize(
    ("method", "scenario", "payment"),
    [
        ("gcash", "success", "paid"),
        ("card", "success", "paid"),
        ("cash", "success", "unpaid"),
        ("card", "declined", "failed"),
        ("gcash", "insufficient", "failed"),
        ("gcash", "cancelled", "cancelled"),
    ],
)
def test_payment_scenarios(app, users, catalogue, method, scenario, payment):
    with app.app_context():
        order = place(users["ada"], catalogue["product"], method=method, scenario=scenario)
        assert order.payment.status == payment
        cancelled = payment in {"failed", "cancelled"}
        assert order.status == ("cancelled" if cancelled else "pending")
        assert bool(order.stock_restored) == cancelled
        assert db.session.get(Product, catalogue["product"]).stock == (10 if cancelled else 8)
        assert service.financial_summary()["revenue"] == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"method": "evil"},
        {"scenario": "evil"},
        {"method": "cash", "scenario": "declined"},
        {"customer_name": ""},
        {"phone": "abc"},
        {"pickup_note": "x" * 301},
    ],
)
def test_invalid_checkout_rolls_back(app, users, catalogue, changes):
    with app.app_context():
        with pytest.raises(service.BakeryError):
            place(users["ada"], catalogue["product"], **changes)
        assert db.session.get(Product, catalogue["product"]).stock == 10
        assert db.session.scalar(db.select(func.count(Order.id))) == 0


def test_stock_revalidation_empty_cart_deactivation_and_atomicity(app, users, catalogue):
    with app.app_context():
        for cart in (
            {},
            {str(catalogue["product"]): 11},
            {str(catalogue["product"]): 1, str(catalogue["sold_out"]): 1},
        ):
            with pytest.raises(service.BakeryError):
                service.checkout(users["ada"], cart, details(), str(uuid.uuid4()))
        item = db.session.get(Product, catalogue["product"])
        item.active = False
        db.session.commit()
        with pytest.raises(service.BakeryError):
            place(users["ada"], item.id)
        assert db.session.get(Product, item.id).stock == 10
        assert db.session.scalar(db.select(func.count(OrderItem.id))) == 0


def test_customer_cancel_restores_once_and_refunds(app, client, users, catalogue):
    login(client)
    response = browser_checkout(client, catalogue["product"])
    identifier = int(response.location.rsplit("/", 1)[1])
    assert post(client, f"/orders/{identifier}/cancel", {"version": 1}).status_code == 303
    post(client, f"/orders/{identifier}/cancel", {"version": 2})
    with app.app_context():
        order = db.session.get(Order, identifier)
        assert order.status == "cancelled" and order.payment.status == "refunded"
        assert db.session.get(Product, catalogue["product"]).stock == 10


def test_order_permissions_and_administration(app, client, users, catalogue):
    assert client.get("/orders").status_code == 302
    assert client.get("/admin/bakery").status_code == 302
    login(client, email="grace@example.com")
    for path in ["/admin/bakery", "/admin/bakery/orders", "/admin/bakery/products", "/admin/bakery/products/new"]:
        assert client.get(path).status_code == 403
    assert post(client, "/admin/bakery/products/new", {}).status_code == 403
    with app.app_context():
        identifier = place(users["ada"], catalogue["product"]).id
    assert client.get(f"/orders/{identifier}").status_code == 404
    assert post(client, f"/orders/{identifier}/cancel", {"version": 1}).status_code == 404
    assert b"MTH-" not in client.get("/orders").data
    login(client, email="owner@example.com")
    assert client.get(f"/orders/{identifier}").status_code == 200
    assert client.get("/admin/bakery/orders?status=pending").status_code == 200
    assert client.get("/admin/bakery").status_code == 200


def test_valid_transitions_cash_collection_and_financials(app, users, catalogue):
    with app.app_context():
        order = place(users["ada"], catalogue["product"], method="cash")
        identifier = order.id
        with pytest.raises(service.BakeryError):
            service.transition(users["admin"], identifier, "completed", 1)
        with pytest.raises(service.BakeryError):
            service.collect_cash(users["admin"], identifier, 1)
        service.transition(users["admin"], identifier, "preparing", 1)
        with pytest.raises(service.BakeryError):
            service.transition(users["ada"], identifier, "cancelled", 2, customer=True)
        service.transition(users["admin"], identifier, "ready", 2)
        with pytest.raises(service.BakeryError):
            service.transition(users["admin"], identifier, "completed", 3)
        stats = service.financial_summary()
        assert stats["unpaid"] == Decimal("96.50") and stats["revenue"] == 0
        service.collect_cash(users["admin"], identifier, 3)
        with pytest.raises(service.BakeryError):
            service.collect_cash(users["admin"], identifier, 4)
        service.transition(users["admin"], identifier, "completed", 4)
        place(users["ada"], catalogue["product"], quantity=1, scenario="declined")
        place(users["ada"], catalogue["product"], quantity=1, method="cash")
        place(users["ada"], catalogue["product"], quantity=1)
        cancelled = place(users["ada"], catalogue["product"], quantity=1)
        service.transition(users["admin"], cancelled.id, "cancelled", 1)
        stats = service.financial_summary()
        assert stats["count"] == 1 and stats["revenue"] == Decimal("96.50") and stats["average"] == Decimal("96.50")
        assert stats["unpaid"] == Decimal("48.25") and stats["paid_open"] == Decimal("48.25")
        assert stats["best"][0].units == 2 and stats["daily"][0].sales == Decimal("96.50")
        with pytest.raises(service.BakeryError):
            service.transition(users["admin"], identifier, "cancelled", 5)


def product_values(catalogue, **changes):
    return {
        "name": "New cookie",
        "description": "Chocolate and butter. Contains wheat.",
        "price": "25.75",
        "stock": "15",
        "category_id": catalogue["category"],
        "image": "cookie",
        "active": "1",
        "version": "1",
        **changes,
    }


def test_product_create_edit_deactivate_and_stale_version(app, client, users, catalogue):
    login(client, email="owner@example.com")
    assert post(client, "/admin/bakery/products/new", product_values(catalogue)).status_code == 303
    with app.app_context():
        item = db.session.scalar(db.select(Product).where(Product.name == "New cookie"))
        identifier = item.id
        assert item.price == Decimal("25.75") and item.stock == 15
    values = product_values(catalogue, price="28.25", stock="7", active="")
    assert post(client, f"/admin/bakery/products/{identifier}", values).status_code == 303
    assert client.get(f"/products/{identifier}").status_code == 404
    assert post(client, f"/admin/bakery/products/{identifier}", values).status_code == 422
    assert b"New cookie" not in client.get("/products").data


@pytest.mark.parametrize(
    "changes",
    [
        {"price": "NaN"},
        {"price": "Infinity"},
        {"price": "0"},
        {"price": "12.345"},
        {"price": "1000000"},
        {"stock": "-1"},
        {"stock": "1.5"},
        {"category_id": "999"},
        {"image": "../../secret"},
        {"name": ""},
    ],
)
def test_product_validation(app, users, catalogue, changes):
    with app.app_context():
        with pytest.raises(service.BakeryError):
            service.save_product(users["admin"], product_values(catalogue, **changes))
        assert db.session.scalar(db.select(func.count(Product.id))) == 2


def test_concurrent_last_item_cannot_be_oversold(app, users, catalogue):
    with app.app_context():
        item = db.session.get(Product, catalogue["product"])
        item.stock = 1
        db.session.commit()
    barrier = Barrier(2)

    def worker(actor):
        with app.app_context():
            barrier.wait(timeout=10)
            try:
                return ("ok", place(actor, catalogue["product"], quantity=1).id)
            except service.BakeryError:
                return ("rejected", None)
            finally:
                db.session.remove()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, [users["ada"], users["grace"]]))
    assert sorted(result[0] for result in outcomes) == ["ok", "rejected"]
    with app.app_context():
        assert db.session.get(Product, catalogue["product"]).stock == 0
        assert db.session.scalar(db.select(func.count(Order.id))) == 1


def test_duplicate_checkout_token_under_concurrency(app, users, catalogue):
    token = str(uuid.uuid4())
    barrier = Barrier(2)

    def worker(_):
        with app.app_context():
            barrier.wait(timeout=10)
            try:
                return service.checkout(users["ada"], {str(catalogue["product"]): 1}, details(), token).id
            finally:
                db.session.remove()

    with ThreadPoolExecutor(max_workers=2) as pool:
        identifiers = list(pool.map(worker, range(2)))
    assert identifiers[0] == identifiers[1]
    with app.app_context():
        assert db.session.get(Product, catalogue["product"]).stock == 9


def test_db_constraint_and_stale_inventory_edit(app, users, catalogue):
    with app.app_context():
        item = db.session.get(Product, catalogue["product"])
        item.stock = -1
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
        place(users["ada"], catalogue["product"])
        with pytest.raises(service.BakeryError):
            service.save_product(users["admin"], product_values(catalogue), catalogue["product"])
        assert db.session.get(Product, catalogue["product"]).stock == 8


def test_stale_checkout_token_and_cash_scenario_http(client, users, catalogue):
    login(client)
    post(client, f"/cart/{catalogue['product']}", {"quantity": 1})
    assert post(client, "/checkout", {"checkout_token": "made-up", **details()}).status_code == 409
    response = browser_checkout(client, catalogue["product"], method="cash", scenario="declined")
    assert response.status_code == 422
    assert "Cash on pickup uses" in response.text


def test_migration_roundtrip_and_schema_check(app):
    with app.app_context():
        # Fixture database is disposable and empty. Never downgrade a live application for testing.
        downgrade(directory=str(ROOT / "database/migrations"), revision="6fdee4623110")
        upgrade(directory=str(ROOT / "database/migrations"))
        check(directory=str(ROOT / "database/migrations"))
        assert seed() == 12


def test_checkout_transaction_rolls_back_after_write_failure(app, users, catalogue, monkeypatch):
    def failed_audit(*args):
        raise RuntimeError("Synthetic failure after stock deduction")

    monkeypatch.setattr(service, "audit", failed_audit)
    with app.app_context():
        with pytest.raises(RuntimeError, match="Synthetic"):
            place(users["ada"], catalogue["product"])
        assert db.session.get(Product, catalogue["product"]).stock == 10
        assert db.session.scalar(db.select(func.count(Order.id))) == 0
        assert db.session.scalar(db.select(func.count(OrderItem.id))) == 0


def test_cancellation_after_replenishment_and_stale_order_version(app, users, catalogue):
    with app.app_context():
        order = place(users["ada"], catalogue["product"])
        item = db.session.get(Product, catalogue["product"])
        values = product_values(catalogue, stock="1000000", version=str(item.version))
        service.save_product(users["admin"], values, item.id)
        service.transition(users["admin"], order.id, "cancelled", 1)
        assert db.session.get(Product, item.id).stock == 1000002
        with pytest.raises(service.BakeryError, match="changed"):
            service.transition(users["admin"], order.id, "preparing", 1)
        assert db.session.get(Product, item.id).stock == 1000002


def test_catalogue_pagination(client, app):
    with app.app_context():
        seed()
        category = db.session.scalar(db.select(Category))
        db.session.add(
            Product(
                category_id=category.id,
                name="Another bread",
                description="Bread",
                price=Decimal("10.00"),
                stock=2,
                image="bread",
            )
        )
        db.session.commit()
    first = client.get("/products")
    second = client.get("/products?page=2")
    assert first.status_code == second.status_code == 200
    assert "Page 1 of 2" in first.text and "Next" in first.text
    assert "Page 2 of 2" in second.text and "Previous" in second.text


def test_static_requests_cannot_overwrite_checkout_cookie(client, users, catalogue):
    login(client)
    post(client, f"/cart/{catalogue['product']}", {"quantity": 1})
    assert client.get("/checkout").status_code == 200
    # In a browser, a slow static response can finish after checkout rendered.
    # It must not refresh an older signed session over the new checkout token.
    response = client.get("/static/css/bakery.css")
    assert not response.headers.getlist("Set-Cookie")
