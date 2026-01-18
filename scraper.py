import json
import os
import requests
from bs4 import BeautifulSoup

def main():
    url = "https://resultadosbalonmano.isquad.es/competicion.php?id_superficie=1&seleccion=0&id_categoria=2660&id_temp=2526&id_ambito=20&id_territorial=37"
    club = "3COM Squad Valsequillo"
    folder = "TF"
    
    print(f"Iniciando descarga de {url}")
    os.makedirs(folder, exist_ok=True)
    
    try:
        r = requests.get(url, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")
        matches = []
        
        for tr in soup.find_all("tr"):
            if club in tr.get_text():
                tds = tr.find_all("td")
                if len(tds) >= 4:
                    matches.append({
                        "fecha_texto": tds[0].get_text(strip=True),
                        "local": tds[1].get_text(strip=True),
                        "visitante": tds[2].get_text(strip=True),
                        "resultado": tds[3].get_text(strip=True),
                        "lugar": tds[4].get_text(strip=True) if len(tds) > 4 else ""
                    })
        
        with open(f"{folder}/partidos.json", "w", encoding="utf-8") as f:
            json.dump({"categoria": "Liga Territorial Femenina", "matches": matches}, f, ensure_ascii=False)
        
        print(f"✅ ÉXITO: Creado {folder}/partidos.json con {len(matches)} partidos")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    main()
