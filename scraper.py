import json
import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

CLUB = "3COM Squad Valsequillo"
UA = "Mozilla/5.0 (GitHubActions)"

def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

def find_table(soup):
    for table in soup.find_all("table"):
        headers = [clean(th.get_text()).upper() for th in table.find_all("th")]
        if "EQUIPOS" in headers and "FECHA" in headers and "LUGAR" in headers:
            return table, headers
    return None, None

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        cats = json.load(f)

    for c in cats:
        slug = c["slug"]
        title = c["title"]
        url = c["url"]

        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        table, headers = find_table(soup)
        if not table:
            raise RuntimeError(f"No encontré la tabla de partidos en {url}")

        hmap = {h: i for i, h in enumerate(headers)}
        i_eq = hmap["EQUIPOS"]
        i_f = hmap["FECHA"]
        i_l = hmap["LUGAR"]
        i_e = hmap.get("ESTADO", None)

        matches = []
        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if not tds:
                continue

            equipos_raw = clean(tds[i_eq].get_text(" ", strip=True))
            if CLUB not in equipos_raw:
                continue

            equipos_clean = re.sub(r"^\s*VS\s*", "", equipos_raw, flags=re.I).strip()
            local, visitante = equipos_clean, ""
            if " - " in equipos_clean:
                local, visitante = [clean(x) for x in equipos_clean.split(" - ", 1)]

            fecha_texto = clean(tds[i_f].get_text(" ", strip=True))
            lugar = clean(tds[i_l].get_text(" ", strip=True))
            estado = clean(tds[i_e].get_text(" ", strip=True)) if (i_e is not None and i_e < len(tds)) else "Pendiente"

            matches.append({
                "local": local,
                "visitante": visitante,
                "fecha_texto": fecha_texto,
                "lugar": lugar,
                "estado": estado,
                "es_casa": (CLUB in local),
            })

        payload = {
            "club": CLUB,
            "categoria": title,
            "slug": slug,
            "source_url": url,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "matches": matches
        }

        os.makedirs(slug, exist_ok=True)
        with open(os.path.join(slug, "partidos.json"), "w", encoding="utf-8") as out:
            json.dump(payload, out, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
