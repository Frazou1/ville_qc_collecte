#!/usr/bin/env bash
set -e

OPTIONS_FILE="/data/options.json"

ADDRESS="$(jq -r '.address' $OPTIONS_FILE)"
UPDATE_INTERVAL="$(jq -r '.update_interval' $OPTIONS_FILE)"
MQTT_HOST="$(jq -r '.mqtt_host' $OPTIONS_FILE)"
MQTT_PORT="$(jq -r '.mqtt_port' $OPTIONS_FILE)"
MQTT_USER="$(jq -r '.mqtt_username' $OPTIONS_FILE)"
MQTT_PASS="$(jq -r '.mqtt_password' $OPTIONS_FILE)"
CALENDAR_FILE="$(jq -r '.calendar_file' $OPTIONS_FILE)"  # Nouvelle option

echo "[INFO] Démarrage de l'add-on Ville Québec Collecte"
echo "[INFO] Adresse = $ADDRESS"
echo "[INFO] Intervalle = $UPDATE_INTERVAL"
echo "[INFO] MQTT = $MQTT_HOST:$MQTT_PORT"
echo "[INFO] Fichier calendrier ICS = $CALENDAR_FILE"

while true; do
    echo "[INFO] Exécution du script Python..."
    python /script.py \
      --address "$ADDRESS" \
      --mqtt_host "$MQTT_HOST" \
      --mqtt_port "$MQTT_PORT" \
      --mqtt_user "$MQTT_USER" \
      --mqtt_pass "$MQTT_PASS" \
      --calendar_file "$CALENDAR_FILE"  # Passage du chemin du fichier ICS

    echo "[INFO] Attente $UPDATE_INTERVAL secondes..."
    sleep "$UPDATE_INTERVAL"
done
