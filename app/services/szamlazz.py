"""Számlázz.hu Agent kliens — dry-run outbox, ha nincs Agent kulcs / disabled."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from xml.sax.saxutils import escape

import httpx
from sqlalchemy.orm import Session, joinedload

from app.config import BASE_DIR, settings
from app.models import Order
from app.services.vat import split_gross

logger = logging.getLogger(__name__)
OUTBOX = BASE_DIR / "data" / "szamlazz_outbox"
PDF_DIR = BASE_DIR / "data" / "szamlazz_pdf"


@dataclass
class SzamlazzResult:
    ok: bool
    invoice_number: str = ""
    dry_run: bool = False
    error: str = ""
    pdf_path: str = ""
    raw: str = ""


def _xml_text(value: str | float | int | None) -> str:
    if value is None:
        return ""
    return escape(str(value))


def _fizmod(order: Order) -> str:
    return {
        "prepaid": "Bankkártya",
        "cod": "Utánvét",
        "invoice": "Átutalás",
    }.get(order.payment_method or "", "Átutalás")


def build_invoice_xml(order: Order, *, agent_key: str, eszamla: bool, download_pdf: bool) -> str:
    """xmlszamla — mezősorrend a hivatalos XSD szerint (kötelező tagek)."""
    today = date.today().isoformat()
    rate = float(order.tax_rate_percent or 27.0)
    afakulcs = str(int(rate) if rate == int(rate) else rate)

    tetelek: list[str] = []
    for ln in order.lines or []:
        gross = float(ln.line_total or 0)
        net, tax, _ = split_gross(gross, rate)
        qty = float(ln.quantity or 1)
        unit_gross = gross / qty if qty else gross
        unit_net, _, _ = split_gross(unit_gross, rate)
        tetelek.append(
            f"""    <tetel>
      <megnevezes>{_xml_text(ln.product_title)}</megnevezes>
      <mennyiseg>{qty}</mennyiseg>
      <mennyisegiEgyseg>db</mennyisegiEgyseg>
      <nettoEgysegar>{unit_net:.2f}</nettoEgysegar>
      <afakulcs>{_xml_text(afakulcs)}</afakulcs>
      <nettoErtek>{net:.2f}</nettoErtek>
      <afaErtek>{tax:.2f}</afaErtek>
      <bruttoErtek>{gross:.2f}</bruttoErtek>
      <megjegyzes>{_xml_text(ln.sku or '')}</megjegyzes>
    </tetel>"""
        )

    if order.shipping_total and order.shipping_total > 0:
        sn, st, _ = split_gross(float(order.shipping_total), rate)
        tetelek.append(
            f"""    <tetel>
      <megnevezes>Szállítás</megnevezes>
      <mennyiseg>1.0</mennyiseg>
      <mennyisegiEgyseg>db</mennyisegiEgyseg>
      <nettoEgysegar>{sn:.2f}</nettoEgysegar>
      <afakulcs>{_xml_text(afakulcs)}</afakulcs>
      <nettoErtek>{sn:.2f}</nettoErtek>
      <afaErtek>{st:.2f}</afaErtek>
      <bruttoErtek>{float(order.shipping_total):.2f}</bruttoErtek>
      <megjegyzes></megjegyzes>
    </tetel>"""
        )

    if order.cod_fee_total and order.cod_fee_total > 0:
        cn, ct, _ = split_gross(float(order.cod_fee_total), rate)
        tetelek.append(
            f"""    <tetel>
      <megnevezes>Utánvét kezelési díj</megnevezes>
      <mennyiseg>1.0</mennyiseg>
      <mennyisegiEgyseg>db</mennyisegiEgyseg>
      <nettoEgysegar>{cn:.2f}</nettoEgysegar>
      <afakulcs>{_xml_text(afakulcs)}</afakulcs>
      <nettoErtek>{cn:.2f}</nettoErtek>
      <afaErtek>{ct:.2f}</afaErtek>
      <bruttoErtek>{float(order.cod_fee_total):.2f}</bruttoErtek>
      <megjegyzes></megjegyzes>
    </tetel>"""
        )

    if order.discount_total and order.discount_total > 0:
        dg = -abs(float(order.discount_total))
        dn, dt, _ = split_gross(abs(dg), rate)
        tetelek.append(
            f"""    <tetel>
      <megnevezes>Kedvezmény</megnevezes>
      <mennyiseg>1.0</mennyiseg>
      <mennyisegiEgyseg>db</mennyisegiEgyseg>
      <nettoEgysegar>{-dn:.2f}</nettoEgysegar>
      <afakulcs>{_xml_text(afakulcs)}</afakulcs>
      <nettoErtek>{-dn:.2f}</nettoErtek>
      <afaErtek>{-dt:.2f}</afaErtek>
      <bruttoErtek>{dg:.2f}</bruttoErtek>
      <megjegyzes>{_xml_text(order.coupon_code or '')}</megjegyzes>
    </tetel>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xmlszamla xmlns="http://www.szamlazz.hu/xmlszamla" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.szamlazz.hu/xmlszamla https://www.szamlazz.hu/szamla/docs/xsds/agent/xmlszamla.xsd">
  <beallitasok>
    <szamlaagentkulcs>{_xml_text(agent_key or 'DRY-RUN')}</szamlaagentkulcs>
    <eszamla>{"true" if eszamla else "false"}</eszamla>
    <szamlaLetoltes>{"true" if download_pdf else "false"}</szamlaLetoltes>
    <valaszVerzio>2</valaszVerzio>
    <aggregator></aggregator>
    <szamlaKulsoAzon>{_xml_text(order.order_number)}</szamlaKulsoAzon>
  </beallitasok>
  <fejlec>
    <keltDatum>{today}</keltDatum>
    <teljesitesDatum>{today}</teljesitesDatum>
    <fizetesiHataridoDatum>{today}</fizetesiHataridoDatum>
    <fizmod>{_xml_text(_fizmod(order))}</fizmod>
    <penznem>{_xml_text(order.currency or "HUF")}</penznem>
    <szamlaNyelve>hu</szamlaNyelve>
    <megjegyzes>{_xml_text(f"Whoopy rendelés {order.order_number}")}</megjegyzes>
    <arfolyamBank></arfolyamBank>
    <arfolyam>0</arfolyam>
    <rendelesSzam>{_xml_text(order.order_number)}</rendelesSzam>
    <dijbekeroSzamlaszam></dijbekeroSzamlaszam>
    <elolegszamla>false</elolegszamla>
    <vegszamla>false</vegszamla>
    <helyesbitoszamla>false</helyesbitoszamla>
    <helyesbitettSzamlaszam></helyesbitettSzamlaszam>
    <dijbekero>false</dijbekero>
    <szallislevel>false</szallislevel>
  </fejlec>
  <elado>
    <bank></bank>
    <bankszamlaszam></bankszamlaszam>
    <emailReplyto></emailReplyto>
    <emailTargy></emailTargy>
    <emailSzoveg></emailSzoveg>
  </elado>
  <vevo>
    <nev>{_xml_text(order.full_name)}</nev>
    <orszag>{_xml_text(order.country or "HU")}</orszag>
    <irsz>{_xml_text(order.zip_code)}</irsz>
    <telepules>{_xml_text(order.city)}</telepules>
    <cim>{_xml_text(order.address)}</cim>
    <email>{_xml_text(order.email)}</email>
    <sendEmail>true</sendEmail>
    <adoszam></adoszam>
    <postazasiNev></postazasiNev>
    <postazasiOrszag></postazasiOrszag>
    <postazasiIrsz></postazasiIrsz>
    <postazasiTelepules></postazasiTelepules>
    <postazasiCim></postazasiCim>
    <azonosito></azonosito>
    <telefonszam>{_xml_text(order.phone)}</telefonszam>
    <megjegyzes></megjegyzes>
  </vevo>
  <fuvarlevel>
    <uticel></uticel>
    <futarSzolgalat></futarSzolgalat>
  </fuvarlevel>
  <tetelek>
{chr(10).join(tetelek)}
  </tetelek>
</xmlszamla>
"""


def _parse_xml_response(body: str) -> SzamlazzResult:
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        if "DONE" in body.upper() or body.startswith("%PDF"):
            m = re.search(r"DONE[;:]?\s*([A-Z0-9\-]+)", body, re.I)
            return SzamlazzResult(ok=True, invoice_number=m.group(1) if m else "", raw=body[:500])
        return SzamlazzResult(ok=False, error=body[:400], raw=body[:500])

    def local(tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    data = {local(c.tag): (c.text or "") for c in root}
    success = (data.get("sikeres") or "").lower() == "true"
    if not success:
        return SzamlazzResult(
            ok=False,
            error=data.get("hibauzenet") or data.get("hiba") or body[:400],
            raw=body[:500],
        )
    return SzamlazzResult(
        ok=True,
        invoice_number=data.get("szamlaszam") or "",
        raw=body[:500],
    )


def issue_invoice(db: Session, order: Order, *, force: bool = False) -> SzamlazzResult:
    """Kiállít számlát Számlázz.hu-n, vagy dry-run XML-t ír az outboxba."""
    if not settings.szamlazz_enabled and not force:
        return SzamlazzResult(ok=False, error="SZAMLAZZ_ENABLED=false", dry_run=True)

    if order.invoice_status == "issued" and order.invoice_number and not force:
        return SzamlazzResult(ok=True, invoice_number=order.invoice_number)

    full = (
        db.query(Order)
        .options(joinedload(Order.lines), joinedload(Order.shipments))
        .filter(Order.id == order.id)
        .first()
    ) or order

    xml_body = build_invoice_xml(
        full,
        agent_key=settings.szamlazz_agent_key,
        eszamla=settings.szamlazz_eszamla,
        download_pdf=settings.szamlazz_download_pdf,
    )

    if not settings.szamlazz_agent_key.strip():
        OUTBOX.mkdir(parents=True, exist_ok=True)
        path = OUTBOX / f"{full.order_number}.xml"
        path.write_text(xml_body, encoding="utf-8")
        full.invoice_status = "skipped"
        full.invoice_provider = "szamlazz"
        full.invoice_error = f"dry-run outbox: {path.name}"
        db.commit()
        logger.info("Számlázz dry-run XML → %s", path)
        return SzamlazzResult(ok=True, dry_run=True, invoice_number="", raw=str(path))

    full.invoice_status = "pending"
    full.invoice_provider = "szamlazz"
    full.invoice_error = ""
    db.commit()

    try:
        with httpx.Client(timeout=settings.szamlazz_timeout_sec) as client:
            files = {
                "action-xmlagentxmlfile": ("invoice.xml", xml_body.encode("utf-8"), "application/xml"),
            }
            resp = client.post(settings.szamlazz_api_url, files=files)
            body = resp.text
            content_type = (resp.headers.get("content-type") or "").lower()

            if resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code}: {body[:300]}")

            if "pdf" in content_type or body.startswith("%PDF"):
                PDF_DIR.mkdir(parents=True, exist_ok=True)
                pdf_path = PDF_DIR / f"{full.order_number}.pdf"
                pdf_path.write_bytes(resp.content)
                inv_no = resp.headers.get("szlahu_szamlaszam") or ""
                full.invoice_status = "issued"
                full.invoice_number = inv_no
                full.invoice_pdf_path = str(pdf_path)
                full.invoice_error = ""
                db.commit()
                return SzamlazzResult(ok=True, invoice_number=inv_no, pdf_path=str(pdf_path))

            parsed = _parse_xml_response(body)
            if not parsed.ok:
                full.invoice_status = "failed"
                full.invoice_error = parsed.error[:512]
                db.commit()
                return parsed

            try:
                root = ET.fromstring(body)
                for el in root.iter():
                    if el.tag.endswith("pdf") and el.text:
                        import base64

                        PDF_DIR.mkdir(parents=True, exist_ok=True)
                        pdf_path = PDF_DIR / f"{full.order_number}.pdf"
                        pdf_path.write_bytes(base64.b64decode(el.text))
                        parsed.pdf_path = str(pdf_path)
                        full.invoice_pdf_path = str(pdf_path)
                        break
            except Exception:
                logger.exception("Számlázz PDF extract failed")

            full.invoice_status = "issued"
            full.invoice_number = parsed.invoice_number
            full.invoice_error = ""
            db.commit()
            return parsed
    except Exception as exc:
        logger.exception("Számlázz issue failed for %s", full.order_number)
        full.invoice_status = "failed"
        full.invoice_error = str(exc)[:512]
        db.commit()
        return SzamlazzResult(ok=False, error=str(exc)[:400])


def maybe_auto_invoice(db: Session, order: Order) -> SzamlazzResult | None:
    if not settings.szamlazz_enabled or not settings.szamlazz_auto_on_paid:
        return None
    return issue_invoice(db, order, force=False)
