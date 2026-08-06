"""Termékkép feltöltés – helyi tároló (`data/uploads/products`)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import BASE_DIR, settings
from app.models import Product, ProductImage

UPLOAD_ROOT = BASE_DIR / "data" / "uploads" / "products"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def ensure_upload_dirs() -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)


def public_url(product_id: int, filename: str) -> str:
    """Relatív path a storefront / media mount felé."""
    return f"/media/products/{product_id}/{filename}"


def absolute_media_url(relative_or_absolute: str) -> str:
    """CDN / PUBLIC_BASE — abszolút URL a Merchant feedhez és primary image_url-hez."""
    url = (relative_or_absolute or "").strip()
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = settings.media_base
    if not url.startswith("/"):
        url = "/" + url
    return f"{base}{url}" if base else url


def s3_enabled() -> bool:
    return bool(settings.s3_bucket and settings.s3_access_key and settings.s3_secret_key)


def upload_bytes_to_s3(key: str, data: bytes, content_type: str = "application/octet-stream") -> str | None:
    """Opcionális S3/R2 feltöltés. Vissza: publikus URL vagy None."""
    if not s3_enabled():
        return None
    try:
        import boto3
        from botocore.client import Config
    except ImportError as exc:
        raise HTTPException(500, "boto3 nincs telepítve (pip install boto3)") from exc

    client_kwargs: dict = {
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
        "region_name": settings.s3_region or "auto",
        "config": Config(signature_version="s3v4"),
    }
    if settings.s3_endpoint_url:
        client_kwargs["endpoint_url"] = settings.s3_endpoint_url
    client = boto3.client("s3", **client_kwargs)
    client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    if settings.s3_public_base:
        return f"{settings.s3_public_base.rstrip('/')}/{key}"
    if settings.media_public_base:
        return f"{settings.media_public_base.rstrip('/')}/{key}"
    # path-style guess
    if settings.s3_endpoint_url:
        return f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{key}"
    return f"https://{settings.s3_bucket}.s3.amazonaws.com/{key}"


def disk_path(product_id: int, filename: str) -> Path:
    return UPLOAD_ROOT / str(product_id) / filename


def _safe_ext(filename: str, content_type: str | None) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in ALLOWED_EXT:
        return ext if ext != ".jpeg" else ".jpg"
    mime_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }
    if content_type in mime_map:
        return mime_map[content_type]
    raise HTTPException(400, "Csak jpg/png/webp/gif engedélyezett")


async def save_product_image(
    db: Session,
    product: Product,
    file: UploadFile,
    *,
    alt: str = "",
    set_primary: bool = False,
) -> ProductImage:
    ensure_upload_dirs()
    if file.content_type and file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, f"Nem támogatott MIME: {file.content_type}")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Üres fájl")
    if len(data) > MAX_BYTES:
        raise HTTPException(400, "Max 5 MB")

    ext = _safe_ext(file.filename or "", file.content_type)
    filename = f"{uuid.uuid4().hex}{ext}"
    dest_dir = UPLOAD_ROOT / str(product.id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    dest.write_bytes(data)

    url = public_url(product.id, filename)
    s3_url = None
    try:
        s3_url = upload_bytes_to_s3(
            f"products/{product.id}/{filename}",
            data,
            content_type=file.content_type or "application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception:
        # S3 hiba ne akadályozza a helyi mentést
        s3_url = None

    count = db.query(ProductImage).filter(ProductImage.product_id == product.id).count()
    is_primary = set_primary or count == 0

    if is_primary:
        for img in db.query(ProductImage).filter(ProductImage.product_id == product.id).all():
            img.is_primary = False
        product.image_url = s3_url or absolute_media_url(url)

    image = ProductImage(
        product_id=product.id,
        filename=filename,
        url=url,
        alt=alt.strip() or product.title,
        sort_order=(count + 1) * 10,
        is_primary=is_primary,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def set_primary_image(db: Session, product: Product, image: ProductImage) -> ProductImage:
    for img in db.query(ProductImage).filter(ProductImage.product_id == product.id).all():
        img.is_primary = img.id == image.id
    product.image_url = absolute_media_url(image.url)
    db.commit()
    db.refresh(image)
    return image


def delete_product_image(db: Session, product: Product, image: ProductImage) -> None:
    path = disk_path(product.id, image.filename)
    was_primary = image.is_primary
    db.delete(image)
    db.flush()
    if path.exists():
        path.unlink(missing_ok=True)
    if was_primary:
        nxt = (
            db.query(ProductImage)
            .filter(ProductImage.product_id == product.id)
            .order_by(ProductImage.sort_order, ProductImage.id)
            .first()
        )
        if nxt:
            nxt.is_primary = True
            product.image_url = absolute_media_url(nxt.url)
        else:
            # ha külső URL volt, ne töröljük vakon — csak feltöltött primary hiányában ürítjük, ha /media/
            if "/media/products/" in (product.image_url or ""):
                product.image_url = ""
    db.commit()


def absolute_or_path(url: str) -> str:
    """Storefronthez: abszolút vagy gyökér-relatív URL (CDN-aware)."""
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return absolute_media_url(url)