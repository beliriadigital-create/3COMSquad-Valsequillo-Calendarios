import json, os, re, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def limpiar(t):
    if not t: return ""
    t = re.sub(r"(\d{2}/\d{2}/\d{4})(\d{2}:\d{2})", r"\1 | \2", t)
    return t.replace("VS", "").strip()

def scrape_categoria(cat):
    slug = cat['slug']
    os.makedirs(slug, exist_ok=True)
    matches = []
    try:
        r = requests.get(cat['url'], timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, "html.parser")
        for tr in soup.find_all("tr"):
            txt = tr.get_text().lower()
            # BUSCADOR FLEXIBLE: Si sale cualquiera de estas palabras, guarda el partido
            if any(k in txt for k in ["3com", "valsequillo", "squad"]):
                tds = tr.find_all("td")
                if len(tds) >= 4:
                    f, l, v, res = limpiar(tds[0].text), limpiar(tds[1].text), limpiar(tds[2].text), limpiar(tds[3].text)
                    # Corrección para Territorial
                    if "/" not in f and "/" in v:
                        matches.append({"fecha_texto": limpiar(v), "local": l, "visitante": "3COM Squad Valsequillo", "resultado": f, "lugar": "Pabellón Municipal"})
                    else:
                        matches.append({"fecha_texto": f, "local": l, "visitante": v, "resultado": res, "lugar": "Pabellón Municipal"})
        
        with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
            json.dump({"matches": matches}, f, ensure_ascii=False)
            
        # Generar Calendario ICS
        lines = ["BEGIN:VCALENDAR","VERSION:2.0","X-WR-CALNAME:"+cat['name']]
        for m in matches:
            try:
                dt = datetime.strptime(m['fecha_texto'].replace(" | ", " "), "%d/%m/%Y %H:%M")
                lines.extend(["BEGIN:VEVENT",f"SUMMARY:{m['local']} vs {m['visitante']}",f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",f"DTEND:{(dt+timedelta(minutes=90)).strftime('%Y%m%dT%H%M%S')}","END:VEVENT"])
            except: pass
        lines.append("END:VCALENDAR")
        with open(f"{slug}/calendar.ics", "w", encoding="utf-8") as f: f.write("\n".join(lines))
    except: pass

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        for cat in json.load(f): scrape_categoria(cat)

if __name__ == "__main__": main()
