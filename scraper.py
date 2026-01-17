import json, os, re, requests
from bs4 import BeautifulSoup
from datetime import datetime

CLUB = "3COM Squad Valsequillo"
UA = "Mozilla/5.0 (GitHubActions)"

def create_ics(slug, title, matches):
    ics_content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//3COM Squad Valsequillo//NONSGML v1.0//ES",
        f"X-WR-CALNAME:{title}",
        "X-WR-TIMEZONE:Atlantic/Canary",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    for m in matches:
        # Intentar extraer fecha para el formato ICS (YYYYMMDDTHHMMSS)
        try:
            # Formato esperado: "15/10/2023 12:00"
            dt = datetime.strptime(m['fecha_texto'], "%d/%m/%Y %H:%M")
            dt_str = dt.strftime("%Y%m%dT%H%M%S")
            dt_end = dt.strftime("%Y%m%dT%H%M%S") # Duración estimada no definida, ponemos misma hora
        except:
            continue

        uid = f"{slug}-{dt_str}@valsequillo-balonmano"
        ics_content.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{dt_str}",
            f"SUMMARY:{m['local']} vs {m['visitante']}",
            f"LOCATION:{m['lugar']}",
            f"DESCRIPTION:Partido de {title}. Estado: {m['estado']}",
            "END:VEVENT"
        ])
    
    ics_content.append("END:VCALENDAR")
    
    with open(os.path.join(slug, "calendario.ics"), "w", encoding="utf-8") as f:
        f.write("\n".join(ics_content))

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        cats = json.load(f)

    for c in cats:
        slug, title, url = c["slug"], c["title"], c["url"]
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table")
        if not table: continue

        matches = []
        for tr in table.find_all("tr"):
            if CLUB in tr.get_text():
                tds = tr.find_all("td")
                if len(tds) < 4: continue
                equipos = tds[1].get_text(strip=True).replace("VS", "").strip()
                local, visitante = equipos, ""
                if " - " in equipos:
                    parts = equipos.split(" - ", 1)
                    local, visitante = parts[0].strip(), parts[1].strip()

                matches.append({
                    "local": local, "visitante": visitante,
                    "fecha_texto": tds[2].get_text(strip=True),
                    "lugar": tds[3].get_text(strip=True),
                    "estado": tds[4].get_text(strip=True) if len(tds)>4 else "Pendiente",
                    "es_casa": (CLUB in local)
                })

        os.makedirs(slug, exist_ok=True)
        # Guardar JSON
        with open(os.path.join(slug, "partidos.json"), "w", encoding="utf-8") as out:
            json.dump({"categoria": title, "matches": matches}, out, ensure_ascii=False, indent=2)
        # Guardar ICS
        create_ics(slug, title, matches)

if __name__ == "__main__":
    main()
