"""Idempotent, explicit educational catalogue. No users or private data are seeded."""

from decimal import Decimal

from backend.modules.bakery.service import lock_writes
from database import db
from database.models.bakery import Category, Product

SAMPLES = [
    (
        "Bread",
        "bread",
        "Classic Pandesal · 6 pack",
        "Soft, golden Filipino breakfast rolls with a delicate breadcrumb crust. Baked fresh for your morning coffee. Contains wheat and dairy.",
        "48.00",
        "bread",
        50,
    ),
    (
        "Bread",
        "bread",
        "Country Sourdough",
        "A slow-fermented loaf with a crisp crust and tender, tangy centre. Perfect for toast. Contains wheat.",
        "185.00",
        "bread",
        16,
    ),
    (
        "Pastries",
        "pastries",
        "Butter Croissant",
        "Flaky layers of real butter, folded by hand and baked until golden. Contains wheat, dairy and eggs.",
        "85.00",
        "pastry",
        24,
    ),
    (
        "Pastries",
        "pastries",
        "Pain au Chocolat",
        "Our buttery laminated pastry wrapped around a rich dark chocolate centre. Contains wheat, dairy, eggs and soy.",
        "105.00",
        "pastry",
        20,
    ),
    (
        "Cakes",
        "cakes",
        "Ube Cloud Cake",
        "A six-inch purple yam sponge with light vanilla cream. A little celebration in every slice. Contains wheat, dairy and eggs.",
        "680.00",
        "cake",
        6,
    ),
    (
        "Cakes",
        "cakes",
        "Chocolate Celebration Cake",
        "Six inches of moist cocoa sponge and silky chocolate frosting. Made for sharing. Contains wheat, dairy, eggs and soy.",
        "750.00",
        "cake",
        5,
    ),
    (
        "Cookies",
        "cookies",
        "Chocolate Chunk Cookies · 4 pack",
        "Crisp edges, soft centres and generous chunks of dark chocolate. Contains wheat, dairy, eggs and soy.",
        "160.00",
        "cookie",
        18,
    ),
    (
        "Cookies",
        "cookies",
        "Oat & Raisin Cookies · 4 pack",
        "A comforting mix of rolled oats, plump raisins and warm cinnamon. Contains wheat, dairy and eggs.",
        "140.00",
        "cookie",
        15,
    ),
    (
        "Filipino Favourites",
        "filipino",
        "Cheese Ensaymada",
        "A pillowy brioche swirl topped with butter, sugar and grated cheese. Contains wheat, dairy and eggs.",
        "75.00",
        "bun",
        24,
    ),
    (
        "Filipino Favourites",
        "filipino",
        "Spanish Bread · 4 pack",
        "Soft rolls filled with a sweet, buttery breadcrumb centre. Contains wheat, dairy and eggs.",
        "68.00",
        "bread",
        30,
    ),
    (
        "Filipino Favourites",
        "filipino",
        "Ube Cheese Pandesal · 4 pack",
        "Purple yam rolls with a creamy cheese centre. Contains wheat, dairy and eggs.",
        "120.00",
        "bun",
        20,
    ),
    (
        "Pastries",
        "pastries",
        "Cinnamon Morning Roll",
        "A tender swirl of cinnamon sugar finished with vanilla glaze. Contains wheat, dairy and eggs.",
        "95.00",
        "bun",
        0,
    ),
]


def seed():
    try:
        lock_writes()
        added = 0
        for category_name, slug, name, description, price, image, stock in SAMPLES:
            category = db.session.scalar(db.select(Category).where(Category.slug == slug))
            if not category:
                category = Category(name=category_name, slug=slug)
                db.session.add(category)
                db.session.flush()
            if db.session.scalar(db.select(Product.id).where(Product.name == name)):
                continue
            db.session.add(
                Product(
                    category_id=category.id,
                    name=name,
                    description=description,
                    price=Decimal(price),
                    image=image,
                    stock=stock,
                    active=True,
                )
            )
            added += 1
        db.session.commit()
        return added
    except Exception:
        db.session.rollback()
        raise
