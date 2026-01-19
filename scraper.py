import json, os, re, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

CLUB_KEYS = ["3com", "valsequillo"]

def clean(s: str) -> str:
    return " ".join(s.replace("\xa0", " ").split()).strip()

def scrape_categoria(cat):
    slug = cat["slug"]
    os.makedirs(slug, exist_ok=True)
    matches = []
    print(f"--- Procesando: {cat['name']} ---")

    try:
        r = requests.get(cat["url"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 4: continue
            
            texto_fila = tr.get_text(" ", strip=True).lower()
            if not any(k in texto_fila for k in CLUB_KEYS): continue

            celdas = [clean(td.get_text(" ", strip=True)) for td in tds]
            
            # Detectar formato: Territorial (Fecha en celda 0) vs Base (Equipos en celda 0)
            if re.search(r"\d{2}/\d{2}/\d{4}", celdas[0]):
                # FORMATO TERRITORIAL
                fecha, local, visitante, resultado = celdas[0], celdas[1], celdas[2], celdas[3]
                lugar = celdas[4] if len(celdas) > 4 else ""
            else:
                # FORMATO JUVENIL/CADETE/INFANTIL
                equipos, resultado, fecha = celdas[0], celdas[1], celdas[2]
                hora = celdas[3] if len(celdas) > 3 else ""
                lugar = celdas[4] if len(celdas) > 4 else ""
                
                if " - " in equipos:
                    local, visitante = equipos.split(" - ", 1)
                elif " VS " in equipos.upper():
                    local, visitante = re.split(r" VS ", equipos, flags=re.I)
                else:
                    local, visitante = equipos, ""
                
                if hora and "/" not in hora:
                    fecha = f"{fecha} | {hora}"

            matches.append({
                "fecha_texto": fecha,
                "local": local.strip(),
                "visitante": visitante.strip(),
                "resultado": resultado,
                "lugar": lugar,
                "estado": ""
            })

        # Guardar JSON
        with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
            json.dump({"matches": matches}, f, ensure_ascii=False, indent=2)
        
        # Generar ICS (Calendario)
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", f"X-WR-CALNAME:{cat['name']}"]
        for m in matches:
            try:
                raw_f = m["fecha_texto"].replace(" | ", " ")
                dt = datetime.strptime(raw_f, "%d/%m/%Y %H:%M")
                lines += ["BEGIN:VEVENT", f"SUMMARY:{m['local']} vs {m['visitante']}",
                          f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}",
                          f"DTEND:{(dt + timedelta(minutes=90)).strftime('%Y%m%dT%H%M%S')}",
                          f"LOCATION:{m['lugar']}", "END:VEVENT"]
            except: continue
        lines.append("END:VCALENDAR")
        with open(f"{slug}/calendar.ics", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            
        print(f"EXITO: {slug} actualizado con {len(matches)} partidos.")
    except Exception as e:
        print(f"ERROR en {slug}: {e}")

def main():
    if not os.path.exists("categories.json"):
        print("Error: No existe categories.json")
        return
    with open("categories.json", "r", encoding="utf-8") as f:
        for cat in json.load(f): scrape_categoria(cat)

if __name__ == "__main__":
    main()
