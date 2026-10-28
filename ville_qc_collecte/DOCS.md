# Ville de Québec – Info-Collecte (module complémentaire Home Assistant / Home Assistant add-on)

[Français](#français) | [English](#english)

---

## Français

### Description

Module complémentaire (add-on) Home Assistant qui lit le calendrier de collecte des **ordures** et du **recyclage** d'une adresse sur le site [Info-Collecte de la Ville de Québec](https://www.ville.quebec.qc.ca/services/info-collecte/). Il publie les prochaines dates dans Home Assistant par **MQTT** (les capteurs apparaissent tout seuls grâce à MQTT Discovery) et peut, en option, ajouter chaque collecte à un **calendrier** Home Assistant.

Le site de la Ville est lu en HTTP simple (formulaire de recherche d'adresse, puis lecture des tableaux du calendrier) : aucun navigateur n'est nécessaire.

### Fonctionnalités

- Prochaine date de collecte des ordures et du recyclage, en capteurs MQTT découverts automatiquement.
- Toutes les dates connues du calendrier affiché par la Ville, dans l'attribut `all_dates`.
- Capteur de statut (`success` / `error`) avec un message d'erreur clair dans l'attribut `message`.
- En cas d'erreur, les dernières dates connues sont conservées.
- Capteurs « indisponibles » quand l'add-on est arrêté ; connexion MQTT persistante avec reconnexion automatique.
- Si plusieurs adresses correspondent (ex. appartements), la meilleure correspondance est choisie et indiquée dans le journal.
- Option : création d'un événement de calendrier par nouvelle date de collecte, sans doublon.

### Installation

**Prérequis :** un broker MQTT (ex. le module complémentaire **Mosquitto broker**) et l'intégration **MQTT** configurée dans Home Assistant.

1. Allez dans **Paramètres → Modules complémentaires → Boutique des modules complémentaires → ⋮ (en haut à droite) → Dépôts** et ajoutez `https://github.com/Frazou1/ville_qc_collecte`.
2. Rafraîchissez la boutique, puis installez **Ville Quebec Collecte Add-on**.
3. Remplissez l'onglet **Configuration** (au minimum `address`).
4. Démarrez l'add-on et consultez l'onglet **Journal**.

### Configuration

| Option | Type | Défaut | Rôle |
|---|---|---|---|
| `address` | texte (requis) | *(vide)* | Votre adresse civique, écrite comme dans la recherche du site Info-Collecte (ex. `1234 rue Exemple`). |
| `update_interval` | entier (secondes) | `3600` | Délai entre deux lectures du site. Minimum appliqué par le code : `300`. |
| `mqtt_host` | texte | `core-mosquitto` | Nom d'hôte du broker MQTT. `core-mosquitto` = add-on Mosquitto. |
| `mqtt_port` | port | `1883` | Port du broker MQTT. |
| `mqtt_username` | texte (optionnel) | *(vide)* | Utilisateur MQTT ; vide si le broker n'exige pas d'authentification. |
| `mqtt_password` | mot de passe (optionnel) | *(vide)* | Mot de passe MQTT (masqué). |
| `ha_calendar_entity` | texte (optionnel) | *(vide)* | Calendrier où créer les événements (ex. `calendar.collectes`). Vide = fonction désactivée. |
| `ha_url` | texte (optionnel) | *(vide)* | URL de Home Assistant. **Seulement** si vous fournissez `ha_token`. |
| `ha_token` | mot de passe (optionnel) | *(vide)* | Jeton d'accès longue durée. Vide = l'add-on utilise son accès intégré au Supervisor (recommandé). |

Exemple :

```yaml
address: "1234 rue Exemple"
update_interval: 3600
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_username: ""
mqtt_password: ""
ha_calendar_entity: calendar.collectes
ha_url: ""
ha_token: ""
```

**Accès à Home Assistant :** l'add-on déclare `homeassistant_api: true`. Si `ha_token` est vide, il appelle l'API de Home Assistant par `http://supervisor/core` avec le jeton fourni par le Supervisor (`SUPERVISOR_TOKEN`) : rien à configurer. Cet accès ne sert qu'aux événements de calendrier ; les capteurs passent uniquement par MQTT.

#### Événements de calendrier (optionnel)

Quand `ha_calendar_entity` est rempli, l'add-on appelle le script **`script.create_calendar_event`** une fois par nouvelle date de collecte (prochaine date d'ordures et prochaine date de recyclage) avec les variables `calendar_entity`, `start_date`, `end_date`, `summary` (`Collecte ordures` ou `Collecte recyclage`) et `description`. **Ce script doit exister** dans Home Assistant, avec exactement cet identifiant. Exemple (événement de 7 h à 7 h 30) :

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

Le calendrier doit accepter la création d'événements (ex. intégration **Calendrier local**). La dernière date créée pour chaque type est mémorisée dans `/data/last_events.json` : un même événement n'est pas recréé.

### Entités créées

Toutes les entités sont rattachées à l'appareil MQTT **VilleQCCollecte** (fabricant « Ville de Québec »).

| Entité (identifiant habituel) | Nom | État | Attributs |
|---|---|---|---|
| `sensor.villeqccollecte_collecte_ordures` | Collecte ordures | Prochaine date (`AAAA-MM-JJ`) ou `N/A` | `all_dates` (liste de dates) |
| `sensor.villeqccollecte_collecte_recyclage` | Collecte recyclage | Prochaine date (`AAAA-MM-JJ`) ou `N/A` | `all_dates` |
| `sensor.villeqccollecte_collecte_status` | Collecte status | `success` ou `error` | `message`, `last_check`, `last_success` (seulement après un succès) |

Les identifiants uniques sont `ville_qc_ordures`, `ville_qc_recyclage` et `ville_qc_status`. L'identifiant d'entité exact dépend de votre version de Home Assistant et de vos renommages : vérifiez-le dans **Paramètres → Appareils et services → Entités** (recherche « Collecte »). `N/A` signifie qu'aucune date future ne figure dans le calendrier publié par la Ville.

### Exemples d'utilisation

Carte Lovelace :

```yaml
type: entities
title: Collectes
entities:
  - entity: sensor.villeqccollecte_collecte_ordures
    name: Ordures
  - entity: sensor.villeqccollecte_collecte_recyclage
    name: Recyclage
  - entity: sensor.villeqccollecte_collecte_status
    name: Statut
```

Rappel la veille de la collecte des ordures, à 19 h (remplacez `notify.notify` par votre service de notification) :

```yaml
alias: Rappel - ordures demain
triggers:
  - trigger: time
    at: "19:00:00"
conditions:
  - condition: template
    value_template: >
      {{ states('sensor.villeqccollecte_collecte_ordures')
         == (now().date() + timedelta(days=1)).isoformat() }}
actions:
  - action: notify.notify
    data:
      message: "Collecte des ordures demain : sortez le bac."
mode: single
```

Alerte quand la lecture du site échoue :

```yaml
alias: Ville QC Collecte - erreur
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

### Dépannage

Consultez l'onglet **Journal** de l'add-on. Chaque ligne est horodatée ; les erreurs commencent par `ERROR:` et sont aussi copiées dans l'attribut `message` du capteur de statut.

| Message (journal) | Cause / quoi faire |
|---|---|
| `No collection calendar for this address. Check the 'address' option.` | Adresse non reconnue par le site. Tapez-la sur le site Info-Collecte et recopiez exactement la même forme dans `address`. |
| `Address not found: '…'.` | Le site a proposé une liste d'adresses vide. Vérifiez l'orthographe. |
| `Several addresses match, using '…'` | Information : plusieurs adresses correspondent ; vérifiez que celle retenue est la bonne, sinon précisez `address`. |
| `No collection found in the calendar for this address.` | Le calendrier est affiché mais sans collecte reconnue (ordures / recyclage). |
| `Unexpected page from the city website (form not found).` | Le site de la Ville a changé de structure ou est en maintenance. |
| `The city website did not answer within 30 s.` / `Cannot reach the city website…` / `The city website returned an error: HTTP …` | Problème réseau ou site indisponible ; nouvel essai au prochain intervalle. |
| `ERROR: MQTT connection refused (…)` | Mauvais hôte, port, utilisateur ou mot de passe MQTT. |
| `Calendar event not created: HTTP …` | Accès à Home Assistant refusé (`401`) ou script `script.create_calendar_event` en erreur. Si vous utilisez `ha_token`, vérifiez aussi `ha_url`. |

Aucune entité n'apparaît ? Vérifiez que l'intégration MQTT est installée et que le journal affiche `Connected to MQTT`.

### Limites connues

- Ville de Québec seulement ; seules les collectes d'**ordures** et de **recyclage** sont lues (pas les autres types de collecte).
- L'add-on lit les pages HTML du site : une refonte du site peut le briser jusqu'à une mise à jour.
- Les événements de calendrier ne sont créés que pour la **prochaine** date de chaque type, au fil des lectures.
- Le slug technique de l'add-on est `example` (conservé pour ne pas perdre la configuration des installations existantes).

### Revenir à une version précédente

Le dépôt ne publie pas d'étiquettes (tags) de version. Pour revenir en arrière, cochez l'option de sauvegarde au moment de la mise à jour de l'add-on, puis restaurez cette sauvegarde dans **Paramètres → Système → Sauvegardes**. L'historique des changements est dans [CHANGELOG.md](https://github.com/Frazou1/ville_qc_collecte/blob/main/ville_qc_collecte/CHANGELOG.md).

### Licence

Apache License 2.0 — voir [LICENSE](https://github.com/Frazou1/ville_qc_collecte/blob/main/LICENSE).

---

## English

### Description

Home Assistant add-on that reads the **garbage** and **recycling** collection calendar of an address on the [Ville de Québec Info-Collecte](https://www.ville.quebec.qc.ca/services/info-collecte/) website. It publishes the next dates to Home Assistant over **MQTT** (sensors appear automatically through MQTT Discovery) and can optionally add each collection to a Home Assistant **calendar**.

The city website is read over plain HTTP (address search form, then the calendar tables): no browser is needed.

### Features

- Next garbage and recycling collection date as auto-discovered MQTT sensors.
- Every known date from the calendar shown by the city, in the `all_dates` attribute.
- Status sensor (`success` / `error`) with a clear error message in the `message` attribute.
- On an error, the last known dates are kept.
- Sensors become unavailable when the add-on is stopped; persistent MQTT connection with automatic reconnection.
- When several addresses match (e.g. apartments), the best match is picked and written to the log.
- Optional: one calendar event per new collection date, without duplicates.

### Installation

**Prerequisites:** an MQTT broker (e.g. the **Mosquitto broker** add-on) and the **MQTT** integration set up in Home Assistant.

1. Go to **Settings → Add-ons → Add-on Store → ⋮ (top right) → Repositories** and add `https://github.com/Frazou1/ville_qc_collecte`.
2. Refresh the store, then install **Ville Quebec Collecte Add-on**.
3. Fill in the **Configuration** tab (at least `address`).
4. Start the add-on and check the **Log** tab.

### Configuration

| Option | Type | Default | Purpose |
|---|---|---|---|
| `address` | text (required) | *(empty)* | Your civic address, typed as in the Info-Collecte website search (e.g. `1234 rue Exemple`). |
| `update_interval` | integer (seconds) | `3600` | Delay between two reads of the website. Minimum enforced by the code: `300`. |
| `mqtt_host` | text | `core-mosquitto` | MQTT broker hostname. `core-mosquitto` = Mosquitto add-on. |
| `mqtt_port` | port | `1883` | MQTT broker port. |
| `mqtt_username` | text (optional) | *(empty)* | MQTT username; empty if the broker requires no authentication. |
| `mqtt_password` | password (optional) | *(empty)* | MQTT password (hidden). |
| `ha_calendar_entity` | text (optional) | *(empty)* | Calendar where events are created (e.g. `calendar.collections`). Empty = feature disabled. |
| `ha_url` | text (optional) | *(empty)* | Home Assistant URL. **Only** when you provide `ha_token`. |
| `ha_token` | password (optional) | *(empty)* | Long-lived access token. Empty = the add-on uses its built-in Supervisor access (recommended). |

Example:

```yaml
address: "1234 rue Exemple"
update_interval: 3600
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_username: ""
mqtt_password: ""
ha_calendar_entity: calendar.collections
ha_url: ""
ha_token: ""
```

**Home Assistant access:** the add-on declares `homeassistant_api: true`. When `ha_token` is empty, it calls the Home Assistant API through `http://supervisor/core` with the token provided by the Supervisor (`SUPERVISOR_TOKEN`): nothing to set up. This access is only used for calendar events; sensors go through MQTT only.

#### Calendar events (optional)

When `ha_calendar_entity` is set, the add-on calls the **`script.create_calendar_event`** script once per new collection date (next garbage date and next recycling date) with the variables `calendar_entity`, `start_date`, `end_date`, `summary` (`Collecte ordures` or `Collecte recyclage`) and `description`. **This script must exist** in Home Assistant with exactly that ID. Example (event from 7:00 to 7:30 AM):

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

The calendar must support creating events (e.g. the **Local Calendar** integration). The last date created for each type is stored in `/data/last_events.json`, so the same event is not created twice.

### Created entities

All entities belong to the **VilleQCCollecte** MQTT device (manufacturer "Ville de Québec").

| Entity (usual ID) | Name | State | Attributes |
|---|---|---|---|
| `sensor.villeqccollecte_collecte_ordures` | Collecte ordures (garbage) | Next date (`YYYY-MM-DD`) or `N/A` | `all_dates` (list of dates) |
| `sensor.villeqccollecte_collecte_recyclage` | Collecte recyclage (recycling) | Next date (`YYYY-MM-DD`) or `N/A` | `all_dates` |
| `sensor.villeqccollecte_collecte_status` | Collecte status | `success` or `error` | `message`, `last_check`, `last_success` (only after a success) |

The unique IDs are `ville_qc_ordures`, `ville_qc_recyclage` and `ville_qc_status`. The exact entity ID depends on your Home Assistant version and any renaming: check it in **Settings → Devices & services → Entities** (search for "Collecte"). `N/A` means no future date is listed in the calendar published by the city.

### Usage examples

Lovelace card:

```yaml
type: entities
title: Collections
entities:
  - entity: sensor.villeqccollecte_collecte_ordures
    name: Garbage
  - entity: sensor.villeqccollecte_collecte_recyclage
    name: Recycling
  - entity: sensor.villeqccollecte_collecte_status
    name: Status
```

Reminder the evening before garbage collection, at 7 PM (replace `notify.notify` with your notification service):

```yaml
alias: Reminder - garbage tomorrow
triggers:
  - trigger: time
    at: "19:00:00"
conditions:
  - condition: template
    value_template: >
      {{ states('sensor.villeqccollecte_collecte_ordures')
         == (now().date() + timedelta(days=1)).isoformat() }}
actions:
  - action: notify.notify
    data:
      message: "Garbage collection tomorrow: put the bin out."
mode: single
```

Alert when reading the website fails:

```yaml
alias: Ville QC Collecte - error
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

### Troubleshooting

Check the add-on's **Log** tab. Every line is timestamped; errors start with `ERROR:` and are also copied to the `message` attribute of the status sensor.

| Log message | Cause / what to do |
|---|---|
| `No collection calendar for this address. Check the 'address' option.` | Address not recognised by the website. Type it on the Info-Collecte website and copy exactly the same form into `address`. |
| `Address not found: '…'.` | The website offered an empty list of addresses. Check the spelling. |
| `Several addresses match, using '…'` | Information: several addresses match; make sure the chosen one is right, otherwise make `address` more specific. |
| `No collection found in the calendar for this address.` | The calendar is shown but contains no recognised collection (garbage / recycling). |
| `Unexpected page from the city website (form not found).` | The city website changed its layout or is under maintenance. |
| `The city website did not answer within 30 s.` / `Cannot reach the city website…` / `The city website returned an error: HTTP …` | Network problem or website down; retried at the next interval. |
| `ERROR: MQTT connection refused (…)` | Wrong MQTT host, port, username or password. |
| `Calendar event not created: HTTP …` | Home Assistant access refused (`401`) or the `script.create_calendar_event` script failed. If you use `ha_token`, also check `ha_url`. |

No entity shows up? Make sure the MQTT integration is installed and that the log shows `Connected to MQTT`.

### Known limitations

- Québec City only; only **garbage** and **recycling** collections are read (no other collection types).
- The add-on reads the website's HTML pages: a website redesign can break it until an update.
- Calendar events are only created for the **next** date of each type, as reads go by.
- The add-on's technical slug is `example` (kept so existing installations keep their configuration).

### Rolling back to a previous version

The repository does not publish version tags. To roll back, tick the backup option when updating the add-on, then restore that backup in **Settings → System → Backups**. The change history is in [CHANGELOG.md](https://github.com/Frazou1/ville_qc_collecte/blob/main/ville_qc_collecte/CHANGELOG.md).

### License

Apache License 2.0 — see [LICENSE](https://github.com/Frazou1/ville_qc_collecte/blob/main/LICENSE).

