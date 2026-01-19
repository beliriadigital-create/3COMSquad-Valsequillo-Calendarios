import json
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def limpiar_dato(texto):
    if not texto: return ""
    t = str(texto).strip()
    # SEPARACIÓN AGRESIVA: Busca DD/MM/AAAAHH:MM y mete " | "
    t = re.sub(r"(\d{2}/\d{2}/\d{4})(\d{2}:\d{2})", r"\1 | \2", t)
    # Si hay espacio pero no barra, la ponemos
    if "/" in t and ":" in t and " | " not in t:
        t = t.replace(" ", " | ")
    return t.replace("VS", "").strip()

def generar_ics(slug, name, matches):
    lines = ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//3COM//ES","X-WR-CALNAME:"+name]
    for i, m in enumerate(matches):
        try:
            f = m['fecha_texto'].replace(" | ", " ")
            dt = datetime.strptime(f, "%d/%m/%Y %H:%M")
            lines.extend(["BEGIN:VEVENT",f"SUMMARY:{m['local']} vs {m['visitante']}",f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",f"DTEND:{(dt+timedelta(minutes=90)).strftime('%Y%m%dT%H%M%S')}","END:VEVENT"])
        except: pass
    lines.append("END:VCALENDAR")
    with open(f"{slug}/calendar.ics", "w", encoding="utf-8") as f: f.write("\n".join(lines))

def scrape_categoria(cat):
    slug = cat['slug']
    os.makedirs(slug, exist_ok=True)
    matches = []
    try:
        r = requests.get(cat['url'], timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, "html.parser")
        for tr in soup.find_all("tr"):
            if "3com" in tr.get_text().lower() or "valsequillo" in tr.get_text().lower():
                tds = tr.find_all("td")
                if len(tds) >= 4:
                    f = limpiar_dato(tds[0].get_text(strip=True))
                    l = limpiar_dato(tds[1].get_text(strip=True))
                    v = limpiar_dato(tds[2].get_text(strip=True))
                    res = limpiar_dato(tds[3].get_text(strip=True))
                    # Corrección Territorial
                    if "/" not in f and "/" in v:
                        matches.append({"fecha_texto": limpiar_dato(v), "local": l, "visitante": "3COM Squad Valsequillo", "resultado": f, "lugar": "Pabellón Municipal"})
                    else:
                        matches.append({"fecha_texto": f, "local": l, "visitante": v, "resultado": res, "lugar": "Pabellón Municipal"})
        with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
            json.dump({"categoria": cat['name'], "matches": matches}, f, ensure_ascii=False, indent=2)
        generar_ics(slug, cat['name'], matches)
    except: pass

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        for cat in json.load(f): scrape_categoria(cat)

if __name__ == "__main__": main()
