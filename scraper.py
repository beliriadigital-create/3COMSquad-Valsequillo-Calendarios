 import json
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def limpiar_texto(t):
    if not t: return ""
    # Separar fecha de hora si están pegadas (DD/MM/AAAAHH:MM)
    t = re.sub(r'(\d{2}/\d{2}/\d{4})(\d{2}:\d{2})', r'\1 | \2', t)
    return t.replace('VS', '').strip()

def scrape_categoria(cat):
    slug = cat['slug']
    os.makedirs(slug, exist_ok=True)
    try:
        r = requests.get(cat['url'], timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, "html.parser")
        matches = []
        for tr in soup.find_all("tr"):
            if "3com" in tr.get_text().lower():
                tds = tr.find_all("td")
                if len(tds) >= 4:
                    # Extraemos y limpiamos cada campo
                    f_raw = limpiar_texto(tds[0].get_text(strip=True))
                    l_raw = limpiar_texto(tds[1].get_text(strip=True))
                    v_raw = limpiar_texto(tds[2].get_text(strip=True))
                    r_raw = limpiar_texto(tds[3].get_text(strip=True))
                    lug_raw = limpiar_texto(tds[4].get_text(strip=True)) if len(tds) > 4 else ""

                    # Si la fecha parece un resultado (ej. 40-17), reordenamos
                    if "-" in f_raw and "/" in v_raw:
                        matches.append({"fecha_texto": v_raw, "local": l_raw, "visitante": "3COM Squad Valsequillo", "resultado": f_raw, "lugar": r_raw})
                    else:
                        matches.append({"fecha_texto": f_raw, "local": l_raw, "visitante": v_raw, "resultado": r_raw, "lugar": lug_raw})
        
        with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
            json.dump({"categoria": cat['name'], "matches": matches}, f, ensure_ascii=False, indent=2)
    except Exception as e: print(f"Error en {slug}: {e}")

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        categorias = json.load(f)
    for cat in categorias: scrape_categoria(cat)

if __name__ == "__main__": main()
