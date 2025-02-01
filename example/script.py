import argparse
import json
import time

import paho.mqtt.client as mqtt

# Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
from datetime import datetime, date

def publish_sensor(client, topic_base, sensor_name, state, attributes=None):
    """
    Publie un capteur via MQTT Discovery.
    
    - 'topic_base' : ex "homeassistant/sensor/ville_qc_collecte"
    - 'sensor_name': "ordures", "recyclage", ou "status"
    - 'state'      : la valeur du capteur (string)
    - 'attributes' : dict supplémentaire (pour attributs JSON)
    """
    config_topic = f"{topic_base}/{sensor_name}/config"
    state_topic = f"{topic_base}/{sensor_name}/state"
    attr_topic = f"{topic_base}/{sensor_name}/attributes"

    device_name = "VilleQCCollecte"
    unique_id = f"ville_qc_{sensor_name}"

    # Construction du payload de config
    config_payload = {
        "name": f"Collecte {sensor_name}",
        "state_topic": state_topic,
        "unique_id": unique_id,
        "device": {
            "identifiers": ["ville_qc_collecte_device"],
            "name": device_name,
            "manufacturer": "Ville de Québec"
        }
    }

    # Gérer les attributs sous forme JSON
    if attributes:
        config_payload["json_attributes_topic"] = attr_topic
        client.publish(attr_topic, json.dumps(attributes), retain=True)
    else:
        # S'il n'y a pas d'attribut, on peut laisser de côté l'attr_topic
        pass

    # Publier la config (retenue pour que HA la détecte durablement)
    client.publish(config_topic, json.dumps(config_payload), retain=True)

    # Publier l'état (retenu aussi)
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

    print(f"[SCRIPT] Démarrage avec adresse={ADDRESS}")

    # Connexion MQTT
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

    # On définit un statut par défaut à "success". En cas d'erreur, on le change.
    status = "success"

    ordures_dates = []
    recyclage_dates = []

    try:
        # Selenium en mode headless
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        service = Service("/usr/bin/chromedriver")  # Ou le chemin où se trouve ton chromedriver

        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Accéder à la page
        url_main = "https://www.ville.quebec.qc.ca/services/info-collecte/"
        print(f"[SCRIPT] Accès: {url_main}")
        driver.get(url_main)

        # Trouver le champ d'adresse
        field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.NAME,
                "ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$txtNomRue"
            ))
        )
        field.clear()
        field.send_keys(ADDRESS)

        # Bouton Rechercher
        search_button = driver.find_element(
            By.NAME,
            "ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$BtnRue"
        )
        search_button.click()

        # Attendre le calendrier
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.calendrier"))
        )
        print("[SCRIPT] Calendrier détecté.")

        # Parser
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tables = soup.find_all("table", class_="calendrier")
        if not tables:
            raise RuntimeError("Aucune table 'calendrier' trouvée !")

        # Mapping de mois (en minuscule) -> numéro
        months_map = {
            "janvier": 1, "février": 2, "fevrier": 2, "mars": 3,
            "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
            "aout": 8, "août": 8, "septembre": 9, "octobre": 10,
            "novembre": 11, "décembre": 12
        }

        today = date.today()

        for table in tables:
            caption = table.find("caption")
            if caption:
                caption_txt = caption.get_text(strip=True).lower()
            else:
                caption_txt = ""

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

        # Vérifier si on a trouvé au moins une date
        if not ordures_dates and not recyclage_dates:
            raise ValueError("Aucune collecte trouvée pour l'adresse donnée.")

        # Déterminer la prochaine date >= today
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
        # Fermer Selenium si on l’a ouvert
        try:
            driver.quit()
        except:
            pass

    # Publication MQTT
    topic_base = "homeassistant/sensor/ville_qc_collecte"

    # 1) Capteur "status" (pour surveiller succès / erreur)
    publish_sensor(
        client,
        topic_base,
        "status",
        state=status,
        attributes={}
    )

    # 2) Capteur "ordures"
    # S’il y a un statut d’erreur, on peut publier "N/A" ou la dernière date connue
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

    # 3) Capteur "recyclage"
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

    # Clean up MQTT
    client.loop_stop()
    client.disconnect()
    print("[SCRIPT] Terminé.")

if __name__ == "__main__":
    main()
