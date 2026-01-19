import json, os, re, requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Ahora buscamos cualquiera de estas palabras para no fallar
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
        
        # Buscamos todas las filas de la tabla
        for tr in soup.find_all("tr"):
            texto_fila = tr.get_text(" ", strip=True).lower()
            
            # Si no menciona nuestro club, saltamos a la siguiente fila
            if not any(k in texto_fila for k in CLUB_KEYS):
                continue

            tds = tr.find_all("td")
            if len(tds) < 3: continue
            
            celdas = [clean(td.get_text(" ", strip=True)) for td in tds]
            
            # --- LÓGICA DE EXTRACCIÓN ---
            if re.search(r"\d{2}/\d{2}/\d{4}", celdas[0]):
                # Formato Territorial
                fecha, local, visitante, resultado = celdas[0], celdas[1], celdas[2], celdas[3]
                lugar = celdas[4] if len(celdas) > 4 else ""
            else:
                # Formato Base (Juvenil, Cadete, Infantil)
                # En base: Celda 0=Equipos, Celda 1=Resultado, Celda 2=Fecha, Celda 3=Hora, Celda 4=Lugar
                equipos = celdas[0]
                resultado = celdas[1]
                fecha = celdas[2]
                hora = celdas[3] if len(celdas) > 3 else ""
                lugar = celdas[4] if len(celdas) > 4 else ""
                
                # Separar equipos
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
                "local": local,
                "visitante": visitante,
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
            scrape_categoria(cat)

if __name__ == "__main__":
    main()
