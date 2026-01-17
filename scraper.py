import json, os, re, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

CLUB = "3COM Squad Valsequillo"
UA = "Mozilla/5.0 (GitHubActions)"

RE_SCORE = re.compile(r"^\d+\s*-\s*\d+$")
RE_DATE = re.compile(r"(\d{2}/\d{2}/\d{4})")
RE_TIME = re.compile(r"(\d{2}:\d{2})")

def norm_score(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    s = re.sub(r"\s*", "", s)          # "15 - 45" -> "15-45"
    s = s.replace("-", " - ")          # "15-45" -> "15 - 45"
    s = re.sub(r"\s+", " ", s).strip()
    return s

def create_ics(slug, title, matches):
    ics = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//3COM Squad Valsequillo//NONSGML v1.0//ES",
        f"X-WR-CALNAME:{title}",
        "X-WR-TIMEZONE:Atlantic/Canary",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for m in matches:
        try:
            dt = datetime.strptime(m["fecha_texto"], "%d/%m/%Y %H:%M")
        except Exception:
            continue

        dt_str = dt.strftime("%Y%m%dT%H%M%S")
        dt_end = (dt + timedelta(hours=1, minutes=30)).strftime("%Y%m%dT%H%M%S")
        uid = f"{slug}-{dt_str}@valsequillo"

        res = f" ({m['resultado']})" if m.get("resultado") else ""
        summary = f"{m['local']}{res} vs {m['visitante']}".strip()

        ics.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{dt_str}",
            f"DTEND:{dt_end}",
            f"SUMMARY:{summary}",
            f"LOCATION:{m.get('lugar','')}",
            f"DESCRIPTION:Partido de {title}",
            "END:VEVENT",
        ])

    ics.append("END:VCALENDAR")
    with open(os.path.join(slug, "calendario.ics"), "w", encoding="utf-8") as f:
        f.write("\n".join(ics))

def extract_teams(tr, tds):
    # 1) Método fiable: enlaces a equipo.php CON TEXTO (ignora los 2 primeros vacíos)
    a_eq = tr.select('a[href*="equipo.php"]')
    names = []
    for a in a_eq:
        t = a.get_text(" ", strip=True)
        if not t:
            continue
        if t.upper() == "VS":
            continue
        names.append(t)

    # quitar duplicados manteniendo orden
    seen = set()
    names = [x for x in names if not (x in seen or seen.add(x))]

    if len(names) >= 2:
        return names[0], names[1]

    # 2) Fallback: usar el texto de la primera celda "VS TeamA - TeamB"
    if tds:
        txt = tds[0].get_text(" ", strip=True)
        txt = re.sub(r"^\s*VS\s+", "", txt, flags=re.IGNORECASE).strip()
        if " - " in txt:
            p = txt.split(" - ", 1)
            return p[0].strip(), p[1].strip()

    return "", ""

def main():
    if not os.path.exists("categories.json"):
        print("No categories.json found")
        return

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
                # mantenemos el filtro del club para no listar toda la competición
                if CLUB.lower() not in tr.get_text(" ", strip=True).lower():
                    continue

                tds = tr.find_all("td")
                if len(tds) < 4:
                    continue

                local, visitante = extract_teams(tr, tds)

                # Fecha (en iSquad suele estar en tds[2], pero lo buscamos por patrón para ser robustos)
                fecha_texto = "Fecha por confirmar"
                for td in tds:
                    t = td.get_text(" ", strip=True)
                    dm = RE_DATE.search(t)
                    if dm:
                        hm = RE_TIME.search(t)
                        fecha_texto = f"{dm.group(1)} {hm.group(1) if hm else '00:00'}"
                        break

                # Lugar (en iSquad suele ser tds[3])
                lugar = tds[3].get_text(" ", strip=True) if len(tds) > 3 else ""

                # Resultado (si existe)
                resultado = ""
                for td in tds:
                    t = td.get_text(" ", strip=True)
                    if RE_SCORE.match(t):
                        resultado = norm_score(t)
                        break

                matches.append({
                    "local": local,
                    "visitante": visitante,
                    "resultado": resultado,
                    "fecha_texto": fecha_texto,
                    "lugar": lugar if lugar else "Pabellón por confirmar",
                    "es_casa": (CLUB.lower() in (local or "").lower()),
                })

            os.makedirs(slug, exist_ok=True)
            with open(os.path.join(slug, "partidos.json"), "w", encoding="utf-8") as out:
                json.dump({"categoria": title, "matches": matches}, out, ensure_ascii=False, indent=2)

            create_ics(slug, title, matches)

        except Exception as e:
            print(f"Error en {slug}: {e}")

if __name__ == "__main__":
    main()
