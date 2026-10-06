"""Ville de Québec – Info-Collecte.

Lit le calendrier de collecte d'une adresse sur le site de la Ville de Québec, publie les
prochaines dates via MQTT Discovery et crée les événements dans un calendrier Home Assistant.
Reads the collection calendar of an address on the Ville de Québec website, publishes the
next dates via MQTT Discovery and creates the events in a Home Assistant calendar.
"""

import json
import os
import re
import signal
import sys
import time
import unicodedata
from datetime import date, datetime

import paho.mqtt.client as mqtt
import requests
from bs4 import BeautifulSoup

OPTIONS_FILE = "/data/options.json"
STATE_FILE = "/data/last_events.json"

URL = "https://www.ville.quebec.qc.ca/services/info-collecte/"
FORM_URL = URL + "index.aspx"
FIELD = "ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$"
HTTP_TIMEOUT = 30

TOPIC_BASE = "homeassistant/sensor/ville_qc_collecte"
AVAILABILITY_TOPIC = f"{TOPIC_BASE}/availability"

MONTHS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
}


class CollecteError(Exception):
    """Erreur claire à afficher / Clear error to display."""


def log(message):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}", flush=True)


def normalize(text):
    """Minuscules, sans accents ni ponctuation / Lowercase, no accents or punctuation."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


# ---------------------------------------------------------------------------
# Site de la Ville (formulaire ASP.NET, sans navigateur)
# City website (ASP.NET form, no browser needed)
# ---------------------------------------------------------------------------

def form_fields(html):
    """Champs cachés du formulaire (__VIEWSTATE, etc.) / Hidden form fields."""
    form = BeautifulSoup(html, "html.parser").find("form", id="aspnetForm")
    if form is None:
        raise CollecteError("Unexpected page from the city website (form not found).")
    return {
        i["name"]: i.get("value", "")
        for i in form.find_all("input")
        if i.get("name") and i.get("type") not in ("submit", "image", "button", "checkbox", "radio")
    }


def pick_address(options, address):
    """Choisit l'adresse dans la liste proposée par le site / Pick the address from the site's list."""
    wanted = normalize(address)
    for value, label in options:
        if normalize(label) == wanted:
            return value, label
    for value, label in options:
        if normalize(label).startswith(wanted) or wanted.startswith(normalize(label)):
            return value, label
    return options[0]


def fetch_calendar_html(address):
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Home Assistant add-on ville_qc_collecte)"
    try:
        page = session.get(URL, timeout=HTTP_TIMEOUT)
        page.raise_for_status()
        data = form_fields(page.text)
        data[FIELD + "txtNomRue"] = address
        data[FIELD + "BtnRue"] = "Rechercher"
        result = session.post(FORM_URL, data=data, timeout=HTTP_TIMEOUT)
        result.raise_for_status()

        # Plusieurs adresses possibles : le site demande de choisir dans une liste
        # Several possible addresses: the site asks to pick one from a list
        soup = BeautifulSoup(result.text, "html.parser")
        choice = soup.find("select", attrs={"name": FIELD + "ddChoix"})
        if choice is not None:
            options = [(o.get("value"), o.get_text(strip=True)) for o in choice.find_all("option") if o.get("value")]
            if not options:
                raise CollecteError(f"Address not found: '{address}'.")
            value, label = pick_address(options, address)
            log(f"Several addresses match, using '{label}'")
            data = form_fields(result.text)
            data[FIELD + "ddChoix"] = value
            data[FIELD + "btnChoix"] = "Poursuivre"
            result = session.post(FORM_URL, data=data, timeout=HTTP_TIMEOUT)
            result.raise_for_status()
        return result.text
    except requests.Timeout as err:
        raise CollecteError(f"The city website did not answer within {HTTP_TIMEOUT} s.") from err
    except requests.ConnectionError as err:
        raise CollecteError("Cannot reach the city website. Is the Internet connection down?") from err
    except requests.HTTPError as err:
        raise CollecteError(f"The city website returned an error: HTTP {err.response.status_code}.") from err


def parse_dates(html, today):
    """Retourne (dates d'ordures, dates de recyclage) / Returns (garbage dates, recycling dates)."""
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table", class_="calendrier")
    if not tables:
        raise CollecteError("No collection calendar for this address. Check the 'address' option.")

    ordures, recyclage = set(), set()
    for table in tables:
        caption = table.find("caption")
        parts = normalize(caption.get_text() if caption else "").split()
        month = MONTHS.get(parts[0], 0) if parts else 0
        year = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else today.year
        for td in table.find_all("td"):
            day = td.find("p", class_="date")
            if not day or not day.get_text(strip=True).isdigit():
                continue
            try:
                current = date(year, month, int(day.get_text(strip=True)))
            except ValueError:
                continue
            for img in td.select("p.img img"):
                alt = normalize(img.get("alt", ""))
                if "ordures" in alt:
                    ordures.add(current)
                if "recyclage" in alt:
                    recyclage.add(current)

    if not ordures and not recyclage:
        raise CollecteError("No collection found in the calendar for this address.")
    return sorted(ordures), sorted(recyclage)


def next_date(dates, today):
    return next((d for d in dates if d >= today), None)


# ---------------------------------------------------------------------------
# Calendrier Home Assistant / Home Assistant calendar
# ---------------------------------------------------------------------------

def ha_api(options):
    """URL et jeton de l'API HA / HA API URL and token.

    Sans jeton configuré, on passe par l'API du Supervisor (homeassistant_api).
    Without a configured token, use the Supervisor API (homeassistant_api).
    """
    if options.get("ha_token"):
        return options.get("ha_url", "").rstrip("/"), options["ha_token"]
    if os.environ.get("SUPERVISOR_TOKEN"):
        return "http://supervisor/core", os.environ["SUPERVISOR_TOKEN"]
    return None, None


def create_event(options, day, summary, description):
    """Appelle script.create_calendar_event dans HA / Call script.create_calendar_event in HA."""
    url, token = ha_api(options)
    response = requests.post(
        f"{url}/api/services/script/turn_on",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "entity_id": "script.create_calendar_event",
            "variables": {
                "calendar_entity": options["ha_calendar_entity"],
                "start_date": day.isoformat(),
                "end_date": day.isoformat(),
                "summary": summary,
                "description": description,
            },
        },
        timeout=HTTP_TIMEOUT,
    )
    if response.status_code != 200:
        raise CollecteError(f"Calendar event not created: HTTP {response.status_code} {response.text[:200]}")
    log(f"Calendar event created: {summary} on {day.isoformat()}")


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as file:
            return json.load(file)
    except (OSError, ValueError):
        return {}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as file:
            json.dump(state, file)
    except OSError as err:
        log(f"WARNING: could not save {STATE_FILE}: {err}")


def update_calendar(options, next_ordures, next_recyclage):
    if not options.get("ha_calendar_entity") or ha_api(options)[0] is None:
        return
    state = load_state()
    for key, day, summary, label_fr in (
        ("ordures", next_ordures, "Collecte ordures", "d'ordures"),
        ("recyclage", next_recyclage, "Collecte recyclage", "de recyclage"),
    ):
        # Un seul événement par date (pas de doublon) / One event per date (no duplicates)
        if day is None or state.get(key) == day.isoformat():
            continue
        try:
            create_event(options, day, summary, f"Prochaine collecte {label_fr} prévue le {day.isoformat()}")
            state[key] = day.isoformat()
        except (CollecteError, requests.RequestException) as err:
            log(f"ERROR: {err}")
    save_state(state)


# ---------------------------------------------------------------------------
# MQTT
# ---------------------------------------------------------------------------

class Publisher:
    """Connexion MQTT persistante avec reconnexion automatique.

    Persistent MQTT connection with automatic reconnection.
    """

    def __init__(self, options):
        self.retained = {}
        self.client = mqtt.Client()
        if options.get("mqtt_username"):
            self.client.username_pw_set(options["mqtt_username"], options.get("mqtt_password") or None)
        # Les capteurs deviennent indisponibles si l'add-on s'arrête
        # Sensors become unavailable if the add-on stops
        self.client.will_set(AVAILABILITY_TOPIC, "offline", retain=True)
        self.client.on_connect = self._on_connect
        self.client.connect_async(options["mqtt_host"], int(options["mqtt_port"]), 60)
        self.client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            log(f"ERROR: MQTT connection refused ({mqtt.connack_string(rc)})")
            return
        log("Connected to MQTT")
        client.publish(AVAILABILITY_TOPIC, "online", retain=True)
        # Republie tout après une reconnexion / Republish everything after a reconnect
        for topic, payload in self.retained.items():
            client.publish(topic, payload, retain=True)

    def _send(self, topic, payload):
        self.retained[topic] = payload
        if self.client.is_connected():
            self.client.publish(topic, payload, retain=True)

    def sensor(self, name, state, attributes, icon):
        # Mêmes unique_id et appareil qu'avant : les entités existantes sont conservées
        # Same unique_id and device as before: existing entities are kept
        base = f"{TOPIC_BASE}/{name}"
        config = {
            "name": f"Collecte {name}",
            "unique_id": f"ville_qc_{name}",
            "state_topic": f"{base}/state",
            "json_attributes_topic": f"{base}/attributes",
            "availability_topic": AVAILABILITY_TOPIC,
            "icon": icon,
            "device": {
                "identifiers": ["ville_qc_collecte_device"],
                "name": "VilleQCCollecte",
                "manufacturer": "Ville de Québec",
            },
        }
        self._send(f"{base}/config", json.dumps(config, ensure_ascii=False))
        self._send(f"{base}/attributes", json.dumps(attributes, ensure_ascii=False))
        self._send(f"{base}/state", state)

    def stop(self):
        if self.client.is_connected():
            self.client.publish(AVAILABILITY_TOPIC, "offline", retain=True).wait_for_publish(5)
        self.client.disconnect()
        self.client.loop_stop()


# ---------------------------------------------------------------------------
# Boucle principale / Main loop
# ---------------------------------------------------------------------------

def run_once(options, publisher):
    today = date.today()
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        ordures, recyclage = parse_dates(fetch_calendar_html(options["address"]), today)
    except CollecteError as err:
        # Le statut vaut exactement « error » (pour les automatisations), le détail est en attribut ;
        # les dernières dates connues sont conservées.
        # Status is exactly "error" (for automations), details are in an attribute;
        # the last known dates are kept.
        log(f"ERROR: {err}")
        publisher.sensor("status", "error", {"message": str(err), "last_check": now}, "mdi:alert-circle")
        return

    next_ordures, next_recyclage = next_date(ordures, today), next_date(recyclage, today)
    log(f"Next garbage: {next_ordures or 'N/A'}, next recycling: {next_recyclage or 'N/A'}")
    publisher.sensor("status", "success", {"message": "OK", "last_check": now, "last_success": now}, "mdi:check-circle")
    publisher.sensor("ordures", next_ordures.isoformat() if next_ordures else "N/A",
                     {"all_dates": [d.isoformat() for d in ordures]}, "mdi:trash-can")
    publisher.sensor("recyclage", next_recyclage.isoformat() if next_recyclage else "N/A",
                     {"all_dates": [d.isoformat() for d in recyclage]}, "mdi:recycle")
    update_calendar(options, next_ordures, next_recyclage)


def main():
    with open(OPTIONS_FILE, encoding="utf-8") as file:
        options = json.load(file)
    interval = max(300, int(options.get("update_interval", 3600)))
    log(f"Starting Ville de Québec collecte (address: {options['address']}, every {interval} s)")

    publisher = Publisher(options)

    def shutdown(signum, frame):
        log("Stopping")
        publisher.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while True:
        try:
            run_once(options, publisher)
        except Exception as err:  # noqa: BLE001 - l'add-on ne doit jamais s'arrêter / must never stop
            log(f"ERROR: unexpected error: {err!r}")
        time.sleep(interval)


if __name__ == "__main__":
    main()
