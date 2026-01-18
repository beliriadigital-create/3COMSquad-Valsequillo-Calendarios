import json
import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GitHub Actions) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari"
}

def clean(s: str) -> str:
    """Limpia espacios en blanco extra"""
    return re.sub(r"\s+", " ", (s or "").strip())

def parse_rows(html: str, club: str):
    """Extrae partidos de la tabla HTML donde aparece el nombre del club"""
    soup = BeautifulSoup(html, "lxml")
    matches = []
    
    # Buscamos todas las filas de tablas
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue

        # Verificamos si el club aparece en esta fila
        row_text = clean(tr.get_text(" "))
        if club.lower() not in row_text.lower():
            continue

        # Extraemos las columnas
        cols = [clean(td.get_text(" ")) for td in tds]

        # Estructura típica: [fecha, local, visitante, resultado, lugar]
        fecha_texto = cols[0] if len(cols) >= 1 else ""
        local = cols[1] if len(cols) >= 2 else ""
        visitante = cols[2] if len(cols) >= 3 else ""

        resultado = None
        lugar = ""

        # Buscamos el resultado (formato "40-17" o "40 - 17")
        for c in cols:
            if re.search(r"\b\d{1,3}\s*-\s*\d{1,3}\b", c):
                resultado = re.search(r"\b\d{1,3}\s*-\s*\d{1,3}\b", c).group(0).replace(" ", "")
                resultado = resultado.replace("-", " - ")
                break

        # Lugar: normalmente en la última columna
        if len(cols) >= 5:
            lugar = cols[-1]
        else:
            lugar = "Por determinar"

        matches.append({
            "fecha_texto": fecha_texto,
            "local": local,
            "visitante": visitante,
            "resultado": resultado,
            "lugar": lugar
        })

    return matches

def main():
    """Función principal que lee categories.json y genera los archivos de datos"""
    with open("categories.json", "r", encoding="utf-8") as f:
        categories = json.load(f)

    for cat in categories:
        name = cat["name"]
        slug = cat["slug"]
        url = cat["url"]
        club = cat.get("club", "3COM Squad Valsequillo")

        print(f"\n==> Procesando: {name} ({slug})")
        
        # Crear carpeta si no existe
        os.makedirs(slug, exist_ok=True)

        try:
            # Descargar la página
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            html = r.text
        except Exception as e:
            print(f"❌ ERROR al descargar la página: {e}")
            # Escribimos un JSON vacío para que la web no falle
            out = {
                "categoria": name,
                "club": club,
                "matches": [],
                "error": str(e)
            }
            with open(os.path.join(slug, "partidos.json"), "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            continue

        # Extraer partidos
        matches = parse_rows(html, club)
        print(f"✅ Partidos encontrados: {len(matches)}")

        # Guardar JSON
        out = {
            "categoria": name,
            "club": club,
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "source": url,
            "matches": matches
        }

        with open(os.path.join(slug, "partidos.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

        print(f"💾 Guardado en: {slug}/partidos.json")

if __name__ == "__main__":
    main()
