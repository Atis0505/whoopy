from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
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

    from app.services.storefront_ops import feeds_should_serve

    if not feeds_should_serve(db):
        return Response(
            content='<?xml version="1.0"?><rss version="2.0"><channel><title>disabled</title></channel></rss>',
            media_type="application/xml; charset=utf-8",
        )
    xml = build_google_merchant_xml(db)
    return Response(content=xml, media_type="application/xml; charset=utf-8")


@router.get("/feeds/meta-catalog.xml")
def meta_catalog_feed(db: Session = Depends(get_db)):
    from fastapi.responses import Response

    from app.services.marketing_feeds import build_meta_catalog_xml
    from app.services.storefront_ops import feeds_should_serve

    if not feeds_should_serve(db):
        return Response(
            content='<?xml version="1.0"?><rss version="2.0"><channel><title>disabled</title></channel></rss>',
            media_type="application/xml; charset=utf-8",
        )
    return Response(content=build_meta_catalog_xml(db), media_type="application/xml; charset=utf-8")


@router.get("/feeds/arukereso.xml")
def arukereso_feed(db: Session = Depends(get_db)):
    from fastapi.responses import Response

    from app.services.marketing_feeds import build_arukereso_xml
    from app.services.storefront_ops import feeds_should_serve

    if not feeds_should_serve(db):
        return Response(
            content='<?xml version="1.0"?><products></products>',
            media_type="application/xml; charset=utf-8",
        )
    return Response(content=build_arukereso_xml(db), media_type="application/xml; charset=utf-8")


@router.get("/go/aff/{code}")
def affiliate_redirect(code: str, request: Request, next: str = "/", db: Session = Depends(get_db)):
    from app.services.attribution import record_affiliate_click

    request.session["affiliate_code"] = code.strip().upper()[:64]
    request.session["utm_source"] = request.session.get("utm_source") or "affiliate"
    request.session["utm_medium"] = request.session.get("utm_medium") or "partner"
    request.session["utm_campaign"] = request.session.get("utm_campaign") or code.strip().upper()[:64]
    record_affiliate_click(db, code)
    dest = next if next.startswith("/") else "/"
    return RedirectResponse(dest, status_code=303)


@router.get("/go/c/{campaign_id}")
def campaign_click(campaign_id: int, request: Request, db: Session = Depends(get_db)):
    from app.services.attribution import bump_campaign_click

    c = bump_campaign_click(db, campaign_id)
    dest = (c.link_url if c and c.link_url else "/") or "/"
    if not dest.startswith("/") and not dest.startswith("http"):
        dest = "/"
    return RedirectResponse(dest, status_code=303)


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
    page: int = 1,
):
    from app.services.catalog import list_brands, list_catalog, pager_query
    from app.services.merchandising import active_campaigns, bestsellers, hero_for_session, showcase_products

    result = list_catalog(
        db,
        page=page,
        q=q,
        category_id=category,
        brand=brand,
        in_stock=in_stock == "1",
        sort=sort or "newest",
        min_price=min_price,
        max_price=max_price,
    )
    products = result.items
    _enrich_products(db, products)
    brands = list_brands(db)
    roots = db.query(Category).filter(Category.parent_id.is_(None)).order_by(Category.name).all()
    best = bestsellers(db, limit=8)
    _enrich_products(db, best)
    showcase = []
    show_showcase = page <= 1 and not q and not brand and not category and in_stock != "1"
    if show_showcase:
        showcase = showcase_products(db, limit=14)
        _enrich_products(db, showcase)
    filter_params = {
        "q": q,
        "category": category or "",
        "brand": brand,
        "in_stock": in_stock,
        "sort": sort,
        "min_price": min_price if min_price is not None else "",
        "max_price": max_price if max_price is not None else "",
    }
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
            showcase_products=showcase,
            hero_campaigns=hero_for_session(db, request.session),
            strip_campaigns=active_campaigns(db, "strip"),
            tile_campaigns=active_campaigns(db, "tile"),
            pager=result,
            pager_base="/",
            pager_qs=lambda p: pager_query(filter_params, p),
        ),
    )


@router.get("/c/{google_id}", response_class=HTMLResponse)
def category_page(
    google_id: int,
    request: Request,
    page: int = 1,
    view: str = "",
    db: Session = Depends(get_db),
):
    from app.services.catalog import list_catalog, pager_query
    from app.services.category_browse import resolve_browse_mode

    cat = db.query(Category).filter(Category.google_id == google_id).first()
    if not cat:
        return RedirectResponse("/", status_code=302)

    force_products = view.strip().lower() in ("products", "all", "list")
    browse = resolve_browse_mode(db, cat, force_products=force_products)
    products: list = []
    result = None
    if browse["mode"] == "products" or force_products:
        result = list_catalog(db, page=page, category_path_prefix=cat.full_path, sort="newest")
        products = result.items
        _enrich_products(db, products)
        browse["mode"] = "products"

    children = db.query(Category).filter(Category.parent_id == cat.id).order_by(Category.name).all()
    return templates.TemplateResponse(
        "store/category.html",
        store_context(
            request,
            db,
            category=cat,
            children=children,
            products=products,
            pager=result,
            pager_base=f"/c/{google_id}",
            pager_qs=lambda p: pager_query({"view": "products"} if force_products else {}, p),
            browse=browse,
            force_products=force_products,
        ),
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
    from app.services.customer_ux import push_recent_product, session_list_ids

    push_recent_product(request.session, product.id)
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
    compare_ids = session_list_ids(request.session, "compare_ids")
    from app.services.compliance import lowest_price_30d

    lowest = lowest_price_30d(db, product.id)
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
            in_compare=product.id in compare_ids,
            lowest_30d=lowest,
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


@router.post("/cart/gift")
def cart_gift(request: Request, gift_card_code: str = Form(""), db: Session = Depends(get_db)):
    from app.services.customer_ux import find_gift_card

    cart = cart_for_request(request, db)
    code = gift_card_code.strip().upper()
    if code and not find_gift_card(db, code):
        items = (
            db.query(CartItem)
            .options(
                joinedload(CartItem.offer).joinedload(Offer.product),
                joinedload(CartItem.offer).joinedload(Offer.supplier),
            )
            .filter(CartItem.cart_id == cart.id)
            .all()
        )
        return templates.TemplateResponse(
            "store/cart.html",
            store_context(request, db, items=items, gift_error=True),
            status_code=400,
        )
    cart.gift_card_code = code
    db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/loyalty")
def cart_loyalty(request: Request, loyalty_redeem_points: int = Form(0), db: Session = Depends(get_db)):
    cart = cart_for_request(request, db)
    user = get_current_user(request, db)
    pts = max(0, int(loyalty_redeem_points or 0))
    if user:
        pts = min(pts, int(user.loyalty_points or 0))
    else:
        pts = 0
    cart.loyalty_redeem_points = pts
    db.commit()
    return RedirectResponse("/cart", status_code=303)


@router.post("/cart/delivery")
def cart_delivery(
    request: Request,
    delivery_mode: str = Form("courier"),
    pickup_provider: str = Form(""),
    pickup_point_id: str = Form(""),
    pickup_point_label: str = Form(""),
    db: Session = Depends(get_db),
):
    cart = cart_for_request(request, db)
    mode = delivery_mode if delivery_mode in ("courier", "pickup") else "courier"
    cart.delivery_mode = mode
    if mode == "pickup":
        cart.pickup_provider = pickup_provider.strip()[:32]
        cart.pickup_point_id = pickup_point_id.strip()[:64]
        cart.pickup_point_label = pickup_point_label.strip()[:255]
    else:
        cart.pickup_provider = ""
        cart.pickup_point_id = ""
        cart.pickup_point_label = ""
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
    billing_same: str = Form("1"),
    billing_full_name: str = Form(""),
    billing_country: str = Form(""),
    billing_city: str = Form(""),
    billing_address: str = Form(""),
    billing_zip: str = Form(""),
    billing_tax_id: str = Form(""),
    db: Session = Depends(get_db),
):
    cart = cart_for_request(request, db)
    user = get_current_user(request, db)
    request.session["country"] = country.upper()
    cart.country = country.upper()
    db.commit()
    same = billing_same == "1"
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
            billing_same=same,
            billing_full_name=billing_full_name,
            billing_country=billing_country,
            billing_city=billing_city,
            billing_address=billing_address,
            billing_zip=billing_zip,
            billing_tax_id=billing_tax_id,
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
    user = get_current_user(request, db)
    token = request.query_params.get("t", "")
    allowed = False
    if user and (user.id == order.customer_id or user.is_staff):
        allowed = True
    elif request.session.get("last_order") == order.order_number:
        allowed = True
    elif token and order.access_token and token == order.access_token:
        allowed = True
        request.session["last_order"] = order.order_number
    if not allowed:
        return RedirectResponse("/track?error=1", status_code=303)
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
    from app.services.store_settings import get_store_settings
    from app.services.storefront_ops import storefront_is_closed

    user = try_login(db, email.strip().lower(), password)
    if not user:
        return templates.TemplateResponse(
            "store/login.html",
            store_context(request, db, error="bad_login"),
            status_code=401,
        )
    if storefront_is_closed(get_store_settings(db)) and user.role == "worker" and not user.is_admin:
        return templates.TemplateResponse(
            "store/login.html",
            store_context(request, db, error="worker_closed"),
            status_code=403,
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
    from app.models import Subscription
    from app.services.subscriptions import ALLOWED_INTERVALS

    orders = db.query(Order).filter(Order.customer_id == user.id).order_by(Order.created_at.desc()).limit(20).all()
    subscriptions = (
        db.query(Subscription)
        .options(joinedload(Subscription.lines))
        .filter(Subscription.user_id == user.id)
        .order_by(Subscription.id.desc())
        .all()
    )
    return templates.TemplateResponse(
        "store/account.html",
        store_context(
            request,
            db,
            orders=orders,
            subscriptions=subscriptions,
            interval_choices=ALLOWED_INTERVALS,
        ),
    )


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
