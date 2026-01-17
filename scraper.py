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
            res = f" ({m['resultado']})" if m.get('resultado') else ""
            ics_content.extend([
                "BEGIN:VEVENT", f"UID:{uid}",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{dt_str}", f"DTEND:{dt_end}",
                f"SUMMARY:{m['local']}{res} vs {m['visitante']}",
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
            rows = soup.find_all("tr")
            matches = []

            for tr in rows:
                if CLUB.lower() in tr.get_text().lower():
                    tds = tr.find_all("td")
                    if len(tds) < 4: continue

                    # 1. EQUIPOS (Buscamos enlaces en la fila)
                    links = tr.find_all("a", href=re.compile(r'id_equipo|equipo'))
                    if len(links) >= 2:
                        local = links[0].get_text(strip=True)
                        visitante = links[1].get_text(strip=True)
                    else:
                        # Si no hay enlaces, usamos la columna 2 (índice 1)
                        txt = tds[1].get_text(" ", strip=True)
                        parts = re.split(r'\s*-\s*|\s+VS\s+', txt, flags=re.IGNORECASE)
                        local = parts[0].strip() if len(parts) > 0 else "Local"
                        visitante = parts[1].strip() if len(parts) > 1 else "Visitante"

                    # 2. RESULTADO (Solo si hay una celda que sea exactamente "N - N")
                    resultado = ""
                    for td in tds:
                        t = td.get_text(strip=True)
                        if re.match(r'^\d+\s*-\s*\d+$', t):
                            resultado = t
                            break

                    # 3. FECHA (Columna 3 / índice 2)
                    raw_f = tds[2].get_text(strip=True)
                    f_m = re.search(r'(\d{2}/\d{2}/\d{4})\s*(\d{2}:\d{2})?', raw_f.replace(" ", ""))
                    fecha_f = f"{f_m.group(1)} {f_m.group(2) if f_m.group(2) else '00:00'}" if f_m else "Fecha por confirmar"

                    # 4. LUGAR (Columna 4 / índice 3)
                    lugar = tds[3].get_text(strip=True) if len(tds) > 3 else "Pabellón por confirmar"
                    # Si el lugar es muy corto (menos de 5 letras), probablemente es un error, buscamos en la siguiente
                    if len(lugar) < 5 and len(tds) > 4:
                        lugar = tds[4].get_text(strip=True)

                    matches.append({
                        "local": local, "visitante": visitante,
                        "resultado": resultado, "fecha_texto": fecha_f,
                        "lugar": lugar, "es_casa": (CLUB.lower() in local.lower())
                    })

            os.makedirs(slug, exist_ok=True)
            with open(os.path.join(slug, "partidos.json"), "w", encoding="utf-8") as out:
                json.dump({"categoria": title, "matches": matches}, out, ensure_ascii=False, indent=2)
            create_ics(slug, title, matches)
        except Exception as e: print(f"Error en {slug}: {e}")

if __name__ == "__main__":
    main()
