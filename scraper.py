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
            
            # Buscamos todas las filas de la tabla
            rows = soup.find_all("tr")
            matches = []

            for tr in rows:
                cells = tr.find_all("td")
                # Si la fila tiene el nombre del club
                if CLUB.lower() in tr.get_text().lower():
                    # Intentamos localizar los nombres de los equipos
                    # En iSquad suelen estar en celdas con enlaces o clases específicas
                    # Vamos a buscar textos que NO sean la fecha ni el lugar
                    
                    equipos_texto = ""
                    fecha_texto = ""
                    lugar_texto = ""
                    
                    for td in cells:
                        t = td.get_text(" ", strip=True)
                        # Si tiene formato de fecha (00/00/0000)
                        if re.search(r'\d{2}/\d{2}/\d{4}', t):
                            fecha_texto = t
                        # Si es una celda con " - " o " VS " es probablemente la de equipos
                        elif " - " in t or " VS " in t.upper():
                            equipos_texto = t
                        # Si es texto largo y no es lo anterior, es el lugar
                        elif len(t) > 10 and not lugar_texto:
                            lugar_texto = t

                    # Si no encontramos la celda con " - ", probamos a juntar las celdas de equipos
                    if not equipos_texto and len(cells) >= 2:
                        # A veces local y visitante están en celdas separadas
                        # Buscamos celdas que contengan nombres de clubes (suelen tener enlaces)
                        potential_teams = [td.get_text(strip=True) for td in cells if len(td.get_text(strip=True)) > 3 and not re.search(r'\d{2}/\d{2}', td.get_text())]
                        if len(potential_teams) >= 2:
                            local = potential_teams[0]
                            visitante = potential_teams[1]
                        else:
                            local = "3COM Squad Valsequillo"
                            visitante = "Rival"
                    else:
                        # Limpiamos el texto de equipos
                        clean_teams = " ".join(equipos_texto.split())
                        parts = re.split(r'\s*-\s*|\s+VS\s+|\s+vs\s+', clean_teams, flags=re.IGNORECASE)
                        local = parts[0].strip() if len(parts) > 0 else "Local"
                        visitante = parts[1].strip() if len(parts) > 1 else "Visitante"

                    # Limpiar la fecha pegada (ej: 18/01/202612:00)
                    f_match = re.search(r'(\d{2}/\d{2}/\d{4})\s*(\d{2}:\d{2})?', fecha_texto.replace(" ", ""))
                    if f_match:
                        fecha_f = f_match.group(1)
                        hora_f = f_match.group(2) if f_match.group(2) else "00:00"
                        fecha_final = f"{fecha_f} {hora_f}"
                    else:
                        fecha_final = "Fecha por confirmar"

                    matches.append({
                        "local": local,
                        "visitante": visitante,
                        "fecha_texto": fecha_final,
                        "lugar": lugar_texto if lugar_texto else "Pabellón por confirmar",
                        "es_casa": (CLUB.lower() in local.lower())
                    })

            os.makedirs(slug, exist_ok=True)
            with open(os.path.join(slug, "partidos.json"), "w", encoding="utf-8") as out:
                json.dump({"categoria": title, "matches": matches}, out, ensure_ascii=False, indent=2)
            create_ics(slug, title, matches)
            print(f"✅ {title}: {len(matches)} partidos encontrados.")
        except Exception as e:
            print(f"❌ Error en {slug}: {e}")

if __name__ == "__main__":
    main()
