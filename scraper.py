import json
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Ajusta si tu club aparece con otro nombre en alguna categoría
CLUB_KEYWORDS = ["3com", "valsequillo"]

def limpiar_dato(texto: str) -> str:
    if not texto:
        return ""
    t = str(texto).strip()

    # Quitar "VS" suelto
    t = t.replace("VS", "").strip()

    # Arreglar fecha y hora pegadas: DD/MM/AAAAHH:MM -> DD/MM/AAAA | HH:MM
    t = re.sub(r"(\d{2}/\d{2}/\d{4})(\d{2}:\d{2})", r"\1 | \2", t)

    # Normalizar espacios
    t = re.sub(r"\s+", " ", t).strip()
    return t

def fila_es_del_club(tr) -> bool:
    txt = tr.get_text(" ", strip=True).lower()
    return any(k in txt for k in CLUB_KEYWORDS)

def parsear_fecha_para_ics(fecha_texto: str):
    """
    Devuelve datetime (naive) si puede parsear 'DD/MM/YYYY | HH:MM' o 'DD/MM/YYYY HH:MM'
    Si no puede, devuelve None.
    """
    if not fecha_texto:
        return None
    t = fecha_texto.replace("|", " ").strip()
    t = re.sub(r"\s+", " ", t)

    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H.%M"):
        try:
            return datetime.strptime(t, fmt)
        except:
            pass
    return None

def generar_ics(slug: str, categoria: str, matches: list):
    """
    Genera un calendario simple con eventos de 90 min (por defecto).
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//3COM Squad Valsequillo//Calendarios//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{categoria}",
        "X-WR-TIMEZONE:Atlantic/Canary",
    ]

    for i, m in enumerate(matches, start=1):
        dt = parsear_fecha_para_ics(m.get("fecha_texto", ""))
        if not dt:
            continue

        # Duración estimada 90 minutos
        dt_end = dt + timedelta(minutes=90)

        # Formato iCalendar (sin zona, pero aceptado por la mayoría)
        dtstart = dt.strftime("%Y%m%dT%H%M%S")
        dtend = dt_end.strftime("%Y%m%dT%H%M%S")

        local = m.get("local", "").strip()
        visitante = m.get("visitante", "").strip()
        lugar = m.get("lugar", "").strip()

        summary = f"{local} vs {visitante}".strip()
        uid = f"{slug}-{i}-{dtstart}@3com-valsequillo"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{summary}",
            f"LOCATION:{lugar}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")

    with open(f"{slug}/calendar.ics", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def scrape_categoria(cat: dict):
    slug = cat["slug"]
    name = cat.get("name", slug)
    url = cat["url"]

    # Asegura carpeta
    os.makedirs(slug, exist_ok=True)

    matches = []

    try:
        r = requests.get(url, timeout=25)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")

        # Recorremos filas
        for tr in soup.find_all("tr"):
            if not fila_es_del_club(tr):
                continue

            tds = tr.find_all("td")
            if len(tds) < 4:
                continue

            # Lectura estándar esperada:
            # 0 fecha, 1 local, 2 visitante, 3 resultado, (4 lugar opcional)
            f = limpiar_dato(tds[0].get_text(" ", strip=True))
            l = limpiar_dato(tds[1].get_text(" ", strip=True))
            v = limpiar_dato(tds[2].get_text(" ", strip=True))
            res = limpiar_dato(tds[3].get_text(" ", strip=True))
            lug = limpiar_dato(tds[4].get_text(" ", strip=True)) if len(tds) > 4 else ""

            # Corrección para casos tipo Territorial donde columnas vienen movidas:
            # Si la "fecha" no contiene "/" pero el "visitante" sí parece fecha, intercambiamos.
            # Ejemplo visto: f="40-17", v="18/01/202612:00"
            if ("/" not in f) and ("/" in v):
                # Interpretación: v es fecha real, f es resultado
                fecha_texto = limpiar_dato(v)
                resultado = limpiar_dato(f)
                local = l
                visitante = "3COM Squad Valsequillo"
                lugar = res or lug
            else:
                fecha_texto = f
                resultado = res
                local = l
                visitante = v
                lugar = lug

            matches.append({
                "fecha_texto": fecha_texto,
                "local": local,
                "visitante": visitante,
                "resultado": resultado,
                "lugar": lugar
            })

    except Exception as e:
        print(f"❌ Error en {slug}: {e}")

    # Guardar JSON aunque esté vacío
    with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
        json.dump({"categoria": name, "matches": matches}, f, ensure_ascii=False, indent=2)

    # Generar ICS (aunque haya 0 eventos, crea el archivo)
    generar_ics(slug, name, matches)

    print(f"✅ {name} ({slug}): {len(matches)} partidos")

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        categorias = json.load(f)

    for cat in categorias:
        scrape_categoria(cat)

if __name__ == "__main__":
    main()
