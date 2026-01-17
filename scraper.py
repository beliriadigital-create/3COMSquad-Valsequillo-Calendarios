import json, os, re, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

CLUB = "3COM Squad Valsequillo"
UA = "Mozilla/5.0 (GitHubActions)"

def create_ics(slug, title, matches):
    ics_content = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//3COM Squad Valsequillo//NONSGML v1.0//ES",
        f"X-WR-CALNAME:{title}", "X-WR-TIMEZONE:Atlantic/Canary",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH"
    ]
    for m in matches:
        try:
            dt = datetime.strptime(m['fecha_texto'], "%d/%m/%Y %H:%M")
            dt_str = dt.strftime("%Y%m%dT%H%M%S")
            dt_end = (dt + timedelta(hours=1, minutes=30)).strftime("%Y%m%dT%H%M%S")
            uid = f"{slug}-{dt_str}@valsequillo"
            ics_content.extend([
                "BEGIN:VEVENT", f"UID:{uid}",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{dt_str}", f"DTEND:{dt_end}",
                f"SUMMARY:{m['local']} vs {m['visitante']}",
                f"LOCATION:{m['lugar']}",
                f"DESCRIPTION:Partido de {title}", "END:VEVENT"
            ])
        except: continue
    ics_content.append("END:VCALENDAR")
    with open(os.path.join(slug, "calendario.ics"), "w", encoding="utf-8") as f:
        f.write("\n".join(ics_content))

def main():
    if not os.path.exists("categories.json"): return
    with open("categories.json", "r", encoding="utf-8") as f:
        cats = json.load(f)

    for c in cats:
        slug, title, url = c["slug"], c["title"], c["url"]
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")
            if not table: continue

            matches = []
            for tr in table.find_all("tr"):
                text = tr.get_text()
                if CLUB in text:
                    tds = tr.find_all("td")
                    if len(tds) < 4: continue
                    
                    # EXTRACCIÓN DE EQUIPOS MEJORADA
                    # Buscamos el texto en la segunda columna y separamos por " - " o " VS "
                    raw_teams = tds[1].get_text(" ", strip=True)
                    # Limpiamos espacios dobles y saltos
                    clean_teams = " ".join(raw_teams.split())
                    # Separar por guion o VS
                    parts = re.split(r'\s*-\s*|\s+VS\s+|\s+vs\s+', clean_teams, flags=re.IGNORECASE)
                    
                    local = parts[0].strip() if len(parts) > 0 else "Equipo Local"
                    visitante = parts[1].strip() if len(parts) > 1 else "Equipo Visitante"

                    # Limpiar fecha (evitar que se pegue la hora)
                    raw_f = tds[2].get_text(strip=True)
                    f_match = re.search(r'(\d{2}/\d{2}/\d{4})(\d{2}:\d{2})', raw_f)
                    fecha_f = f"{f_match.group(1)} {f_match.group(2)}" if f_match else raw_f

                    matches.append({
                        "local": local, "visitante": visitante,
                        "fecha_texto": fecha_f,
                        "lugar": tds[3].get_text(strip=True),
                        "estado": tds[4].get_text(strip=True) if len(tds)>4 else "Pendiente",
                        "es_casa": (CLUB.lower() in local.lower())
                    })

            os.makedirs(slug, exist_ok=True)
            with open(os.path.join(slug, "partidos.json"), "w", encoding="utf-8") as out:
                json.dump({"categoria": title, "matches": matches}, out, ensure_ascii=False, indent=2)
            create_ics(slug, title, matches)
        except Exception as e: print(f"Error en {slug}: {e}")

if __name__ == "__main__":
    main()
