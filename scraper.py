import json
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def limpiar_fecha(texto):
    if not texto: return ""
    texto = re.sub(r'(\d{2}/\d{2}/\d{4})(\d{1,2}:\d{2})', r'\1 \2', texto)
    return texto.strip()

def generar_ics(matches, categoria, folder):
    eventos = []
    for m in matches:
        f = m.get('fecha_texto', '')
        match = re.search(r'(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2}):(\d{2})', f)
        if match:
            dia, mes, anio, hora, minuto = match.groups()
            fecha_ics = f"{anio}{mes}{dia}T{hora.zfill(2)}{minuto}00"
            evento = f"BEGIN:VEVENT\nSUMMARY:{m['local']} vs {m['visitante']}\nDTSTART:{fecha_ics}\nDTEND:{fecha_ics}\nLOCATION:{m['lugar']}\nDESCRIPTION:Categoría: {categoria}\nEND:VEVENT"
            eventos.append(evento)
    
    if eventos:
        content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//3COM//ES\n" + "\n".join(eventos) + "\nEND:VCALENDAR"
        with open(f"{folder}/calendar.ics", "w", encoding="utf-8") as f:
            f.write(content)

def scrape_categoria(cat):
    os.makedirs(cat['slug'], exist_ok=True)
    try:
        r = requests.get(cat['url'], timeout=20)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, "html.parser")
        matches = []
        for tr in soup.find_all("tr"):
            if "3com" in tr.get_text().lower():
                tds = tr.find_all("td")
                if len(tds) >= 4:
                    matches.append({
                        "fecha_texto": limpiar_fecha(tds[0].get_text(strip=True)),
                        "local": tds[1].get_text(strip=True),
                        "visitante": tds[2].get_text(strip=True),
                        "resultado": tds[3].get_text(strip=True),
                        "lugar": tds[4].get_text(strip=True) if len(tds) > 4 else ""
                    })
        with open(f"{cat['slug']}/partidos.json", "w", encoding="utf-8") as f:
            json.dump({"categoria": cat['name'], "matches": matches}, f, ensure_ascii=False, indent=2)
        generar_ics(matches, cat['name'], cat['slug'])
    except Exception as e: print(f"Error en {cat['slug']}: {e}")

def main():
    with open("categories.json", "r", encoding="utf-8") as f:
        categorias = json.load(f)
    for cat in categorias: scrape_categoria(cat)

if __name__ == "__main__": main()
