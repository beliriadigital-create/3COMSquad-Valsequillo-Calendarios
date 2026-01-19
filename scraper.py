import json
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def limpiar_fecha(texto):
    """Separa fecha de hora si vienen pegadas (ej: 18/01/202612:00 -> 18/01/2026 12:00)"""
    if not texto:
        return texto
    # Patrón: DD/MM/AAAAHH:MM (sin espacio)
    texto = re.sub(r'(\d{2}/\d{2}/\d{4})(\d{1,2}:\d{2})', r'\1 \2', texto)
    return texto.strip()

def parsear_fecha_para_ics(texto):
    """Intenta convertir texto de fecha a formato iCalendar (YYYYMMDDTHHMMSS)"""
    if not texto or "confirmar" in texto.lower():
        return None
    try:
        # Buscar patrón DD/MM/YYYY HH:MM
        match = re.search(r'(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2}):(\d{2})', texto)
        if match:
            dia, mes, anio, hora, minuto = match.groups()
            dt = datetime(int(anio), int(mes), int(dia), int(hora), int(minuto))
            return dt.strftime('%Y%m%dT%H%M%S')
    except:
        pass
    return None

def generar_ics(matches, categoria, folder):
    """Genera archivo .ics con los partidos"""
    eventos = []
    for m in matches:
        fecha_ics = parsear_fecha_para_ics(m.get('fecha_texto', ''))
        if not fecha_ics:
            continue
        
        local = m.get('local', '')
        visitante = m.get('visitante', '')
        lugar = m.get('lugar', 'Por confirmar')
        
        # Crear evento
        evento = f"""BEGIN:VEVENT
UID:{fecha_ics}-{local}-{visitante}@3comsquad
DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}
DTSTART:{fecha_ics}
SUMMARY:{local} vs {visitante}
DESCRIPTION:Categoría: {categoria}
LOCATION:{lugar}
END:VEVENT"""
        eventos.append(evento)
    
    if eventos:
        ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//3COM Squad Valsequillo//Calendarios//ES
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:{categoria}
X-WR-TIMEZONE:Atlantic/Canary
{''.join(eventos)}
END:VCALENDAR"""
        
        with open(f"{folder}/calendar.ics", "w", encoding="utf-8") as f:
            f.write(ics_content)
        print(f"   📅 Generado {folder}/calendar.ics")

def scrape_categoria(cat_info):
    """Descarga y procesa una categoría"""
    nombre = cat_info['name']
    slug = cat_info['slug']
    url = cat_info['url']
    club = cat_info.get('club', '3COM Squad Valsequillo')
    
    print(f"\n🔍 Procesando: {nombre} ({slug})")
    print(f"   URL: {url}")
    
    os.makedirs(slug, exist_ok=True)
    
    try:
        r = requests.get(url, timeout=30)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, "html.parser")
        matches = []
        
        # Buscar todas las filas que contengan el nombre del club
        for tr in soup.find_all("tr"):
            texto_fila = tr.get_text()
            if club.lower() in texto_fila.lower() or "3com" in texto_fila.lower():
                tds = tr.find_all("td")
                if len(tds) >= 4:
                    fecha_raw = tds[0].get_text(strip=True)
                    local_raw = tds[1].get_text(strip=True)
                    visitante_raw = tds[2].get_text(strip=True)
                    resultado_raw = tds[3].get_text(strip=True)
                    lugar_raw = tds[4].get_text(strip=True) if len(tds) > 4 else ""
                    
                    # Limpiar fecha (separar si está pegada)
                    fecha_limpia = limpiar_fecha(fecha_raw)
                    visitante_limpio = limpiar_fecha(visitante_raw)
                    
                    match = {
                        "fecha_texto": fecha_limpia,
                        "local": local_raw,
                        "visitante": visitante_limpio,
                        "resultado": resultado_raw,
                        "lugar": lugar_raw
                    }
                    matches.append(match)
        
        # Guardar JSON
        data = {"categoria": nombre, "matches": matches}
        with open(f"{slug}/partidos.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"   ✅ Guardado {slug}/partidos.json con {len(matches)} partidos")
        
        # Generar ICS
        generar_ics(matches, nombre, slug)
        
    except Exception as e:
        print(f"   ❌ ERROR en {nombre}: {e}")

def main():
    print("=" * 60)
    print("🤖 ROBOT ACTUALIZADOR DE CALENDARIOS - 3COM SQUAD VALSEQUILLO")
    print("=" * 60)
    
    # Leer configuración
    try:
        with open("categories.json", "r", encoding="utf-8") as f:
            categorias = json.load(f)
    except Exception as e:
        print(f"❌ No se pudo leer categories.json: {e}")
        return
    
    # Procesar cada categoría
    for cat in categorias:
        scrape_categoria(cat)
    
    print("\n" + "=" * 60)
    print("✅ ACTUALIZACIÓN COMPLETADA")
    print("=" * 60)

if __name__ == "__main__":
    main()
