import argparse
import json
import time

# MQTT
import paho.mqtt.client as mqtt

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
from datetime import datetime
import re

def publish_sensor(client, topic_base, sensor_name, state, attributes=None):
    """
    Publie un sensor via MQTT Discovery.
    """
    # Topic de config
    config_topic = f"{topic_base}/{sensor_name}/config"
    # Topic de state
    state_topic = f"{topic_base}/{sensor_name}/state"

    device_name = "VilleQCCollecte"
    unique_id = f"ville_qc_{sensor_name}"

    config_payload = {
        "name": f"Collecte {sensor_name}",
        "state_topic": state_topic,
        "unique_id": unique_id,
        "device": {
            "identifiers": ["ville_qc_collecte_device"],
            "name": device_name,
            "manufacturer": "Ville de Québec",
        }
    }

    # Gérer les attributs
    if attributes:
        attr_topic = f"{topic_base}/{sensor_name}/attributes"
        config_payload["json_attributes_topic"] = attr_topic
        # Publier le JSON des attributs
        client.publish(attr_topic, json.dumps(attributes), retain=True)

    # Publier la config (retain pour discovery)
    client.publish(config_topic, json.dumps(config_payload), retain=True)
    # Publier l’état
    client.publish(state_topic, state, retain=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", required=True)
    parser.add_argument("--mqtt_host", default="core-mosquitto")
    parser.add_argument("--mqtt_port", default="1883")
    parser.add_argument("--mqtt_user", default="")
    parser.add_argument("--mqtt_pass", default="")

    args = parser.parse_args()

    ADDRESS = args.address
    MQTT_HOST = args.mqtt_host
    MQTT_PORT = int(args.mqtt_port)
    MQTT_USER = args.mqtt_user
    MQTT_PASS = args.mqtt_pass

    print(f"[SCRIPT] Lancement avec adresse = {ADDRESS}")

    # Connexion MQTT
    client = mqtt.Client()
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.loop_start()
        print("[SCRIPT] Connecté à MQTT.")
    except Exception as e:
        print(f"[ERREUR] Connexion MQTT impossible : {e}")
        return

    # Préparation Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")

    # Sur la plupart des installations, on a chromium-driver dans /usr/bin
    service = Service("/usr/bin/chromedriver")

    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        url_main = "https://www.ville.quebec.qc.ca/services/info-collecte/"
        print(f"[SCRIPT] Accès à la page: {url_main}")
        driver.get(url_main)

        # Trouver le champ d’adresse
        field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.NAME,
                "ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$txtNomRue"
            ))
        )
        field.clear()
        field.send_keys(ADDRESS)
        print(f"[SCRIPT] Adresse saisie : {ADDRESS}")

        # Bouton Rechercher
        search_button = driver.find_element(
            By.NAME,
            "ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$BtnRue"
        )
        search_button.click()

        # Attendre l'apparition de "table.calendrier"
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.calendrier"))
        )
        print("[SCRIPT] Calendriers détectés.")

        # Parser
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tables = soup.find_all("table", class_="calendrier")
        if not tables:
            print("[SCRIPT] Aucune table calendrier trouvée.")
            publish_sensor(client, "homeassistant/sensor/ville_qc_collecte", "erreur", "No table found")
            return

        # Extraire ordures / recyclage
        from datetime import date
        today = date.today()

        ordures_dates = []
        recyclage_dates = []

        # Mapping mois en minuscule -> numéro
        months_map = {
            "janvier": 1, "février": 2, "fevrier": 2, "mars": 3,
            "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
            "aout": 8, "août": 8, "septembre": 9, "octobre": 10,
            "novembre": 11, "décembre": 12
        }

        for table in tables:
            caption = table.find("caption")
            if caption:
                text_caption = caption.get_text(strip=True).lower()
            else:
                text_caption = ""
            parts = text_caption.split()
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

                # Type de collecte ? (img alt)
                picto = td.find("p", class_="img")
                if picto:
                    img = picto.find("img")
                    if img:
                        alt = img.get("alt", "").lower()
                        if "ordures" in alt:
                            ordures_dates.append(dt)
                        elif "recyclage" in alt:
                            recyclage_dates.append(dt)

        def next_future(dates_list):
            fut = [d for d in dates_list if d >= today]
            if not fut:
                return None
            return min(fut)

        next_ordures = next_future(ordures_dates)
        next_recyclage = next_future(recyclage_dates)
        str_ordures = next_ordures.isoformat() if next_ordures else "N/A"
        str_recyclage = next_recyclage.isoformat() if next_recyclage else "N/A"

        print(f"[SCRIPT] Prochaines collectes : ordures={str_ordures}, recyclage={str_recyclage}")

        # Publication via MQTT Discovery
        topic_base = "homeassistant/sensor/ville_qc_collecte"
        publish_sensor(
            client,
            topic_base,
            "ordures",
            str_ordures,
            attributes={"dates": [d.isoformat() for d in sorted(ordures_dates)]}
        )
        publish_sensor(
            client,
            topic_base,
            "recyclage",
            str_recyclage,
            attributes={"dates": [d.isoformat() for d in sorted(recyclage_dates)]}
        )

    finally:
        driver.quit()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
