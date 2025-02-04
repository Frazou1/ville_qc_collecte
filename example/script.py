import argparse
import json
import time
from datetime import datetime, date, timedelta  # Ajout de timedelta pour le calcul DTEND

import paho.mqtt.client as mqtt

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup

# ... (le reste de tes imports et code inchangés)

def generate_ics(file_path, ordures_dates, recyclage_dates, today):
    """
    Génère un fichier ICS contenant les événements de collecte à partir des listes de dates.
    Seules les dates >= aujourd'hui seront ajoutées.
    """
    now_str = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = []
    lines.append("BEGIN:VCALENDAR")
    lines.append("VERSION:2.0")
    lines.append("PRODID:-//VilleQCCollecte Addon//EN")
    lines.append("CALSCALE:GREGORIAN")
    # Événements pour ordures
    for d in sorted(ordures_dates):
        if d < today:
            continue
        dtstart = d.strftime("%Y%m%d")
        dtend = (d + timedelta(days=1)).strftime("%Y%m%d")
        uid = f"ordures-{d.isoformat()}@villeqc"
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{now_str}")
        lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
        lines.append(f"DTEND;VALUE=DATE:{dtend}")
        lines.append("SUMMARY:Collecte ordures")
        lines.append("END:VEVENT")
    # Événements pour recyclage
    for d in sorted(recyclage_dates):
        if d < today:
            continue
        dtstart = d.strftime("%Y%m%d")
        dtend = (d + timedelta(days=1)).strftime("%Y%m%d")
        uid = f"recyclage-{d.isoformat()}@villeqc"
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{now_str}")
        lines.append(f"DTSTART;VALUE=DATE:{dtstart}")
        lines.append(f"DTEND;VALUE=DATE:{dtend}")
        lines.append("SUMMARY:Collecte recyclage")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", required=True)
    parser.add_argument("--mqtt_host", default="core-mosquitto")
    parser.add_argument("--mqtt_port", default="1883")
    parser.add_argument("--mqtt_user", default="")
    parser.add_argument("--mqtt_pass", default="")
    # Nouvelle option pour le calendrier ICS
    parser.add_argument("--calendar_file", default="", help="Chemin du fichier .ics pour générer le calendrier")
    args = parser.parse_args()
    ADDRESS = args.address
    MQTT_HOST = args.mqtt_host
    MQTT_PORT = int(args.mqtt_port)
    MQTT_USER = args.mqtt_user
    MQTT_PASS = args.mqtt_pass
    calendar_file = args.calendar_file.strip()  # Peut être vide

    print(f"[SCRIPT] Démarrage avec adresse={ADDRESS}")

    # Connexion MQTT et autres parties inchangées...
    client = mqtt.Client()
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.loop_start()
        print("[SCRIPT] Connecté à MQTT.")
    except Exception as e:
        print(f"[ERREUR] Impossible de se connecter à MQTT: {e}")
        return

    status = "success"
    ordures_dates = []
    recyclage_dates = []
    today = date.today()  # On définit la date d'aujourd'hui

    try:
        # Partie Selenium et scraping (inchangée)
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        url_main = "https://www.ville.quebec.qc.ca/services/info-collecte/"
        print(f"[SCRIPT] Accès: {url_main}")
        driver.get(url_main)
        field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.NAME,
                "ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$txtNomRue"
            ))
        )
        field.clear()
        field.send_keys(ADDRESS)
        search_button = driver.find_element(
            By.NAME,
            "ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$BtnRue"
        )
        search_button.click()
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.calendrier"))
        )
        print("[SCRIPT] Calendrier détecté.")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tables = soup.find_all("table", class_="calendrier")
        if not tables:
            raise RuntimeError("Aucune table 'calendrier' trouvée !")
        months_map = {
            "janvier": 1, "février": 2, "fevrier": 2, "mars": 3,
            "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
            "aout": 8, "août": 8, "septembre": 9, "octobre": 10,
            "novembre": 11, "décembre": 12
        }
        for table in tables:
            caption = table.find("caption")
            caption_txt = caption.get_text(strip=True).lower() if caption else ""
            parts = caption_txt.split()
            if len(parts) >= 2:
                month_str = parts[0]
                year_str = parts[1]
                month_num = months_map.get(month_str, 0)
                year_num = int(year_str) if year_str.isdigit() else today.year
            else:
                month_num = 0
                year_num = today.year
            for td in table.find_all("td"):
                date_p = td.find("p", class_="date")
                if not date_p:
                    continue
                day_str = date_p.get_text(strip=True)
                if not day_str.isdigit():
                    continue
                day_num = int(day_str)
                try:
                    dt = datetime(year_num, month_num, day_num).date()
                except:
                    continue
                picto = td.find("p", class_="img")
                if picto:
                    img = picto.find("img")
                    if img:
                        alt = img.get("alt", "").lower()
                        if "ordures" in alt:
                            ordures_dates.append(dt)
                        elif "recyclage" in alt:
                            recyclage_dates.append(dt)
        if not ordures_dates and not recyclage_dates:
            raise ValueError("Aucune collecte trouvée pour l'adresse donnée.")
        def next_future(dates):
            fut = [d for d in dates if d >= today]
            if not fut:
                return None
            return min(fut)
        next_ordures = next_future(ordures_dates)
        next_recyclage = next_future(recyclage_dates)
        str_ordures = next_ordures.isoformat() if next_ordures else "N/A"
        str_recyclage = next_recyclage.isoformat() if next_recyclage else "N/A"
        print(f"[SCRIPT] Prochaine ordures = {str_ordures}, recyclage = {str_recyclage}")
    except Exception as e:
        status = f"error: {e}"
        print(f"[SCRIPT] ERREUR: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass

    # Si une option de calendrier a été fournie et qu'il n'y a pas d'erreur, générer le fichier ICS
    if calendar_file and not status.startswith("error"):
        try:
            generate_ics(calendar_file, ordures_dates, recyclage_dates, today)
            print(f"[SCRIPT] Calendrier ICS généré à {calendar_file}")
        except Exception as e:
            print(f"[SCRIPT] Erreur lors de la génération du calendrier ICS: {e}")

    # Publication MQTT (inchangée)
    topic_base = "homeassistant/sensor/ville_qc_collecte"
    publish_sensor(
        client,
        topic_base,
        "status",
        state=status,
        attributes={}
    )
    if status.startswith("error"):
        publish_sensor(client, topic_base, "ordures", "error", attributes={})
    else:
        publish_sensor(
            client,
            topic_base,
            "ordures",
            str_ordures,
            attributes={
                "all_dates": [d.isoformat() for d in sorted(ordures_dates)]
            }
        )
    if status.startswith("error"):
        publish_sensor(client, topic_base, "recyclage", "error", attributes={})
    else:
        publish_sensor(
            client,
            topic_base,
            "recyclage",
            str_recyclage,
            attributes={
                "all_dates": [d.isoformat() for d in sorted(recyclage_dates)]
            }
        )
    client.loop_stop()
    client.disconnect()
    print("[SCRIPT] Terminé.")

if __name__ == "__main__":
    main()
