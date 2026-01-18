import json
import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (GitHub Actions) AppleWebKit/537.36"}

def clean(s):
    return re.sub(r"\s+", " ", (s or "").strip())

def parse_rows(html, club):
    soup = BeautifulSoup(html, "lxml")
    matches = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3: continue
        row_text = clean(tr.get_text(" "))
        if club.lower() not in row_text.lower(): continue
        cols = [clean(td.get_text(" ")) for td in tds]
        res = None
        for c in cols:
            if re.search(r"\b\d{1,3}\s*-\s*\d{1,3}\b", c):
                res = re.search(r"\b\d{1,3}\s*-\s*\d{1,3}\b", c).group(0).replace(" ", "").replace("-", " - ")
                break
        matches.append({
            "fecha_texto": cols[0] if len(cols) >= 1 else "",
            "local": cols[1] if len(cols) >= 2 else "",
            "visitante": cols[2] if len(cols) >= 3 else "",
            "resultado": res,
            "lugar": cols[-1] if len(cols) >= 5 else "Por determinar"
        })
    return matches

def main():
    # CONFIGURACIÓN DIRECTA (Sin depender de categories.json)
    categories = [
        {
            "name": "Liga Territorial Femenina",
            "slug": "TF",
            "url": "https://resultadosbalonmano.isquad.es/competicion.php?id_superficie=1&seleccion=0&id_categoria=2660&id_temp=2526&id_ambito=20&id_territorial=37"
        }
    ]

    for cat in categories:
        slug = cat["slug"]
        print(f"Procesando {slug}...")
        os.makedirs(slug, exist_ok=True)
        try:
            r = requests.get(cat["url"], headers=HEADERS, timeout=30)
            matches = parse_rows(r.text, "3COM Squad Valsequillo")
            out = {"categoria": cat["name"], "matches": matches, "updated_at": datetime.now().isoformat()}
            with open(os.path.join(slug, "partidos.json"), "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            print(f"✅ {slug}/partidos.json creado con {len(matches)} partidos")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
