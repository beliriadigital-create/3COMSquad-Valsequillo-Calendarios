# scraper.py
import json
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

# CONFIG
CLUB_KEYS = ["3com", "valsequillo"]
USER_AGENT = "Mozilla/5.0 (compatible; 3COM-scraper/1.0)"
TIMEOUT = 30

def log(*args):
    print("[scraper]", *args)

def clean(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\xa0", " ")
    s = " ".join(s.split())
    s = re.sub(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", r"\1 | \2", s)
    return s.strip()

def is_score(s: str) -> bool:
    s = clean(s)
    return bool(re.fullmatch(r"\d+\s*-\s*\d+", s))

def normalize_score(s: str) -> str:
    s = clean(s)
    if not is_score(s):
        return ""
    return re.sub(r"\s*-\s*", "-", s)

def row_mentions_club(text: str) -> bool:
    t = clean(text).lower()
    return any(k in t for k in CLUB_KEYS)

def parse_equipos_cell(txt: str):
    t = clean(txt)
    t = re.sub(r"^\s*VS\s+", "", t, flags=re.I).strip()
    if " - " in t:
        a, b = t.split(" - ", 1)
    elif " - " in t:
        a, b = t.split("-", 1)
    elif "-" in t:
        a, b = t.split("-", 1)
    else:
        return (t, "")
    return (clean(a).strip(","), clean(b).strip(","))

def try_parse_table(soup):
    matches = []
    tables = soup.find_all("table")
    for table in tables:
        for tr in table.find_all("tr"):
            row_text = tr.get_text(" ", strip=True)
            if not row_mentions_club(row_text):
                continue
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            celdas = [clean(td.get_text(" ", strip=True)) for td in tds]

            # Heurísticas:
            # - Si la primera celda contiene "VS" -> formato equipos/marcador/fecha/lugar/estado
            # - Si la primera celda tiene fecha dd/mm/yyyy -> otro formato
            first = celdas[0].upper()
            if ("VS" in first or " - " in celdas[0] or "-" in celdas[0]) and len(celdas) >= 4:
                equipos_txt = celdas[0]
                marcador_txt = celdas[1] if len(celdas) > 1 else ""
                fecha_txt = celdas[2] if len(celdas) > 2 else ""
                # mejora: si fecha está vacía, intentar celdas[3]
                if not fecha_txt and len(celdas) > 3:
                    # puede ser que lugar esté en celdas[2] y fecha en celdas[3]
                    posible = celdas[3]
                    if re.search(r"\d{2}/\d{2}/\d{4}", posible):
                        fecha_txt = posible
                lugar_txt = celdas[3] if len(celdas) > 3 else ""
                estado_txt = celdas[4] if len(celdas) > 4 else ""

                local, visitante = parse_equipos_cell(equipos_txt)
                resultado = normalize_score(marcador_txt)
                if not resultado and estado_txt:
                    resultado = estado_txt.upper()

                matches.append({
                    "fecha_texto": fecha_txt or "",
                    "local": local,
                    "visitante": visitante,
                    "resultado": resultado,
                    "lugar": lugar_txt,
                    "estado": estado_txt
                })
            else:
                # intento por posiciones: fecha/local/visitante/resultado/(lugar)
                fecha_txt = celdas[0] if re.search(r"\d{2}/\d{2}/\d{4}", celdas[0]) else ""
                if fecha_txt:
                    local_txt = celdas[1] if len(celdas) > 1 else ""
                    visitante_txt = celdas[2] if len(celdas) > 2 else ""
                    resultado_txt = celdas[3] if len(celdas) > 3 else ""
                    lugar_txt = celdas[4] if len(celdas) > 4 else ""
                    resultado = normalize_score(resultado_txt) or resultado_txt
                    matches.append({
                        "fecha_texto": fecha_txt,
                        "local": local_txt,
                        "visitante": visitante_txt,
                        "resultado": resultado,
                        "lugar": lugar_txt,
                        "estado": ""
                    })
    return matches

def find_ics_link(soup, base_url):
    # Busca enlaces directos a .ics o links que contengan 'calendar' o 'ical'
    for a in soup.find_all("a", href=True):
        href = a['href']
        if '.ics' in href.lower() or 'ical' in href.lower() or 'calendar' in href.lower():
            return urljoin(base_url, href)
    # también buscar imagen QR con data-... (a veces es <a download>)
    return None

def parse_ics_text(ics_text):
    # Parse minimal de VEVENTs para SUMMARY, DTSTART, LOCATION
    events = []
    vevents = re.split(r"END:VEVENT", ics_text, flags=re.I)
    for v in vevents:
        if "BEGIN:VEVENT" not in v:
            continue
        summary = re.search(r"SUMMARY:(.*)", v)
        dtstart = re.search(r"DTSTART(?:;[^:]+)?:([0-9T]+)", v)
        location = re.search(r"LOCATION:(.*)", v)
        s = summary.group(1).strip() if summary else ""
        d = dtstart.group(1).strip() if dtstart else ""
        loc = location.group(1).strip() if location else ""
        # intentar parsear d tipo YYYYMMDDTHHMMSS o YYYYMMDD
        fecha_texto = ""
        try:
            if len(d) >= 15:  # con hora
                dt = datetime.strptime(d[:15], "%Y%m%dT%H%M%S")
                fecha_texto = dt.strftime("%d/%m/%Y | %H:%M")
            elif len(d) >= 8:
                dt = datetime.strptime(d[:8], "%Y%m%d")
                fecha_texto = dt.strftime("%d/%m/%Y | 00:00")
        except:
            fecha_texto = ""

        # intentar split summary en "Local vs Visitante"
        local = ""
        visitante = ""
        if " vs " in s.lower():
            parts = re.split(r"\s+vs\.?\s+|\s+-\s+", s, flags=re.I)
            if len(parts) >= 2:
                local = parts[0].strip()
                visitante = parts[1].strip()
        elif "-" in s:
            parts = s.split("-", 1)
            local = parts[0].strip()
            visitante = parts[1].strip()
        else:
            local = s

        events.append({
            "fecha_texto": fecha_texto,
            "local": local,
            "visitante": visitante,
            "resultado": "",
            "lugar": loc,
            "estado": ""
        })
    return events

def try_find_json_in_scripts(soup):
    # busca trozos de JSON en <script> que contengan 'fecha' o 'partidos'
    for script in soup.find_all("script"):
        txt = script.string
        if not txt:
            continue
        if 'partidos' in txt.lower() or 'fecha' in txt.lower():
            # intentar extraer JSON array con regex
            m = re.search(r"(\[{\s*\"fecha_texto\".*?\}])", txt, flags=re.S)
            if m:
                try:
                    arr = json.loads(m.group(1))
                    return arr
                except:
                    continue
            # buscar cualquier array de objetos
            m2 = re.search(r"(\[{\s*.+\}\])", txt, flags=re.S)
            if m2:
                try:
                    arr = json.loads(m2.group(1))
                    return arr
                except:
                    continue
    return None

def scrape_categoria(cat):
    slug = cat["slug"]
    url = cat.get("url")
    if not url:
        log("No URL for", slug)
        return

    os.makedirs(slug, exist_ok=True)
    headers = {"User-Agent": USER_AGENT}
    log("Fetching", url)
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=headers)
        r.encoding = 'utf-8'
    except Exception as e:
        log("Error fetching", url, e)
        return

    soup = BeautifulSoup(r.text, "html.parser")
    matches = []

    # 1) Intento principal: tablas
    matches = try_parse_table(soup)
    log(f"After table parse: found {len(matches)} matches")

    # 2) Si nada, buscar .ics y parsear
    if not matches:
        ics_link = find_ics_link(soup, url)
        if ics_link:
            log("Found ICS link:", ics_link)
            try:
                r2 = requests.get(ics_link, timeout=TIMEOUT, headers=headers)
                events = parse_ics_text(r2.text)
                if events:
                    matches = events
                    log("Parsed", len(events), "events from ICS")
            except Exception as e:
                log("Error fetching/parsing ICS", e)

    # 3) Si nada, buscar JSON en scripts
    if not matches:
        arr = try_find_json_in_scripts(soup)
        if arr:
            log("Found JSON in scripts, length:", len(arr))
            # intentar mapear campos comunes
            parsed = []
            for item in arr:
                fecha = item.get("fecha_texto") or item.get("fecha") or ""
                local = item.get("local") or item.get("home") or item.get("equipo_local") or ""
                visitante = item.get("visitante") or item.get("away") or item.get("equipo_visitante") or ""
                lugar = item.get("lugar") or item.get("sede") or ""
                resultado = item.get("resultado") or item.get("score") or ""
                parsed.append({
                    "fecha_texto": clean(fecha),
                    "local": clean(local),
                    "visitante": clean(visitante),
                    "resultado": normalize_score(resultado) or clean(resultado),
                    "lugar": clean(lugar),
                    "estado": ""
                })
            matches = parsed

    # 4) último intento: buscar líneas libres que mencionen el club
    if not matches:
        for line in r.text.splitlines():
            if row_mentions_club(line):
                sline = clean(BeautifulSoup(line, "html.parser").get_text(" ", strip=True))
                # intentar sacar equipos/fecha con regex
                if re.search(r"\d{2}/\d{2}/\d{4}", sline):
                    # heurística simple
                    fecha_m = re.search(r"(\d{2}/\d{2}/\d{4}(?:\s*\|\s*\d{2}:\d{2})?)", sline)
                    fecha_txt = fecha_m.group(1) if fecha_m else ""
                    # intentar equipos
                    equipos_m = re.search(r"([A-Z0-9 \.\-ÑÁÉÍÓÚ]+)\s+(VS|vs|\-)\s+([A-Z0-9 \.\-ÑÁÉÍÓÚ]+)", sline)
                    if equipos_m:
                        local = equipos_m.group(1).strip()
                        visitante = equipos_m.group(3).strip()
                        matches.append({
                            "fecha_texto": fecha_txt,
                            "local": local,
                            "visitante": visitante,
                            "resultado": "",
                            "lugar": "",
                            "estado": ""
                        })

    log(f"Total matches for {slug}: {len(matches)}")

    # Guardar partidos.json
    with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
        json.dump({"categoria": cat.get("name", slug), "matches": matches}, f, ensure_ascii=False, indent=2)

    # Generar ICS si hay fechas parseables
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "X-WR-CALNAME:" + cat.get("name", slug)]
    for m in matches:
        try:
            if not m.get("fecha_texto"):
                continue
            raw = m["fecha_texto"].replace(" | ", " ").replace("|", " ")
            # buscar dd/mm/yyyy HH:MM o solo dd/mm/yyyy
            dt = None
            mdt = re.search(r"(\d{2}/\d{2}/\d{4})\s*(?:\|\s*)?(\d{2}:\d{2})?", raw)
            if mdt:
                dpart = mdt.group(1)
                tpart = mdt.group(2) or "00:00"
                dt = datetime.strptime(f"{dpart} {tpart}", "%d/%m/%Y %H:%M")
            if not dt:
                continue
            summary = f'{m.get("local","").strip()} vs {m.get("visitante","").strip()}'.strip()
            lines += [
                "BEGIN:VEVENT",
                f"SUMMARY:{summary}",
                f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{(dt + timedelta(minutes=90)).strftime('%Y%m%dT%H%M%S')}",
                f"LOCATION:{m.get('lugar','')}",
                "END:VEVENT"
            ]
        except Exception as e:
            log("Error building ICS event", e)
    lines.append("END:VCALENDAR")
    with open(f"{slug}/calendar.ics", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log("Saved", f"{slug}/partidos.json and {slug}/calendar.ics")

def main():
    try:
        with open("categories.json", "r", encoding="utf-8") as f:
            cats = json.load(f)
    except Exception as e:
        log("Cannot read categories.json:", e)
        return

    for cat in cats:
        try:
            scrape_categoria(cat)
        except Exception as e:
            log("Error scraping", cat.get("slug"), e)

if __name__ == "__main__":
    main()
