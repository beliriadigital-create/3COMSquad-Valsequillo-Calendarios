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
    # deja "40 - 17" como "40-17"
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

        c0 = clean(tds[0].get_text(" ", strip=True))

        # FORMATO NUEVO (Juvenil/Cadete/Infantil):
        # [0]=EQUIPOS, [1]=MARCADOR, [2]=FECHA (puede estar vacío), [3]=LUGAR, [4]=ESTADO (si existe)
        # Lo detectamos porque la celda EQUIPOS empieza por "VS" y contiene " - "
        if re.search(r"\bVS\b", c0, flags=re.I) and (" - " in c0 or "-" in c0):
            equipos_txt = c0
            marcador_txt = clean(tds[1].get_text(" ", strip=True))
            fecha_txt = clean(tds[2].get_text(" ", strip=True))  # puede venir ""
            lugar_txt = clean(tds[3].get_text(" ", strip=True))
            estado_txt = clean(tds[4].get_text(" ", strip=True)) if len(tds) > 4 else ""

            local, visitante = parse_equipos_cell(equipos_txt)
            resultado = normalize_score(marcador_txt)

            # Si no hay marcador y el estado existe (Retirado/Pendiente/etc.), lo mostramos como resultado “visible”
            if not resultado and estado_txt:
                resultado = estado_txt.upper()

            matches.append({
                "fecha_texto": fecha_txt,   # puede ser ""
                "local": local,
                "visitante": visitante,
                "resultado": resultado,     # score o ESTADO en mayúsculas
                "lugar": lugar_txt,
                "estado": estado_txt
            })
            continue

        # FORMATO TERRITORIAL (TF) / otros:
        # Intento simple por posiciones: fecha/local/visitante/resultado/(lugar)
        d0 = clean(tds[0].get_text(" ", strip=True))
        d1 = clean(tds[1].get_text(" ", strip=True))
        d2 = clean(tds[2].get_text(" ", strip=True))
        d3 = clean(tds[3].get_text(" ", strip=True))
        d4 = clean(tds[4].get_text(" ", strip=True)) if len(tds) > 4 else ""

        if is_score(d0) and ("/" in d2):
            # caso raro: resultado en d0 y fecha en d2
            matches.append({
                "fecha_texto": d2,
                "local": d1,
                "visitante": "3COM Squad Valsequillo",
                "resultado": normalize_score(d0),
                "lugar": d3 or d4,
                "estado": ""
            })
        else:
            matches.append({
                "fecha_texto": d0,
                "local": d1,
                "visitante": d2,
                "resultado": normalize_score(d3) or d3,
                "lugar": d4,
                "estado": ""
            })

    with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
        json.dump({"matches": matches}, f, ensure_ascii=False)

    # ICS (solo si hay fecha con dd/mm/yyyy y hh:mm)
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
            f"LOCATION:{m.get("lugar","")}",
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
