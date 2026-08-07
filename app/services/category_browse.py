"""Kategória böngészés: kevés termék → lista; sok → alkategória-kártyák (minden mélység)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Category, Product

# Ennyi termék felett (az ág alatt) alkategória-kártyák a fő nézet
SUBCATEGORY_THRESHOLD = 12


# Stock / atmoszféra képek kategória kulcsszavakra (Unsplash)
_STOCK_BY_KEYWORD: list[tuple[str, str]] = [
    ("headphone", "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&q=80"),
    ("audio", "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=800&q=80"),
    ("laptop", "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=800&q=80"),
    ("computer", "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80"),
    ("electron", "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80"),
    ("television", "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?w=800&q=80"),
    ("video game", "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?w=800&q=80"),
    ("camera", "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=800&q=80"),
    ("clothing", "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=800&q=80"),
    ("shoe", "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800&q=80"),
    ("furniture", "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=800&q=80"),
    ("kitchen", "https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=800&q=80"),
    ("appliance", "https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=800&q=80"),
    ("baby", "https://images.unsplash.com/photo-1519689680058-324335c77eba?w=800&q=80"),
    ("toy", "https://images.unsplash.com/photo-1587654780291-39c9404d746b?w=800&q=80"),
    ("health", "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=800&q=80"),
    ("beauty", "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=800&q=80"),
    ("sport", "https://images.unsplash.com/photo-1461896836934-ffe607ba6851?w=800&q=80"),
    ("pet", "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=800&q=80"),
    ("dog", "https://images.unsplash.com/photo-1589924691995-400dc9ecc119?w=800&q=80"),
    ("food", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800&q=80"),
    ("home", "https://images.unsplash.com/photo-1616486338812-3dadae4b4ace?w=800&q=80"),
    ("garden", "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800&q=80"),
    ("office", "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&q=80"),
    ("vehicle", "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=800&q=80"),
]

_DEFAULT_STOCK = "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=800&q=80"


@dataclass
class SubcategoryCard:
    category: Category
    product_count: int
    image_url: str


def count_products_under(db: Session, cat: Category) -> int:
    prefix = cat.full_path or cat.name
    return (
        db.query(func.count(Product.id))
        .join(Category, Product.category_id == Category.id)
        .filter(Product.active.is_(True), Category.full_path.startswith(prefix))
        .scalar()
        or 0
    )


def stock_image_for_category(cat: Category) -> str:
    hay = f"{cat.name} {cat.full_path}".lower()
    for key, url in _STOCK_BY_KEYWORD:
        if key in hay:
            return url
    return _DEFAULT_STOCK


def _sample_product_image(db: Session, cat: Category) -> str | None:
    prefix = cat.full_path or cat.name
    row = (
        db.query(Product.image_url)
        .join(Category, Product.category_id == Category.id)
        .filter(
            Product.active.is_(True),
            Category.full_path.startswith(prefix),
            Product.image_url != "",
            Product.image_url.isnot(None),
        )
        .order_by(Product.sold_count.desc())
        .first()
    )
    return row[0] if row and row[0] else None


def subcategory_cards(db: Session, cat: Category, *, only_with_products: bool = True) -> list[SubcategoryCard]:
    children = db.query(Category).filter(Category.parent_id == cat.id).order_by(Category.name).all()
    cards: list[SubcategoryCard] = []
    for ch in children:
        n = count_products_under(db, ch)
        if only_with_products and n < 1:
            continue
        img = _sample_product_image(db, ch) or stock_image_for_category(ch)
        cards.append(SubcategoryCard(category=ch, product_count=n, image_url=img))
    return cards


def category_ancestors(db: Session, cat: Category) -> list[Category]:
    chain: list[Category] = []
    cur = cat
    seen: set[int] = set()
    while cur and cur.id not in seen:
        seen.add(cur.id)
        chain.append(cur)
        if not cur.parent_id:
            break
        cur = db.get(Category, cur.parent_id)
    chain.reverse()
    return chain


def resolve_browse_mode(
    db: Session,
    cat: Category,
    *,
    force_products: bool = False,
    threshold: int = SUBCATEGORY_THRESHOLD,
) -> dict:
    """
    products  — terméklista (kevés áru VAGY levél / ?view=products)
    subcategories — alkategória-kártyák (sok áru + van gyermek)
    """
    total = count_products_under(db, cat)
    children = db.query(Category).filter(Category.parent_id == cat.id).count()
    cards = subcategory_cards(db, cat, only_with_products=True)
    # Ha van termék nélküli gyermek is, de threshold felett vagyunk: mutassuk a nem üreseket;
    # ha minden üres de vannak gyermekek és sok termék a saját leafen ritka — akkor products.
    use_subcats = (
        not force_products
        and children > 0
        and total > threshold
        and len(cards) > 0
    )
    # Edge: sok termék, vannak gyermekek, de a termékek közvetlenül ezen a node-on vannak
    # (nem az ágakban) → akkor is subcats ha van legalább 1 nem üres gyerek, különben products
    if not force_products and children > 0 and total > threshold and not cards:
        cards = subcategory_cards(db, cat, only_with_products=False)
        use_subcats = len(cards) > 0

    return {
        "mode": "subcategories" if use_subcats else "products",
        "total_products": total,
        "threshold": threshold,
        "has_children": children > 0,
        "subcategory_cards": cards if use_subcats else subcategory_cards(db, cat, only_with_products=False),
        "show_child_chips": (not use_subcats) and children > 0,
        "ancestors": category_ancestors(db, cat),
    }
