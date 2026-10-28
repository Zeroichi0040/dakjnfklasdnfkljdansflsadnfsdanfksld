"""Storefront routes: products, single product and checkout.

These only exist so the HTML pages open and their links resolve. The product list
below is PLACEHOLDER data; replace it with real products from the database when the
backend is ready (the templates only need the same fields: slug, name, price,
description).
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

bp = Blueprint("shop", __name__)

PLACEHOLDER_PRODUCTS = [
    {"slug": "sample-product-1", "name": "Sample Product 1", "price": 250.00, "description": "Short description."},
    {"slug": "sample-product-2", "name": "Sample Product 2", "price": 320.00, "description": "Short description."},
    {"slug": "sample-product-3", "name": "Sample Product 3", "price": 180.00, "description": "Short description."},
    {"slug": "sample-product-4", "name": "Sample Product 4", "price": 450.00, "description": "Short description."},
    {"slug": "sample-product-5", "name": "Sample Product 5", "price": 275.00, "description": "Short description."},
    {"slug": "sample-product-6", "name": "Sample Product 6", "price": 399.00, "description": "Short description."},
]


@bp.get("/products")
def products():
    return render_template("shop/products.html", products=PLACEHOLDER_PRODUCTS)


@bp.get("/products/<slug>")
def product(slug):
    record = next((item for item in PLACEHOLDER_PRODUCTS if item["slug"] == slug), None)
    if record is None:
        abort(404)
    return render_template("shop/product.html", product=record)


@bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "POST":
        # TODO: validate the form, save the order and clear the cart.
        flash("Checkout form received (placeholder, nothing was saved).", "success")
        return redirect(url_for("shop.checkout"), code=303)
    return render_template("shop/checkout.html")
