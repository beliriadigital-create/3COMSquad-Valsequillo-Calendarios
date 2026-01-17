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
                    if len(tds) < 3: continue

                    # 1. EQUIPOS (Por enlaces)
                    links = tr.find_all("a", href=re.compile(r'id_equipo|equipo'))
                    if len(links) >= 2:
                        local = links[0].get_text(strip=True)
                        visitante = links[1].get_text(strip=True)
                    else:
                        txt_eq = tds[1].get_text(" ", strip=True)
                        txt_limpio = re.sub(r'\d+\s*-\s*\d+', ' vs ', txt_eq)
                        parts = re.split(r'\s*-\s*|\s+VS\s+|\s+vs\s+', txt_limpio, flags=re.IGNORECASE)
                        local = parts[0].strip() if len(parts) > 0 else "Local"
                        visitante = parts[1].strip() if len(parts) > 1 else "Visitante"

                    # 2. FECHA Y RESULTADO
                    fecha_f, resultado = "Fecha por confirmar", ""
                    for td in tds:
                        t = td.get_text(strip=True)
                        f_m = re.search(r'(\d{2}/\d{2}/\d{4})', t)
                        if f_m:
                            h_m = re.search(r'(\d{2}:\d{2})', t)
                            fecha_f = f"{f_m.group(1)} {h_m.group(1) if h_m else '00:00'}"
                        if re.match(r'^\d+\s*-\s*\d+$', t):
                            resultado = t

                    # 3. LUGAR (CON LISTA NEGRA)
                    lugar = "Pabellón por confirmar"
                    for td in tds:
                        t = td.get_text(strip=True)
                        # Si es un texto largo y NO es la fecha ni el resultado
                        if len(t) > 10 and not re.search(r'\d{2}/\d{2}', t) and not re.match(r'^\d+\s*-\s*\d+$', t):
                            # LISTA NEGRA: Si el texto contiene el nombre de los equipos, NO es el lugar
                            if local.lower() not in t.lower() and visitante.lower() not in t.lower():
                                lugar = t
                                break

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
