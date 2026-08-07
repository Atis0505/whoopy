"""Whoopy.hu jogi / tájékoztató CMS szövegek (HU + EU távollévők közötti szerződés).

Ezek sablonok: a cégadatokat az admin Beállításokban kell kitölteni
({{company_name}}, adószám stb. a megjelenítéskor behelyettesül).
Jogász általi véglegesítés ajánlott éles indulás előtt.
"""

from __future__ import annotations

LEGAL_CONTENT_VERSION = 1

# Placeholderek a body-ban — cms_page render helyettesíti StoreSettings-ből:
# {{store_name}} {{company_name}} {{company_address}} {{company_tax_id}}
# {{company_eu_vat}} {{support_email}} {{support_phone}} {{business_hours}} {{domain}}


def _aszf() -> str:
    return """
<p class="muted"><em>Hatályos: 2026. Softveres sablon a Whoopy.hu webáruházhoz. A szolgáltató adatait az
<a href="/pages/impressum">Impresszum</a> és az admin beállítások tartalmazzák.</em></p>

<h2>1. Szolgáltató</h2>
<p>A webáruházat a <strong>{{company_name}}</strong> (a továbbiakban: <strong>Szolgáltató</strong>) üzemelteti.
Elérhetőségek: <a href="/pages/impressum">Impresszum</a>, e-mail: <a href="mailto:{{support_email}}">{{support_email}}</a>,
web: <strong>{{domain}}</strong>.</p>

<h2>2. Fogalmak</h2>
<ul>
  <li><strong>Fogyasztó:</strong> a Ptk. szerinti fogyasztó (természetes személy, aki szakmája, önálló
  foglalkozása vagy üzleti tevékenysége körén kívül jár el).</li>
  <li><strong>Vásárló / Megrendelő:</strong> aki a webáruházban rendelést ad le (fogyasztó vagy vállalkozás).</li>
  <li><strong>Termék:</strong> a katalógusban megjelölt áru.</li>
  <li><strong>Távollévők között kötött szerződés:</strong> a 45/2014. (II. 26.) Korm. rendelet hatálya alá tartozó
  online megrendelés.</li>
</ul>

<h2>3. A szerződés létrejötte</h2>
<ol>
  <li>A katalógusban szereplő termékek és árak ajánlati felhívásnak minősülnek; a rendelés leadásával a Vásárló
  tesz ajánlatot.</li>
  <li>A szerződés a rendelés visszaigazolásával (e-mail / fiók / rendelésoldal) jön létre, a visszaigazolt tartalommal.</li>
  <li>A rendelés leadása előtt a Vásárló köteles elfogadni a jelen ÁSZF-et és az adatvédelmi tájékoztatót.</li>
  <li>Nyelv: magyar. Irányadó jog: magyar jog, kötelező EU fogyasztóvédelmi szabályokkal.</li>
</ol>

<h2>4. Árak, ÁFA, fizetés</h2>
<ul>
  <li>Az árak bruttó forintban (HUF) jelennek meg, ha másképp nincs jelölve, és tartalmazzák a magyar ÁFA-t
  (általános kulcs 27%, eltérés termékoldalon).</li>
  <li>EU B2B vevő érvényes közösségi adószámmal a kosárban jelezheti a fordított ÁFA / mentesség igényét
  (ellenőrzés után).</li>
  <li>Fizetési módok: online bankkártya / SimplePay (vagy más kapu), utánvét (ahol elérhető), esetleg átutalás —
  a kosárban és a pénztárnál látható opciók szerint.</li>
  <li>Utánvét esetén a futárnál fizetendő összeg a rendelés végösszege + esetleges COD díj.</li>
  <li><strong>Omnibus / árkedvezmény:</strong> akció esetén a termékoldalon feltüntetjük a megelőző 30 nap
  legalacsonyabb árát is, ahol alkalmazandó.</li>
</ul>

<h2>5. Szállítás</h2>
<p>A szállítási díjak, átfutási idők és a lefedett országok a
<a href="/pages/szallitas">Szállítási tájékoztatóban</a> és a kosárban jelennek meg.
Több beszállítós rendelés esetén a csomagok külön is érkezhetnek.</p>

<h2>6. Teljesítés, késedelem, hibás teljesítés</h2>
<ul>
  <li>A Szolgáltató a visszaigazolt határidőn belül teljesít. Készlethiány vagy partnerkésedelem esetén
  e-mailben tájékoztatunk; a Fogyasztó elállhat vagy módosított teljesítést kérhet.</li>
  <li>Kellékszavatosság és jótállás: a Ptk. és a vonatkozó fogyasztóvédelmi szabályok szerint
  (pl. tartós fogyasztási cikkeknél kötelező jótállás, ahol alkalmazandó).</li>
  <li>Szavatossági / jótállási igény: <a href="mailto:{{support_email}}">{{support_email}}</a> vagy
  <a href="/contact">Kapcsolat</a>.</li>
</ul>

<h2>7. Elállás és visszaküldés</h2>
<p>Fogyasztó távollévők között kötött szerződés esetén a termék átvételétől számított
<strong>14 napon belül</strong> indokolás nélkül elállhat. Részletek, kivételek és mintaelállási nyilatkozat:
<a href="/pages/visszakuldes">Elállás és visszaküldés</a>. Online kérelem: <a href="/returns">/returns</a>.</p>

<h2>8. Panaszkezelés</h2>
<ol>
  <li>Írásbeli panasz: <a href="mailto:{{support_email}}">{{support_email}}</a> vagy <a href="/contact">Kapcsolat</a>.
  Célunk 30 napon belüli érdemi válasz.</li>
  <li>Fogyasztóvédelmi hatóság / békéltető testület: lásd <a href="/pages/impressum">Impresszum</a>.</li>
  <li>Online vitarendezés (ODR): az EU platformja —
  <a href="https://ec.europa.eu/consumers/odr" rel="noopener" target="_blank">ec.europa.eu/consumers/odr</a>.</li>
</ol>

<h2>9. Felelősség</h2>
<p>A Szolgáltató nem felel a Vásárló érdekkörében felmerült károkért (pl. hibás szállítási adatok),
vis maiorért, illetve a beszállító / futár önhibáján kívüli késedelméért a jogszabályi keretek között.
A kötelező fogyasztóvédelmi és szavatossági szabályok ettől nem sérülhetnek.</p>

<h2>10. Adatvédelem</h2>
<p>Személyes adatok kezelése: <a href="/pages/adatvedelem">Adatvédelmi tájékoztató</a> és
<a href="/pages/sutik">Cookie / süti tájékoztató</a>.</p>

<h2>11. Egyéb</h2>
<ul>
  <li>A Szolgáltató jogosult az ÁSZF egyoldalú módosítására; a hatályos szöveg mindig a weboldalon elérhető.
  Lényeges változásról a fiókban / e-mailben tájékoztathatunk.</li>
  <li>Részleges érvénytelenség esetén a többi rendelkezés hatályban marad.</li>
  <li>Kapcsolódó oldalak: <a href="/faq">GYIK</a>, <a href="/pages/rolunk">Rólunk</a>.</li>
</ul>
"""


def _adatvedelem() -> str:
    return """
<p class="muted"><em>GDPR (EU 2016/679) és az Infotv. szerinti tájékoztató. Adatkezelő: {{company_name}}.</em></p>

<h2>1. Adatkezelő</h2>
<p><strong>{{company_name}}</strong><br/>
Cím: {{company_address}}<br/>
E-mail: <a href="mailto:{{support_email}}">{{support_email}}</a><br/>
Telefon: {{support_phone}}<br/>
Ügyfélfogadás: {{business_hours}}</p>
<p>Adatvédelmi kapcsolattartó: ugyanaz az e-mail (külön DPO hiányában).</p>

<h2>2. Milyen adatokat kezelünk?</h2>
<table>
  <thead><tr><th>Cél</th><th>Adatok</th><th>Jogalap</th><th>Megőrzés</th></tr></thead>
  <tbody>
    <tr>
      <td>Rendelés teljesítése, számla</td>
      <td>Név, e-mail, telefon, szállítási/számlázási cím, adószám (B2B), rendelés tartalma</td>
      <td>Szerződés teljesítése (GDPR 6. cikk (1) b); számviteli kötelezettség (c)</td>
      <td>Számviteli bizonylatok: jogszabály szerint (tipikusan 8 év)</td>
    </tr>
    <tr>
      <td>Fiók, ügyfélszolgálat</td>
      <td>Regisztrációs adatok, üzenetek, visszaküldési kérelmek</td>
      <td>Szerződés / jogos érdek / hozzájárulás</td>
      <td>Fiók fennállásáig + panasz / elévülés</td>
    </tr>
    <tr>
      <td>Hírlevél</td>
      <td>E-mail, nyelv, feliratkozás forrása</td>
      <td>Hozzájárulás (leiratkozás bármikor)</td>
      <td>Visszavonásig</td>
    </tr>
    <tr>
      <td>Webáruház működés (kosár, belépés)</td>
      <td>Munkamenet, cookie azonosítók</td>
      <td>Jogos érdek / szerződés; opcionális cookie: hozzájárulás</td>
      <td>Lásd <a href="/pages/sutik">Süti tájékoztató</a></td>
    </tr>
    <tr>
      <td>Analitika / marketing (ha engedélyezed)</td>
      <td>Consent Mode szerinti mérési adatok</td>
      <td>Hozzájárulás</td>
      <td>Hozzájárulás visszavonásáig / szolgáltatói szabály szerint</td>
    </tr>
  </tbody>
</table>

<h2>3. Címzettek</h2>
<ul>
  <li>Futárszolgálatok / logisztikai partnerek (szállítás)</li>
  <li>Fizetési szolgáltatók (pl. SimplePay / bank)</li>
  <li>Számlázó / könyvelési rendszerek (pl. Számlázz.hu, ha bekapcsolva)</li>
  <li>Tárhely / IT üzemeltetés</li>
  <li>Hatóságok — csak jogszabályi kötelezettség esetén</li>
</ul>
<p>Harmadik országba történő adattovábbítás csak megfelelő garanciák mellett történik (ha egyáltalán).</p>

<h2>4. Az érintett jogai</h2>
<p>Jogod van a hozzáféréshez, helyesbítéshez, törléshez („elfeledtetés”), korlátozáshoz, adathordozhatósághoz,
tiltakozáshoz, valamint a hozzájárulás visszavonásához. Fiókban:</p>
<ul>
  <li><strong>Adat-export:</strong> <a href="/account">Fiók</a> → GDPR export (JSON)</li>
  <li><strong>Törlés / anonimizálás:</strong> fiók törlése megerősítéssel (<code>TORLES</code>)</li>
</ul>
<p>Panasz: Nemzeti Adatvédelmi és Információszabadság Hatóság (NAIH) —
<a href="https://www.naih.hu" rel="noopener" target="_blank">naih.hu</a>.</p>

<h2>5. Cookie-k</h2>
<p>Részletesen: <a href="/pages/sutik">Süti / cookie tájékoztató</a>. A bannerben választhatsz
szükséges / analitika / marketing kategóriákat.</p>

<h2>6. Biztonság</h2>
<p>Igyekszünk megfelelő technikai és szervezési intézkedésekkel védeni az adatokat (HTTPS éles környezetben,
hozzáférés-korlátozás, jelszó hash). Teljes biztonságot egyetlen online szolgáltatás sem garantálhat.</p>

<h2>7. Módosítások</h2>
<p>A tájékoztatót időnként frissíthetjük; a hatályos változat mindig ezen az oldalon érhető el.</p>
"""


def _impressum() -> str:
    return """
<h2>Szolgáltató / üzemeltető</h2>
<p>
  <strong>{{company_name}}</strong><br/>
  Székhely / levelezési cím: {{company_address}}<br/>
  Adószám: {{company_tax_id}}<br/>
  Közösségi adószám (EU ÁFA): {{company_eu_vat}}<br/>
  E-mail: <a href="mailto:{{support_email}}">{{support_email}}</a><br/>
  Telefon: {{support_phone}}<br/>
  Web: https://{{domain}}<br/>
  Ügyfélszolgálat: {{business_hours}}
</p>
<p class="muted">Ha valamely mező még üres, kérjük töltsd ki az admin <strong>Beállítások</strong> menüpontban
(cégnév, cím, adószám) — éles indulás előtt kötelező.</p>

<h2>Tárhelyszolgáltató</h2>
<p>A webáruház tárhelyét / hosztingját a Szolgáltató aktuális infrastruktúra-partnere biztosítja
(részletek kérésre: {{support_email}}).</p>

<h2>Fogyasztóvédelem és vitarendezés</h2>
<ul>
  <li><strong>Budapesti Békéltető Testület</strong> (ha a fogyasztó budapesti / a Szolgáltató budapesti):
    1016 Budapest, Krisztina krt. 99. ·
    <a href="https://bekeltet.bkik.hu" rel="noopener" target="_blank">bekeltet.bkik.hu</a></li>
  <li>Más megyei / fővárosi kereskedelmi és iparkamara mellett működő békéltető testületek listája:
    <a href="https://www.bekeltetes.hu" rel="noopener" target="_blank">bekeltetes.hu</a></li>
  <li><strong>Fogyasztóvédelmi hatóság:</strong> kormányhivatalok fogyasztóvédelmi szervei —
    <a href="https://www.kormanyhivatalok.hu" rel="noopener" target="_blank">kormanyhivatalok.hu</a></li>
  <li><strong>EU online vitarendezés (ODR):</strong>
    <a href="https://ec.europa.eu/consumers/odr" rel="noopener" target="_blank">ec.europa.eu/consumers/odr</a></li>
  <li><strong>NAIH</strong> (adatvédelem): <a href="https://www.naih.hu" rel="noopener" target="_blank">naih.hu</a></li>
</ul>

<h2>Jogi dokumentumok</h2>
<p>
  <a href="/pages/aszf">ÁSZF</a> ·
  <a href="/pages/adatvedelem">Adatvédelem</a> ·
  <a href="/pages/sutik">Sütik</a> ·
  <a href="/pages/szallitas">Szállítás</a> ·
  <a href="/pages/visszakuldes">Elállás</a> ·
  <a href="/pages/rolunk">Rólunk</a>
</p>
"""


def _szallitas() -> str:
    return """
<p>{{store_name}} az Európai Unióba (kiemelten Magyarországra) szállít. A pontos díj és átfutási idő
a kosárban, a választott szállítási módtól és a beszállító(k)tól függ.</p>

<h2>Átfutási idők (tájékoztató)</h2>
<ul>
  <li><strong>Magyarország:</strong> tipikusan 1–3 munkanap a feladástól (készlettől / partnertől függően).</li>
  <li><strong>EU más ország:</strong> tipikusan 3–7 munkanap.</li>
  <li>A termékoldalon ajánlatonként látható lead time tájékoztató jellegű.</li>
</ul>

<h2>Díjak</h2>
<ul>
  <li>Szállítási költség a kosár / pénztár összesítőjében jelenik meg.</li>
  <li>Ingyenes szállítás kampány / küszöb esetén a boltban jelezzük (pl. hirdetőszalag).</li>
  <li>Csomagpont / átvételi pont: a választott pont címére szállítunk; a díj a kosárban látszik.</li>
  <li>Utánvét: ahol elérhető, COD díj felszámítható.</li>
</ul>

<h2>Több csomag</h2>
<p>Több beszállítós rendelésnél a termékek külön csomagokban, eltérő időpontban is érkezhetnek.
Minden csomaghoz külön nyomkövetés tartozhat — lásd <a href="/track">Rendeléskövetés</a>.</p>

<h2>Átvétel</h2>
<p>Kérjük, átvételkor ellenőrizd a csomag sértetlenségét. Látható sérülés esetén jegyzőkönyv / fotó
javasolt, és jelezd nekünk: <a href="mailto:{{support_email}}">{{support_email}}</a>.</p>

<p>Kapcsolódó: <a href="/pages/visszakuldes">Elállás és visszaküldés</a> · <a href="/faq">GYIK</a>.</p>
"""


def _visszakuldes() -> str:
    return """
<p>Ez a tájékoztató a <strong>45/2014. (II. 26.) Korm. rendelet</strong> és az EU fogyasztói jogok irányelve
szerinti elállási jogról szól. Csak <strong>fogyasztói</strong> (nem vállalkozási) vásárlásokra vonatkozik
a törvényi 14 napos elállás.</p>

<h2>14 napos elállási jog</h2>
<ol>
  <li>A Fogyasztó a termék <strong>átvételétől</strong> számított 14 napon belül indokolás nélkül elállhat
  a szerződéstől.</li>
  <li>Az elállási nyilatkozatot e határidőn belül meg kell tenni (elég, ha elküldöd; nem kell, hogy
  a csomag is megérkezzen 14 napon belül).</li>
  <li>Online kérelem: <a href="/returns">Visszaküldés / elállás űrlap</a>.</li>
  <li>E-mail: <a href="mailto:{{support_email}}">{{support_email}}</a> — tárgy: „Elállás”, rendelésszám megadásával.</li>
</ol>

<h2>Visszaküldés és költségek</h2>
<ul>
  <li>Az elállás után a terméket indokolatlan késedelem nélkül, de legkésőbb 14 napon belül vissza kell juttatni.</li>
  <li>A visszaküldés közvetlen költségét — ha jogszabály másképp nem rendelkezik — a Fogyasztó viseli
    (kivéve, ha a Szolgáltató vállalta, vagy hibás teljesítés miatt történik a visszavétel).</li>
  <li>A vételár visszatérítése: az elállás közlésétől / a termék visszaérkezésétől / a feladás igazolásától
    számított 14 napon belül (a törvényi szabályok szerint), az eredeti fizetési móddal egyenértékűen.</li>
  <li>Csökkenthető a visszatérítés, ha a termék értékcsökkenése a jellegének, tulajdonságainak és működésének
    megállapításához szükséges használaton túlmutató kezelésből ered.</li>
</ul>

<h2>Mikor nincs elállási jog? (példák)</h2>
<ul>
  <li>Olyan nem előre gyártott termék, amelyet a fogyasztó utasítása alapján állítottak elő, vagy egyértelműen
    személyre szabtak.</li>
  <li>Romlandó vagy minőségét rövid ideig megőrző termék.</li>
  <li>Olyan zárt csomagolású termék, amely egészségvédelmi / higiéniai okból a csomagolás felbontása után
    nem küldhető vissza.</li>
  <li>Olyan termék, amely jellegénél fogva az átadást követően elválaszthatatlanul vegyül más termékkel.</li>
  <li>Hang-, illetve képmásolat, illetve számítógépes szoftver, ha a fogyasztó a csomagolást felbontotta
    (jogszabályi feltételek szerint).</li>
  <li>Egyéb, a Korm. rendeletben felsorolt kivételek.</li>
</ul>
<p>Vállalkozások (B2B) esetén a törvényi 14 napos elállás nem kötelező; egyedi megállapodás / szavatosság
szerint járunk el.</p>

<h2>Minta elállási nyilatkozat</h2>
<pre style="white-space:pre-wrap;background:var(--bg-soft,#f6f6f6);padding:1rem;border-radius:8px;font-size:0.9rem">
Címzett: {{company_name}}, {{company_address}}, {{support_email}}

Alulírott kijelentem, hogy gyakorlom elállási jogomat az alábbi szerződés tekintetében:
Rendelésszám: …………………………
Termék(ek): …………………………
Megrendelés / átvétel dátuma: …………………………
Fogyasztó neve: …………………………
Fogyasztó címe: …………………………
Dátum: …………………………
Aláírás (csak papír alapon): …………………………
</pre>

<p>Szavatossági / jótállási ügyekben is írj a <a href="/contact">Kapcsolat</a> űrlapon.
ÁSZF: <a href="/pages/aszf">/pages/aszf</a>.</p>
"""


def _rolunk() -> str:
    return """
<p><strong>{{store_name}}</strong> egy <strong>családi vállalkozás</strong>: munka mellett építjük és bővítjük
a webáruházat, hogy átlátható áron, gondosan válogatott termékeket kínáljunk Magyarországon és az EU-ban.</p>

<p>Nem egy nagy multinacionális gépezet vagyunk — ezért néha egy válasz vagy egy csomag egy kicsit több
türelmet kér, cserébe személyesebb ügyintézést és folyamatos fejlesztést kapsz. A katalógust fokozatosan
növeljük; a célunk, hogy a mindennapi és a ritkább holmik is egy helyen megtalálhatók legyenek.</p>

<h2>Miért Whoopy?</h2>
<ul>
  <li>Több forrásból / partnertől összeálló kínálat, egységes boltélménnyel</li>
  <li>Átlátható árak, ÁFA-s számla, EU-s fogyasztói jogok (elállás, adatvédelem)</li>
  <li>Folyamatos fejlesztés: jobb keresés, kategóriák, szállítás és ügyfélszolgálat</li>
</ul>

<h2>Kapcsolat</h2>
<p>Írj nekünk bátran: <a href="/contact">Kapcsolat űrlap</a> vagy
<a href="mailto:{{support_email}}">{{support_email}}</a> · ügyfélszolgálat: {{business_hours}}.</p>
<p>Cégadatok: <a href="/pages/impressum">Impresszum</a>.</p>
"""


def _sutik() -> str:
    return """
<p>Ez a tájékoztató a {{store_name}} (<strong>{{domain}}</strong>) által használt sütikről (cookie-król) szól,
az ePrivacy irányelv és a GDPR elvei szerint.</p>

<h2>Mi az a süti?</h2>
<p>A süti egy kis adatfájl, amelyet a böngésződ tárol. Segít a bejelentkezésben, a kosár megőrzésében,
és — ha engedélyezed — a látogatottság mérésében vagy marketingben.</p>

<h2>Kategóriák</h2>
<table>
  <thead><tr><th>Kategória</th><th>Példa</th><th>Jogalap</th></tr></thead>
  <tbody>
    <tr>
      <td><strong>Szükséges</strong></td>
      <td>Munkamenet, kosár, belépés, biztonság, cookie-preferencia</td>
      <td>Szerződés / jogos érdek — ezek nélkül a bolt nem működik</td>
    </tr>
    <tr>
      <td><strong>Analitika</strong></td>
      <td>Látogatottsági / teljesítmény-mérés (ha bekapcsolod)</td>
      <td>Hozzájárulás</td>
    </tr>
    <tr>
      <td><strong>Marketing</strong></td>
      <td>Hirdetési / remarketing azonosítók (ha bekapcsolod)</td>
      <td>Hozzájárulás</td>
    </tr>
  </tbody>
</table>

<h2>Hogyan állíthatod be?</h2>
<p>Az első látogatáskor megjelenő cookie-bannerben választhatsz: „Csak szükséges”, egyedi kijelölés,
vagy „Összes elfogadása”. A preferencia a munkamenetben / böngészőben tárolódik.
Részletes adatkezelés: <a href="/pages/adatvedelem">Adatvédelmi tájékoztató</a>.</p>

<p>Böngésződből is törölheted / blokkolhatod a sütiket — ekkor egyes funkciók (pl. kosár) korlátozottan
működhetnek.</p>
"""


def default_legal_pages() -> list[tuple[str, str, str]]:
    """(slug, title, html_body) — body a verziójel nélkül; azt a sync adja hozzá."""
    return [
        ("aszf", "Általános szerződési feltételek", _aszf()),
        ("adatvedelem", "Adatvédelmi tájékoztató", _adatvedelem()),
        ("impressum", "Impresszum", _impressum()),
        ("szallitas", "Szállítási tájékoztató", _szallitas()),
        ("visszakuldes", "Elállás és visszaküldés", _visszakuldes()),
        ("rolunk", "Rólunk", _rolunk()),
        ("sutik", "Süti / cookie tájékoztató", _sutik()),
    ]
