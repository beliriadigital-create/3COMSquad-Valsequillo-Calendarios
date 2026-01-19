import json, os, re, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

CLUB_KEYS = ["3com", "valsequillo"]  # filtro flexible

def clean(s: str) -> str:
    if not s:
        return ""
    s = " ".join(s.replace("\xa0", " ").split())
    # separa fecha y hora: 24/01/2026  11:00  -> 24/01/2026 | 11:00
    s = re.sub(r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2})", r"\1 | \2", s)
    return s.strip()

def is_score(s: str) -> bool:
    s = clean(s)
    return bool(re.fullmatch(r"\d+\s*-\s*\d+", s))

def parse_equipos_cell(txt: str):
    """
    Celda EQUIPOS suele venir como: 'VS  3COM ...  - ROMADE'
    Devuelve (local, visitante) ya limpios.
    """
    t = clean(txt)
    t = re.sub(r"^\s*VS\s+", "", t, flags=re.I).strip()
    # separar por " - " (con espacios). Si no, intenta con "-"
    if " - " in t:
        a, b = t.split(" - ", 1)
    elif "-" in t:
        a, b = t.split("-", 1)
    else:
        return (t, "")
    return (clean(a).strip(","), clean(b).strip(","))

def row_mentions_club(text: str) -> bool:
    t = clean(text).lower()
    return any(k in t for k in CLUB_KEYS)

def scrape_categoria(cat):
    slug = cat["slug"]
    os.makedirs(slug, exist_ok=True)
    matches = []

    r = requests.get(cat["url"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    # Buscar tablas y procesar filas que contengan al club
    for tr in soup.find_all("tr"):
        if not row_mentions_club(tr.get_text(" ", strip=True)):
            continue

        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        # Formato NUEVO (Juvenil/Cadete/Infantil): EQUIPOS | MARCADOR | FECHA | LUGAR | ...
        # Detectamos por cabecera implícita: celda 1 suele ser marcador tipo "15 - 45" o "-"
        equipos_txt = tds[0].get_text(" ", strip=True)
        marcador_txt = tds[1].get_text(" ", strip=True)
        fecha_txt = tds[2].get_text(" ", strip=True)
        lugar_txt = tds[3].get_text(" ", strip=True)

        local, visitante = parse_equipos_cell(equipos_txt)
        fecha = clean(fecha_txt)
        lugar = clean(lugar_txt)
        marcador = clean(marcador_txt).replace(" - ", "-").replace(" ", "")

        # Si esto parece válido, lo guardamos:
        if ("/" in fecha) and (local or visitante):
            matches.append({
                "fecha_texto": fecha,
                "local": local,
                "visitante": visitante,
                "resultado": marcador if marcador not in ["-", ""] else "",
                "lugar": lugar
            })
            continue

        # Formato “viejo/territorial” (por si alguna tabla viene distinto):
        # Aquí tuvieras columnas tipo fecha/local/visitante/resultado...
        d0 = clean(tds[0].get_text(" ", strip=True))
        d1 = clean(tds[1].get_text(" ", strip=True))
        d2 = clean(tds[2].get_text(" ", strip=True))
        d3 = clean(tds[3].get_text(" ", strip=True))

        # Si d0 es marcador y d2 es fecha -> reorden
        if is_score(d0) and ("/" in d2):
            matches.append({
                "fecha_texto": d2,
                "local": d1,
                "visitante": "3COM Squad Valsequillo",
                "resultado": d0.replace(" ", ""),
                "lugar": d3 or "Pabellón Municipal"
            })
        else:
            # intento directo
            matches.append({
                "fecha_texto": d0,
                "local": d1,
                "visitante": d2,
                "resultado": d3.replace(" ", ""),
                "lugar": clean(tds[4].get_text(" ", strip=True)) if len(tds) > 4 else ""
            })

    # Guardar JSON
    with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
        json.dump({"matches": matches}, f, ensure_ascii=False)

    # Guardar ICS (si hay fecha)
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "X-WR-CALNAME:" + cat["name"]]
    for m in matches:
        try:
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
