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

    for tr in soup.find_all("tr"):
        row_text = tr.get_text(" ", strip=True)
        if not row_mentions_club(row_text):
            continue

        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        celdas = [clean(td.get_text(" ", strip=True)) for td in tds]

        if len(celdas) >= 5 and ("VS" in celdas[0].upper() or " - " in celdas[0]):
            equipos_txt = celdas[0]
            marcador_txt = celdas[1]
            fecha_txt = celdas[2]
            # Mejorar captura de fecha si está vacía
            if not fecha_txt or fecha_txt.strip() == "":
                if len(celdas) > 3:
                    fecha_txt = celdas[3]
                else:
                    fecha_txt = "Fecha no disponible"
            lugar_txt = celdas[3] if len(celdas) > 3 else ""
            estado_txt = celdas[4] if len(celdas) > 4 else ""

            local, visitante = parse_equipos_cell(equipos_txt)
            resultado = normalize_score(marcador_txt)

            if not resultado and estado_txt:
                resultado = estado_txt.upper()

            matches.append({
                "fecha_texto": fecha_txt,
                "local": local,
                "visitante": visitante,
                "resultado": resultado,
                "lugar": lugar_txt,
                "estado": estado_txt
            })
        else:
            fecha_txt = celdas[0]
            local_txt = celdas[1]
            visitante_txt = celdas[2]
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

    with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
        json.dump({"matches": matches}, f, ensure_ascii=False)

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "X-WR-CALNAME:" + cat["name"]]
    for m in matches:
        try:
            if not m.get("fecha_texto"):
                continue
            dt = datetime.strptime(m["fecha_texto"].replace(" | ", " "), "%d/%m/%Y %H:%M")
        except Exception:
            continue
        summary = f'{m["local"]} vs {m["visitante"]}'.strip()
        lines += [
            "BEGIN:VEVENT",
            f"SUMMARY:{summary}",
            f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{(dt + timedelta(minutes=90)).strftime('%Y%m%dT%H%M%S')}",
            f"LOCATION:{m.get('lugar','')}",
            "END:VEVENT"
        ]
    lines.append("END:VCALENDAR")
    with open(f"{slug}/calendar.ics", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        cats = json.load(f)
    for cat in cats:
        scrape_categoria(cat)

if __name__ == "__main__":
    main()
