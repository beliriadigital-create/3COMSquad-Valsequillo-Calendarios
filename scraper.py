import json, os, re, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

CLUB_KEYS = ["3com", "valsequillo"]

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
    elif "-" in t:
        a, b = t.split("-", 1)
    else:
        return (t, "")
    return (clean(a).strip(","), clean(b).strip(","))

def scrape_categoria(cat):
    slug = cat["slug"]
    os.makedirs(slug, exist_ok=True)
    matches = []

    r = requests.get(cat["url"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    # Buscamos la tabla principal de partidos
    table = soup.find("table", {"class": "table table-striped table-hover"})
    if not table:
        print(f"No se encontró tabla en {slug}")
        return

    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue
        row_text = tr.get_text(" ", strip=True)
        if not row_mentions_club(row_text):
            continue

        # Columnas según inspección:
        # 0: Equipos (local - visitante)
        # 1: Resultado
        # 2: Fecha
        # 3: Hora
        # 4: Lugar

        equipos_txt = clean(tds[0].get_text(" ", strip=True))
        resultado_txt = clean(tds[1].get_text(" ", strip=True))
        fecha_txt = clean(tds[2].get_text(" ", strip=True))
        hora_txt = clean(tds[3].get_text(" ", strip=True))
        lugar_txt = clean(tds[4].get_text(" ", strip=True))

        local, visitante = parse_equipos_cell(equipos_txt)
        resultado = normalize_score(resultado_txt)

        fecha_completa = fecha_txt
        if hora_txt:
            fecha_completa += " | " + hora_txt

        matches.append({
            "fecha_texto": fecha_completa,
            "local": local,
            "visitante": visitante,
            "resultado": resultado or resultado_txt,
            "lugar": lugar_txt,
            "estado": ""
        })

    with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
        json.dump({"categoria": cat.get("name", slug), "matches": matches}, f, ensure_ascii=False, indent=2)

    # Generar ICS
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "X-WR-CALNAME:" + cat.get("name", slug)]
    for m in matches:
        try:
            if not m.get("fecha_texto"):
                continue
            raw = m["fecha_texto"].replace(" | ", " ").replace("|", " ")
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
            print("Error generando evento ICS:", e)
    lines.append("END:VCALENDAR")
    with open(f"{slug}/calendar.ics", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Guardado {slug}/partidos.json y {slug}/calendar.ics")

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        cats = json.load(f)
    for cat in cats:
        scrape_categoria(cat)

if __name__ == "__main__":
    main()
