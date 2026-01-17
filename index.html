import json, os, re, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

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
        try:
            dt = datetime.strptime(m['fecha_texto'], "%d/%m/%Y %H:%M")
            dt_str = dt.strftime("%Y%m%dT%H%M%S")
            dt_end = (dt + timedelta(hours=1, minutes=30)).strftime("%Y%m%dT%H%M%S")
        except: continue
        uid = f"{slug}-{dt_str}@valsequillo-balonmano"
        desc = f"Partido de {title}\\n{m['local']} vs {m['visitante']}\\nEstado: {m['estado']}\\nLugar: {m['lugar']}"
        ics_content.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{dt_str}",
            f"DTEND:{dt_end}",
            f"SUMMARY:{m['local']} vs {m['visitante']}",
            f"LOCATION:{m['lugar']}",
            f"DESCRIPTION:{desc}",
            "STATUS:CONFIRMED",
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
                
                # LIMPIEZA DE EQUIPOS MEJORADA
                raw_equipos = tds[1].get_text(" ", strip=True)
                # Quitamos "VS" o "vs" y dividimos por el guion central
                equipos_clean = re.sub(r'\s+VS\s+', ' - ', raw_equipos, flags=re.IGNORECASE)
                if " - " in equipos_clean:
                    parts = equipos_clean.split(" - ")
                    local = parts[0].strip()
                    visitante = parts[1].strip() if len(parts) > 1 else ""
                else:
                    local = equipos_clean
                    visitante = ""

                # Limpiar fecha (a veces vienen pegadas)
                raw_fecha = tds[2].get_text(strip=True)
                fecha_match = re.search(r'(\d{2}/\d{2}/\d{4})(\d{2}:\d{2})', raw_fecha)
                if fecha_match:
                    fecha_final = f"{fecha_match.group(1)} {fecha_match.group(2)}"
                else:
                    fecha_final = raw_fecha

                matches.append({
                    "local": local,
                    "visitante": visitante,
                    "fecha_texto": fecha_final,
                    "lugar": tds[3].get_text(strip=True),
                    "estado": tds[4].get_text(strip=True) if len(tds) > 4 else "Pendiente",
                    "es_casa": (CLUB.lower() in local.lower())
                })

        os.makedirs(slug, exist_ok=True)
        payload = {"categoria": title, "updated_at": datetime.now().strftime("%d/%m/%Y %H:%M"), "matches": matches}
        with open(os.path.join(slug, "partidos.json"), "w", encoding="utf-8") as out:
            json.dump(payload, out, ensure_ascii=False, indent=2)
        create_ics(slug, title, matches)

if __name__ == "__main__":
    main()
