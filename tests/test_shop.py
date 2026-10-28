import re


def links(html: bytes) -> set[str]:
    return set(re.findall(r'href="([^"#]+)"', html.decode()))


def test_shop_pages_open_and_link_to_each_other(client):
    products = client.get("/products")
    assert products.status_code == 200
    assert "/products/sample-product-1" in links(products.data)

    single = client.get("/products/sample-product-1")
    assert single.status_code == 200
    assert b"Sample Product 1" in single.data
    assert {"/products", "/checkout"} <= links(single.data)

    checkout = client.get("/checkout")
    assert checkout.status_code == 200
    assert "/products" in links(checkout.data)

    assert client.get("/products/does-not-exist").status_code == 404


def test_header_and_cart_sidebar_use_shop_links(client):
    page = client.get("/")
    found = links(page.data)
    assert {"/products", "/checkout"} <= found
    assert b'id="cart-sidebar"' in page.data


def test_every_shop_link_resolves(client):
    for path in ("/products", "/products/sample-product-1", "/checkout"):
        for link in links(client.get(path).data):
            if link.startswith("/") and not link.startswith("/static/"):
                assert client.get(link).status_code == 200, f"{path} links to broken {link}"


def test_checkout_form_accepts_post_with_csrf(client):
    token = re.search(r'name="csrf-token" content="([^"]+)"', client.get("/checkout").data.decode()).group(1)
    response = client.post("/checkout", data={"csrf_token": token, "full_name": "Ada", "email": "ada@example.com"})
    assert response.status_code == 303
    assert response.headers["Location"].endswith("/checkout")
