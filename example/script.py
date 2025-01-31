import argparse
import json
import os
import sys
import time

import paho.mqtt.client as mqtt

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def publish_sensor(client, topic_base, sensor_name, state, attributes=None):
    """
    Publie un sensor Home Assistant (MQTT Discovery ou topics custom).
    
    - topic_base: par ex "homeassistant/sensor/ville_qc_collecte"
    - sensor_name: identifiant du sensor (ex: "recyclage", "ordures")
    - state: valeur
    - attributes: dict d'attributs optionnels
    """
    # Topic pour l'état
    state_topic = f"{topic_base}/{sensor_name}/state"
    # Topic pour la config (discovery MQTT)
    config_topic = f"{topic_base}/{sensor_name}/config"

    # Construction du payload de config (MQTT discovery)
    # Voir la doc : https://www.home-assistant.io/docs/mqtt/discovery/
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
    if attributes:
        # Home Assistant attend un JSON dict dans le topic d’état si on veut
        # inclure des attributs (ou on peut faire un second topic).
        # Pour la démo, on inclut juste un "json_attributes_topic" en plus.
        json_attr_topic = f"{topic_base}/{sensor_name}/attributes"
        config_payload["json_attributes_topic"] = json_attr_topic
        
        # Publier aussi les attributs sous forme JSON
        client.publish(json_attr_topic, json.dumps(attributes), retain=True)

    # Publier la config
    client.publish(config_topic, json.dumps(config_payload), retain=True)
    # Publier l'état (juste un string)
    client.publish(state_topic, state, retain=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", required=True, help="Adresse à rechercher")
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

    print(f"[SCRIPT] Lancement avec address={ADDRESS}")
    
    # === Connexion MQTT ===
    client = mqtt.Client()
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"[ERREUR] Impossible de se connecter à MQTT : {e}")
        return

    # === Setup Selenium en headless ===
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    service = Service("/usr/bin/chromedriver")  # On suppose chromium-driver est installé

    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get("https://www.ville.quebec.qc.ca/services/info-collecte/")

        # Trouver le champ d'adresse
        address_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.NAME,
                "ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$txtNomRue"
            ))
        )
        address_field.clear()
        address_field.send_keys(ADDRESS)

        # Trouver le bouton Rechercher
        search_button = driver.find_element(
            By.NAME,
            "ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$BtnRue"
        )
        search_button.click()

        # Attendre la page de résultats
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.calendrier"))
        )

        # Parser
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tables = soup.find_all("table", class_="calendrier")
        if not tables:
            print("[!] Pas de table calendrier trouvée.")
            # Publier un sensor "erreur" ?
            publish_sensor(client, "homeassistant/sensor/ville_qc_collecte", "erreur", "No calendar found")
            return

        # === Extraire la prochaine date ordures & recyclage ===
        # Logique simplifiée : on scanne toutes les "td" pour trouver si c'est ordures ou recyclage
        # et on retient la plus proche date future pour chacun.
        from datetime import datetime
        import re

        # On va stocker sous forme (date_obj, type) dans deux listes distinctes
        # ou un petit dict.
        ordures_dates = []
        recyclage_dates = []

        # On va supposer qu’on est en 2025 (ou 2024, etc.) => On regarde la caption du tableau.
        # Pour chaque <table> (mois) : ex. "Janvier 2025"
        # On identifie l’année, le mois => on parse jour par <p class='date'>.
        months_map = {
            "janvier": 1,
            "février": 2,
            "fevrier": 2,
            "mars": 3,
            "avril": 4,
            "mai": 5,
            "juin": 6,
            "juillet": 7,
            "aout": 8,
            "août": 8,
            "septembre": 9,
            "octobre": 10,
            "novembre": 11,
            "décembre": 12
        }

        today = datetime.now().date()

        for table in tables:
            caption = table.find("caption").get_text(strip=True) if table.find("caption") else ""
            # Ex: "Janvier 2025"
            parts = caption.lower().split()
            if len(parts) >= 2:
                month_str = parts[0]
                year_str = parts[1]
                month_num = months_map.get(month_str, 0)
                year_num = int(year_str) if year_str.isdigit() else 0
            else:
                # Au cas où
                month_num = 0
                year_num = today.year

            # Parcourir les <td>
            for td in table.find_all("td"):
                date_p = td.find("p", class_="date")
                if not date_p:
                    continue
                day_str = date_p.get_text(strip=True)
                if not day_str.isdigit():
                    continue

                try:
                    day_num = int(day_str)
                    date_obj = datetime(year_num, month_num, day_num).date()
                except:
                    continue

                # Quel type de collecte ?
                picto = td.find("p", class_="img")
                if picto:
                    img = picto.find("img")
                    alt = img.get("alt", "").lower() if img else ""
                    # alt ex: "Ordures et résidus alimentaires", "Recyclage"
                    if "ordures" in alt:
                        ordures_dates.append(date_obj)
                    elif "recyclage" in alt:
                        recyclage_dates.append(date_obj)

        # Trouver la plus proche date future (>= today)
        def next_date(dates):
            futur = [d for d in dates if d >= today]
            if not futur:
                return None
            return min(futur)

        next_ordures = next_date(ordures_dates)
        next_recyclage = next_date(recyclage_dates)

        # Convertir en string
        str_ordures = next_ordures.isoformat() if next_ordures else "N/A"
        str_recyclage = next_recyclage.isoformat() if next_recyclage else "N/A"

        print(f"[INFO] Prochaine ordures: {str_ordures}, Prochain recyclage: {str_recyclage}")

        # === Publier sur MQTT (en découverte auto) ===
        topic_base = "homeassistant/sensor/ville_qc_collecte"

        publish_sensor(
            client,
            topic_base,
            sensor_name="ordures",
            state=str_ordures,
            attributes={"dates": [d.isoformat() for d in sorted(ordures_dates)]}
        )

        publish_sensor(
            client,
            topic_base,
            sensor_name="recyclage",
            state=str_recyclage,
            attributes={"dates": [d.isoformat() for d in sorted(recyclage_dates)]}
        )

    finally:
        driver.quit()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
