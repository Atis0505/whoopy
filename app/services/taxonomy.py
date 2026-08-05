from __future__ import annotations

from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import Category

# Official Google taxonomy format (sample / offline subset).
# Full file can be downloaded later: https://www.google.com/basepages/producttype/taxonomy-with-ids.en-US.txt
SAMPLE_TAXONOMY = """
# Taxonomy Market – Google Product Taxonomy subset (with IDs)
1 - Animals & Pet Supplies
3237 - Animals & Pet Supplies > Pet Supplies
5 - Arts & Entertainment
8 - Arts & Entertainment > Hobbies & Creative Arts
469 - Baby & Toddler
166 - Business & Industrial
141 - Cameras & Optics
222 - Clothing & Accessories
1604 - Clothing & Accessories > Clothing
212 - Electronics
222 - Electronics > Audio  # duplicate id avoided below
267 - Electronics > Computers
278 - Electronics & > Computers > Laptops
"""


# Clean curated subset used for seeding (valid unique IDs)
CURATED_LINES = [
    "1 - Animals & Pet Supplies",
    "3237 - Animals & Pet Supplies > Pet Supplies",
    "2 - Animals & Pet Supplies > Pet Supplies > Dog Supplies",
    "3 - Animals & Pet Supplies > Pet Supplies > Cat Supplies",
    "8 - Arts & Entertainment",
    "5710 - Arts & Entertainment > Hobbies & Creative Arts",
    "469 - Baby & Toddler",
    "537 - Baby & Toddler > Baby Toys",
    "5181 - Baby & Toddler > Nursing & Feeding",
    "141 - Cameras & Optics",
    "142 - Cameras & Optics > Cameras",
    "166 - Business & Industrial",
    "222 - Clothing & Accessories",
    "1604 - Clothing & Accessories > Clothing",
    "212 - Clothing & Accessories > Clothing > Shirts & Tops",
    "2271 - Clothing & Accessories > Shoes",
    "267 - Electronics",
    "278 - Electronics > Computers",
    "328 - Electronics > Computers > Laptops",
    "223 - Electronics > Audio",
    "224 - Electronics > Audio > Headphones",
    "412 - Food, Beverages & Tobacco",
    "413 - Food, Beverages & Tobacco > Food Items",
    "414 - Food, Beverages & Tobacco > Beverages",
    "536 - Home & Garden",
    "604 - Home & Garden > Kitchen & Dining",
    "1239 - Home & Garden > Household Appliances",
    "783 - Health & Beauty",
    "473 - Health & Beauty > Personal Care",
    "784 - Health & Beauty > Health Care",
    "988 - Sporting Goods",
    "499713 - Sporting Goods > Outdoor Recreation",
    "111 - Furniture",
    "436 - Furniture > Beds & Accessories",
    "632 - Hardware",
    "127 - Hardware > Tools",
]


def parse_taxonomy_line(line: str) -> tuple[int, str, list[str]] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if " - " not in line:
        return None
    id_part, path_part = line.split(" - ", 1)
    try:
        google_id = int(id_part.strip())
    except ValueError:
        return None
    parts = [p.strip() for p in path_part.split(">") if p.strip()]
    return google_id, path_part.strip(), parts


def load_taxonomy_into_db(db: Session, lines: Iterable[str] | None = None) -> int:
    """Upsert taxonomy nodes. Returns number of categories created/updated."""
    source = list(lines) if lines is not None else CURATED_LINES
    # google_id -> Category
    by_path: dict[str, Category] = {}
    existing = {c.google_id: c for c in db.query(Category).all()}
    created = 0

    # Process shorter paths first so parents exist
    parsed = []
    seen_ids: set[int] = set()
    for line in source:
        row = parse_taxonomy_line(line)
        if not row:
            continue
        google_id, full_path, parts = row
        if google_id in seen_ids:
            continue
        seen_ids.add(google_id)
        parsed.append((google_id, full_path, parts))

    parsed.sort(key=lambda x: len(x[2]))

    for google_id, full_path, parts in parsed:
        parent = None
        if len(parts) > 1:
            parent_path = " > ".join(parts[:-1])
            parent = by_path.get(parent_path)
            if parent is None:
                parent = db.query(Category).filter(Category.full_path == parent_path).first()

        cat = existing.get(google_id)
        if cat is None:
            cat = Category(
                google_id=google_id,
                name=parts[-1],
                full_path=full_path,
                parent_id=parent.id if parent else None,
                depth=len(parts) - 1,
            )
            db.add(cat)
            db.flush()
            existing[google_id] = cat
            created += 1
        else:
            cat.name = parts[-1]
            cat.full_path = full_path
            cat.parent_id = parent.id if parent else None
            cat.depth = len(parts) - 1

        by_path[full_path] = cat

    db.commit()
    return created


def load_taxonomy_file(db: Session, path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return load_taxonomy_into_db(db, text.splitlines())
