# Ville de Québec – Info-Collecte

[English](#english) · [Français](#français)

---

## English

This add-on reads the garbage and recycling collection calendar of your address on the [Ville de Québec Info-Collecte](https://www.ville.quebec.qc.ca/services/info-collecte/) website, publishes the next dates to Home Assistant over MQTT (sensors are discovered automatically) and can add the collections to a Home Assistant calendar.

### Configuration

| Option | Description | Default |
|---|---|---|
| `address` | Your civic address, as typed on the Info-Collecte website (e.g. `430 4e rue`) | |
| `update_interval` | Seconds between two checks (minimum 300) | `3600` |
| `mqtt_host` / `mqtt_port` | MQTT broker | `core-mosquitto` / `1883` |
| `mqtt_username` / `mqtt_password` | MQTT credentials (optional) | |
| `ha_calendar_entity` | Calendar where events are created (optional, e.g. `calendar.my_calendar`) | |
| `ha_url` / `ha_token` | Optional. Leave empty: the add-on uses its built-in Home Assistant access | |

If the website offers several addresses (e.g. apartments), the add-on picks the one that matches `address` best and writes it in the log.

### Sensors

| Entity | State | Attributes |
|---|---|---|
| `sensor.villeqccollecte_collecte_ordures` | Next garbage date (`YYYY-MM-DD`) | `all_dates` |
| `sensor.villeqccollecte_collecte_recyclage` | Next recycling date (`YYYY-MM-DD`) | `all_dates` |
| `sensor.villeqccollecte_collecte_status` | `success` or `error` | `message` (clear explanation), `last_check`, `last_success` |

On an error, the last known dates are kept. All sensors become unavailable when the add-on is stopped.

### Calendar events

When `ha_calendar_entity` is set, the add-on calls the Home Assistant script `script.create_calendar_event` once per new collection date. Create this script in Home Assistant:

```yaml
alias: Create calendar event
mode: queued
fields:
  calendar_entity: {}
  start_date: {}
  end_date: {}
  summary: {}
  description: {}
sequence:
  - action: calendar.create_event
    data:
      entity_id: "{{ calendar_entity }}"
      start_date_time: "{{ start_date }}T07:00:00"
      end_date_time: "{{ end_date }}T07:30:00"
      summary: "{{ summary }}"
      description: "{{ description }}"
```

### Automation example

```yaml
alias: Ville QC Collecte – error
triggers:
  - trigger: state
    entity_id: sensor.villeqccollecte_collecte_status
    to: error
actions:
  - action: persistent_notification.create
    data:
      title: Ville QC Collecte
      message: "{{ state_attr('sensor.villeqccollecte_collecte_status', 'message') }}"
```

---

## Français

Cet add-on lit le calendrier de collecte des ordures et du recyclage de votre adresse sur le site [Info-Collecte de la Ville de Québec](https://www.ville.quebec.qc.ca/services/info-collecte/), publie les prochaines dates dans Home Assistant via MQTT (capteurs découverts automatiquement) et peut ajouter les collectes à un calendrier Home Assistant.

### Configuration

| Option | Description | Défaut |
|---|---|---|
| `address` | Votre adresse civique, comme sur le site Info-Collecte (ex. `430 4e rue`) | |
| `update_interval` | Secondes entre deux vérifications (minimum 300) | `3600` |
| `mqtt_host` / `mqtt_port` | Broker MQTT | `core-mosquitto` / `1883` |
| `mqtt_username` / `mqtt_password` | Identifiants MQTT (optionnels) | |
| `ha_calendar_entity` | Calendrier où créer les événements (optionnel, ex. `calendar.mon_calendrier`) | |
| `ha_url` / `ha_token` | Optionnels. Laisser vides : l'add-on utilise son accès intégré à Home Assistant | |

Si le site propose plusieurs adresses (ex. appartements), l'add-on choisit celle qui correspond le mieux à `address` et l'indique dans le journal.

### Capteurs

| Entité | État | Attributs |
|---|---|---|
| `sensor.villeqccollecte_collecte_ordures` | Prochaine date d'ordures (`AAAA-MM-JJ`) | `all_dates` |
| `sensor.villeqccollecte_collecte_recyclage` | Prochaine date de recyclage (`AAAA-MM-JJ`) | `all_dates` |
| `sensor.villeqccollecte_collecte_status` | `success` ou `error` | `message` (explication claire), `last_check`, `last_success` |

En cas d'erreur, les dernières dates connues sont conservées. Tous les capteurs deviennent indisponibles quand l'add-on est arrêté.

### Événements de calendrier

Quand `ha_calendar_entity` est rempli, l'add-on appelle le script Home Assistant `script.create_calendar_event` une fois par nouvelle date de collecte. Créez ce script dans Home Assistant (voir l'exemple en anglais ci-dessus).

### Exemple d'automatisation

```yaml
alias: Ville QC Collecte – erreur
triggers:
  - trigger: state
    entity_id: sensor.villeqccollecte_collecte_status
    to: error
actions:
  - action: persistent_notification.create
    data:
      title: Ville QC Collecte
      message: "{{ state_attr('sensor.villeqccollecte_collecte_status', 'message') }}"
```
