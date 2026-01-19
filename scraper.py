import json, os, re, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def limpiar_texto(t):
    if not t: return ""
    # SEPARACIÓN DE FECHA Y HORA (Garantizada)
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
            # Buscamos cualquier variante del club
            if "3com" in txt or "valsequillo" in txt:
                tds = tr.find_all("td")
                if len(tds) >= 4:
                    f = limpiar_texto(tds[0].get_text(strip=True))
                    l = limpiar_texto(tds[1].get_text(strip=True))
                    v = limpiar_texto(tds[2].get_text(strip=True))
                    res = limpiar_texto(tds[3].get_text(strip=True))
                    
                    # Si iSquad da los datos movidos (como en Territorial)
                    if "/" not in f and "/" in v:
                        matches.append({"fecha_texto": limpiar_texto(v), "local": l, "visitante": "3COM Squad Valsequillo", "resultado": f})
                    else:
                        matches.append({"fecha_texto": f, "local": l, "visitante": v, "resultado": res})
        
        # Guardar JSON
        with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
            json.dump({"matches": matches}, f, ensure_ascii=False)
            
        # Generar Calendario ICS
        lines = ["BEGIN:VCALENDAR","VERSION:2.0","X-WR-CALNAME:"+cat['name']]
        for m in matches:
            try:
                dt_str = m['fecha_texto'].replace(" | ", " ")
                dt = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
                lines.extend(["BEGIN:VEVENT",f"SUMMARY:{m['local']} vs {m['visitante']}",f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",f"DTEND:{(dt+timedelta(minutes=90)).strftime('%Y%m%dT%H%M%S')}","END:VEVENT"])
            except: pass
        lines.append("END:VCALENDAR")
        with open(f"{slug}/calendar.ics", "w", encoding="utf-8") as f: f.write("\n".join(lines))
    except: pass

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        for cat in json.load(f): scrape_categoria(cat)

if __name__ == "__main__": main()
