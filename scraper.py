import json, os, re, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Filtro flexible para capturar todas las categorías
CLUB_KEYS = ["3com", "valsequillo", "squad"]

def clean(s: str) -> str:
    return " ".join(s.replace("\xa0", " ").split()).strip()

def scrape_categoria(cat):
    slug = cat["slug"]
    os.makedirs(slug, exist_ok=True)
    matches = []
    print(f"--- Procesando: {cat['name']} ---")

    try:
        r = requests.get(cat["url"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        
        for tr in soup.find_all("tr"):
            texto_fila = tr.get_text(" ", strip=True).lower()
            
            # Si no menciona nuestro club, saltamos
            if not any(k in texto_fila for k in CLUB_KEYS):
                continue

            tds = tr.find_all("td")
            if len(tds) < 3: continue
            
            celdas = [clean(td.get_text(" ", strip=True)) for td in tds]
            
            # Detectar formato por posición de la fecha
            if re.search(r"\d{2}/\d{2}/\d{4}", celdas[0]):
                # Formato Territorial
                fecha, local, visitante, resultado = celdas[0], celdas[1], celdas[2], celdas[3]
                lugar = celdas[4] if len(celdas) > 4 else ""
            else:
                # Formato Base (Juvenil, Cadete, Infantil)
                equipos, resultado, fecha = celdas[0], celdas[1], celdas[2]
                hora = celdas[3] if len(celdas) > 3 else ""
                lugar = celdas[4] if len(celdas) > 4 else ""
                
                if " - " in equipos:
                    local, visitante = equipos.split(" - ", 1)
                elif " vs " in equipos.lower():
                    local, visitante = re.split(r" vs ", equipos, flags=re.I)
                else:
                    local, visitante = equipos, ""
                
                if hora and "/" not in hora:
                    fecha = f"{fecha} | {hora}"

            matches.append({
                "fecha_texto": fecha,
                "local": local.strip(),
                "visitante": visitante.strip(),
                "resultado": resultado,
                "lugar": lugar
            })

        with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
            json.dump({"matches": matches}, f, ensure_ascii=False, indent=2)
            
        print(f"EXITO: {slug} actualizado con {len(matches)} partidos.")
    except Exception as e:
        print(f"ERROR en {slug}: {e}")

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        for cat in json.load(f):
            if cat["url"]: scrape_categoria(cat)

if __name__ == "__main__":
    main()
