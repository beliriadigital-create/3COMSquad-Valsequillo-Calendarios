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
            # Buscamos cualquier rastro del club
            if any(k in txt for k in ["3com", "valsequillo", "squad"]):
                tds = tr.find_all("td")
                if len(tds) >= 4:
                    # Extraemos datos brutos
                    d0, d1, d2, d3 = tds[0].text.strip(), tds[1].text.strip(), tds[2].text.strip(), tds[3].text.strip()
                    
                    # LÓGICA ANTIFALLO: Si d0 es un resultado (ej: 40-17) y d2 tiene fecha
                    if "-" in d0 and "/" in d2:
                        fecha = limpiar(d2)
                        local = d1
                        visitante = "3COM Squad Valsequillo"
                        resultado = d0
                        lugar = d3 if len(d3) > 5 else "Pabellón Municipal"
                    else:
                        fecha = limpiar(d0)
                        local = d1
                        visitante = d2
                        resultado = d3
                        lugar = tds[4].text.strip() if len(tds) > 4 else "Pabellón Municipal"

                    matches.append({
                        "fecha_texto": fecha,
                        "local": local,
                        "visitante": visitante,
                        "resultado": resultado,
                        "lugar": lugar
                    })
        
        with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
            json.dump({"matches": matches}, f, ensure_ascii=False)
            
        # Generar ICS
        lines = ["BEGIN:VCALENDAR","VERSION:2.0","X-WR-CALNAME:"+cat['name']]
        for m in matches:
            try:
                dt = datetime.strptime(m['fecha_texto'].replace(" | ", " "), "%d/%m/%Y %H:%M")
                lines.extend(["BEGIN:VEVENT",f"SUMMARY:{m['local']} vs {m['visitante']}",f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",f"DTEND:{(dt+timedelta(minutes=90)).strftime('%Y%m%dT%H%M%S')}",f"LOCATION:{m['lugar']}","END:VEVENT"])
            except: pass
        lines.append("END:VCALENDAR")
        with open(f"{slug}/calendar.ics", "w", encoding="utf-8") as f: f.write("\n".join(lines))
        print(f"✅ {cat['name']}: {len(matches)} partidos encontrados.")
    except Exception as e: print(f"❌ Error en {cat['name']}: {e}")

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        for cat in json.load(f): scrape_categoria(cat)

if __name__ == "__main__": main()
