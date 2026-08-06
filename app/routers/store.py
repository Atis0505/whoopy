from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import cart_for_request, get_current_user, post_login_redirect, store_context, try_login
from app.i18n import normalize_lang
from app.models import CartItem, Category, CmsPage, NewsletterSubscriber, Offer, Order, Product, User
from app.seed_auth import hash_password
from app.services.cart import (
    add_to_cart,
    quote_cart,
    serialize_shipping_choices,
    parse_shipping_choices,
    update_cart_item,
)
from app.services.checkout import create_order_from_cart
from app.services.google_feed import build_google_merchant_xml
from app.services.pricing import find_coupon, promo_discount_for_product
from app.services.pricing_engine import select_buybox_offer


router = APIRouter(tags=["store"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/feeds/google-merchant.xml")
def google_merchant_feed(db: Session = Depends(get_db)):
    from fastapi.responses import Response

    xml = build_google_merchant_xml(db)
    return Response(content=xml, media_type="application/xml; charset=utf-8")


def _enrich_products(db: Session, products: list[Product]) -> None:
    for p in products:
        buy = select_buybox_offer(db, p)
        active_offers = [o for o in p.offers if o.active and o.stock > 0]
        prices = []
        for o in active_offers:
            unit, promo = promo_discount_for_product(db, p, o.price)
            prices.append(unit)
            o.display_price = unit
            o.promo = promo
        if buy and buy in active_offers:
            unit, promo = promo_discount_for_product(db, p, buy.price)
            p.best_price = unit
            p.buybox_offer = buy
        else:
            p.best_price = min(prices) if prices else None
            p.buybox_offer = buy
        p.offer_count = len(active_offers)
        p.has_promo = any(getattr(o, "promo", None) for o in active_offers)


@router.post("/prefs")
def set_prefs(
    request: Request,
    lang: str = Form(None),
    currency: str = Form(None),
    country: str = Form(None),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    if lang:
        request.session["lang"] = normalize_lang(lang)
    if currency:
        request.session["currency"] = currency.upper()
    if country:
        request.session["country"] = country.upper()
    cart = cart_for_request(request, db)
    return RedirectResponse(next or "/", status_code=303)


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: Session = Depends(get_db),
    q: str = "",
    category: int | None = None,
    brand: str = "",
    in_stock: str = "",
    sort: str = "newest",
    min_price: float | None = None,
    max_price: float | None = None,
):
    from app.services.merchandising import active_campaigns, bestsellers

    query = (
        db.query(Product)
        .options(joinedload(Product.offers).joinedload(Offer.supplier), joinedload(Product.category))
        .filter(Product.active.is_(True))
    )
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.title.ilike(like), Product.brand.ilike(like), Product.description.ilike(like)))
    if category:
        query = query.filter(Product.category_id == category)
    if brand:
        query = query.filter(Product.brand.ilike(brand.strip()))
    if sort == "bestseller":
        query = query.order_by(Product.sold_count.desc())
    elif sort == "title":
        query = query.order_by(Product.title.asc())
    else:
        query = query.order_by(Product.created_at.desc())
    products = query.all()
    _enrich_products(db, products)
    if in_stock == "1":
        products = [p for p in products if (p.best_price is not None)]
    if min_price is not None:
        products = [p for p in products if p.best_price is not None and p.best_price >= min_price]
    if max_price is not None:
        products = [p for p in products if p.best_price is not None and p.best_price <= max_price]
    if sort == "price_asc":
        products = sorted(products, key=lambda p: p.best_price if p.best_price is not None else 1e18)
    elif sort == "price_desc":
        products = sorted(products, key=lambda p: p.best_price if p.best_price is not None else -1, reverse=True)
    brands = sorted({p.brand for p in db.query(Product).filter(Product.active.is_(True), Product.brand != "").all() if p.brand})
    roots = db.query(Category).filter(Category.parent_id.is_(None)).order_by(Category.name).all()
    best = bestsellers(db, limit=8)
    _enrich_products(db, best)
    return templates.TemplateResponse(
        "store/home.html",
        store_context(
            request,
            db,
            products=products,
            categories=roots,
            q=q,
            brands=brands,
            brand=brand,
            in_stock=in_stock,
            sort=sort,
            min_price=min_price,
            max_price=max_price,
            bestsellers=best,
            hero_campaigns=active_campaigns(db, "hero"),
            strip_campaigns=active_campaigns(db, "strip"),
            tile_campaigns=active_campaigns(db, "tile"),
        ),
    )


@router.get("/c/{google_id}", response_class=HTMLResponse)
def category_page(google_id: int, request: Request, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.google_id == google_id).first()
    if not cat:
        return RedirectResponse("/", status_code=302)
    products = (
        db.query(Product)
        .join(Category, Product.category_id == Category.id)
        .options(joinedload(Product.offers), joinedload(Product.category))
        .filter(Product.active.is_(True), Category.full_path.startswith(cat.full_path))
        .all()
    )
    _enrich_products(db, products)
    children = db.query(Category).filter(Category.parent_id == cat.id).order_by(Category.name).all()
    return templates.TemplateResponse(
        "store/category.html",
        store_context(request, db, category=cat, children=children, products=products),
    )


@router.get("/p/{slug}", response_class=HTMLResponse)
def product_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    product = (
        db.query(Product)
        .options(joinedload(Product.offers).joinedload(Offer.supplier), joinedload(Product.category))
        .filter(Product.slug == slug, Product.active.is_(True))
        .first()
    )
    if not product:
        return RedirectResponse("/", status_code=302)
    offers = []
    for o in product.offers:
        if not o.active:
            continue
        unit, promo = promo_discount_for_product(db, product, o.price)
        o.display_price = unit
        o.list_price = o.price
        o.promo = promo
        offers.append(o)
    buy = select_buybox_offer(db, product)
    if buy:
        offers.sort(key=lambda o: (0 if o.id == buy.id else 1, o.display_price, o.lead_days))
    else:
        offers.sort(key=lambda o: (o.display_price, o.lead_days))

    from app.models import ProductReview

    reviews = (
        db.query(ProductReview)
        .filter(ProductReview.product_id == product.id, ProductReview.approved.is_(True))
        .order_by(ProductReview.id.desc())
        .limit(50)
        .all()
    )
    related = []
    if product.category_id:
        related = (
            db.query(Product)
            .filter(
                Product.active.is_(True),
                Product.category_id == product.category_id,
                Product.id != product.id,
            )
            .order_by(Product.sold_count.desc())
            .limit(4)
            .all()
        )
        _enrich_products(db, related)
    return templates.TemplateResponse(
        "store/product.html",
        store_context(
            request,
            db,
            product=product,
            offers=offers,
            buybox_offer=buy,
            reviews=reviews,
            related=related,
        ),
    )


@router.post("/cart/add")
def cart_add(request: Request, offer_id: int = Form(...), quantity: int = Form(1), db: Session = Depends(get_db)):
    cart = cart_for_request(request, db)
    try:
        add_to_cart(db, cart, offer_id, quantity)
    except ValueError:
        return RedirectResponse(request.headers.get("referer", "/"), status_code=303)
    return RedirectResponse("/cart", status_code=303)


@router.get("/cart", response_class=HTMLResponse)
def cart_view(request: Request, db: Session = Depends(get_db)):
    cart = cart_for_request(request, db)
    items = (
        db.query(CartItem)
        .options(
            joinedload(CartItem.offer).joinedload(Offer.product),
            joinedload(CartItem.offer).joinedload(Offer.supplier),
        )
        .filter(CartItem.cart_id == cart.id)
        .all()
    )
    for item in items:
        unit, promo = promo_discount_for_product(db, item.offer.product, item.offer.price)
        item.unit_price = unit
        item.line_total = unit * item.quantity
        item.promo = promo
    return templates.TemplateResponse("store/cart.html", store_context(request, db, items=items))


@router.post("/cart/update")
def cart_update(request: Request, item_id: int = Form(...), quantity: int = Form(...), db: Session = Depends(get_db)):
    cart = cart_for_request(request, db)
    try:
        update_cart_item(db, cart, item_id, quantity)
    except ValueError:
        pass
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/coupon")
def cart_coupon(request: Request, coupon_code: str = Form(""), db: Session = Depends(get_db)):
    cart = cart_for_request(request, db)
    code = coupon_code.strip().upper()
    if code and not find_coupon(db, code):
        items = (
            db.query(CartItem)
            .options(
                joinedload(CartItem.offer).joinedload(Offer.product),
                joinedload(CartItem.offer).joinedload(Offer.supplier),
            )
            .filter(CartItem.cart_id == cart.id)
            .all()
        )
        ctx = store_context(request, db, items=items, coupon_error=True)
        return templates.TemplateResponse("store/cart.html", ctx, status_code=400)
    cart.coupon_code = code
    db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/payment")
def cart_payment(request: Request, payment_preference: str = Form("prepaid"), db: Session = Depends(get_db)):
    cart = cart_for_request(request, db)
    if payment_preference not in ("prepaid", "cod", "invoice"):
        payment_preference = "prepaid"
    cart.payment_preference = payment_preference
    db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/shipping")
async def cart_shipping(request: Request, db: Session = Depends(get_db)):
    cart = cart_for_request(request, db)
    form = await request.form()
    choices = parse_shipping_choices(cart.shipping_choices)
    for key, value in form.items():
        if key.startswith("ship_") and str(value).isdigit():
            sid = key.replace("ship_", "")
            if sid.isdigit():
                choices[int(sid)] = int(value)
    cart.shipping_choices = serialize_shipping_choices(choices)
    db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.get("/checkout", response_class=HTMLResponse)
def checkout_form(request: Request, db: Session = Depends(get_db)):
    cart = cart_for_request(request, db)
    quote = quote_cart(db, cart)
    if quote.item_count == 0:
        return RedirectResponse("/cart", status_code=302)
    user = get_current_user(request, db)
    return templates.TemplateResponse("store/checkout.html", store_context(request, db, error=None, prefill=user))


@router.post("/checkout", response_class=HTMLResponse)
def checkout_submit(
    request: Request,
    email: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(""),
    country: str = Form("HU"),
    city: str = Form(...),
    address: str = Form(...),
    zip_code: str = Form(""),
    notes: str = Form(""),
    newsletter: str = Form(""),
    db: Session = Depends(get_db),
):
    cart = cart_for_request(request, db)
    user = get_current_user(request, db)
    request.session["country"] = country.upper()
    cart.country = country.upper()
    db.commit()
    try:
        order = create_order_from_cart(
            db,
            cart,
            email=email,
            full_name=full_name,
            phone=phone,
            country=country,
            city=city,
            address=address,
            zip_code=zip_code,
            notes=notes,
            customer_id=user.id if user else None,
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            "store/checkout.html",
            store_context(request, db, error=str(exc), prefill=user),
            status_code=400,
        )

    if newsletter == "1":
        existing = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == email.strip().lower()).first()
        if existing:
            existing.active = True
        else:
            db.add(
                NewsletterSubscriber(
                    email=email.strip().lower(),
                    lang=cart.lang or "hu",
                    active=True,
                    source="checkout",
                )
            )
        if user:
            user.newsletter_opt_in = True
        db.commit()

    request.session["last_order"] = order.order_number

    # Online fizetés (prepaid) → fizetési kapu
    if order.payment_method == "prepaid":
        return RedirectResponse(f"/pay/{order.order_number}", status_code=303)
    return RedirectResponse(f"/order/{order.order_number}", status_code=303)


@router.get("/order/{order_number}", response_class=HTMLResponse)
def order_thanks(order_number: str, request: Request, db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.order_number == order_number)
        .first()
    )
    if not order:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("store/order.html", store_context(request, db, order=order))


@router.get("/taxonomy", response_class=HTMLResponse)
def taxonomy_browser(request: Request, db: Session = Depends(get_db)):
    roots = db.query(Category).filter(Category.parent_id.is_(None)).order_by(Category.name).all()
    counts = dict(
        db.query(Product.category_id, func.count(Product.id))
        .filter(Product.active.is_(True))
        .group_by(Product.category_id)
        .all()
    )
    return templates.TemplateResponse("store/taxonomy.html", store_context(request, db, roots=roots, counts=counts))


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("store/register.html", store_context(request, db, error=None))


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(""),
    phone: str = Form(""),
    newsletter: str = Form(""),
    db: Session = Depends(get_db),
):
    email_n = email.strip().lower()
    if db.query(User).filter(User.email == email_n).first():
        return templates.TemplateResponse(
            "store/register.html",
            store_context(request, db, error="email_taken"),
            status_code=400,
        )
    if len(password) < 6:
        return templates.TemplateResponse(
            "store/register.html",
            store_context(request, db, error="password_short"),
            status_code=400,
        )
    cart = cart_for_request(request, db)
    user = User(
        email=email_n,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        phone=phone.strip(),
        role="customer",
        is_admin=False,
        newsletter_opt_in=newsletter == "1",
        preferred_lang=cart.lang or "hu",
        preferred_currency=cart.currency or "HUF",
    )
    db.add(user)
    db.flush()
    if newsletter == "1":
        if not db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == email_n).first():
            db.add(NewsletterSubscriber(email=email_n, lang=cart.lang, active=True, source="register"))
    db.commit()
    request.session["user_id"] = user.id
    return RedirectResponse("/account", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def customer_login_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("store/login.html", store_context(request, db, error=None))


@router.post("/login", response_class=HTMLResponse)
def customer_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = try_login(db, email.strip().lower(), password)
    if not user:
        return templates.TemplateResponse(
            "store/login.html",
            store_context(request, db, error="bad_login"),
            status_code=401,
        )
    request.session["user_id"] = user.id
    request.session["lang"] = user.preferred_lang or "hu"
    request.session["currency"] = user.preferred_currency or "HUF"
    return RedirectResponse(post_login_redirect(user), status_code=303)


@router.get("/logout")
def customer_logout(request: Request):
    request.session.pop("user_id", None)
    return RedirectResponse("/", status_code=303)


@router.get("/account", response_class=HTMLResponse)
def account_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    orders = db.query(Order).filter(Order.customer_id == user.id).order_by(Order.created_at.desc()).limit(20).all()
    return templates.TemplateResponse("store/account.html", store_context(request, db, orders=orders))


@router.post("/account/newsletter")
def account_newsletter(request: Request, newsletter: str = Form(""), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    opt = newsletter == "1"
    user.newsletter_opt_in = opt
    sub = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == user.email).first()
    if opt:
        if sub:
            sub.active = True
        else:
            db.add(NewsletterSubscriber(email=user.email, lang=user.preferred_lang, active=True, source="account"))
    elif sub:
        sub.active = False
    db.commit()
    return RedirectResponse("/account", status_code=303)


@router.post("/newsletter")
def newsletter_subscribe(
    request: Request,
    email: str = Form(...),
    lang: str = Form("hu"),
    db: Session = Depends(get_db),
):
    email_n = email.strip().lower()
    sub = db.query(NewsletterSubscriber).filter(NewsletterSubscriber.email == email_n).first()
    if sub:
        sub.active = True
        sub.lang = normalize_lang(lang)
    else:
        db.add(NewsletterSubscriber(email=email_n, lang=normalize_lang(lang), active=True, source="footer"))
    db.commit()
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)


@router.get("/pages/{slug}", response_class=HTMLResponse)
def cms_page(slug: str, request: Request, db: Session = Depends(get_db)):
    page = db.query(CmsPage).filter(CmsPage.slug == slug, CmsPage.published.is_(True)).first()
    if not page:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("store/cms_page.html", store_context(request, db, page=page))
