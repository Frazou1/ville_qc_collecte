<!-- https://developers.home-assistant.io/docs/add-ons/presentation#keeping-a-changelog -->

## 1.4.0

- No more Chromium/Selenium: the city website is read over plain HTTP (much smaller image, faster, more reliable) / Plus de Chromium ni Selenium : le site de la Ville est lu en HTTP simple (image beaucoup plus légère, plus rapide et plus fiable)
- When several addresses match (e.g. apartments), the best match is picked automatically / Quand plusieurs adresses correspondent (ex. appartements), la meilleure est choisie automatiquement
- Fix: the status sensor is now exactly `error` on failure (it was `error: <message>`, so automations on `error` never fired); the explanation is in the `message` attribute / Correction : le statut vaut maintenant exactement `error` en cas d'échec (il valait `error: <message>`, donc les automatisations sur `error` ne se déclenchaient jamais) ; l'explication est dans l'attribut `message`
- On an error, the last known dates are kept instead of `error` / En cas d'erreur, les dernières dates connues sont conservées au lieu de `error`
- Sensors become unavailable when the add-on stops; persistent MQTT connection with automatic reconnection / Capteurs indisponibles quand l'add-on s'arrête ; connexion MQTT persistante avec reconnexion automatique
- Calendar events can use the add-on's built-in Home Assistant access: `ha_url` and `ha_token` are now optional / Les événements de calendrier peuvent utiliser l'accès intégré de l'add-on : `ha_url` et `ha_token` sont maintenant optionnels
- Passwords and token hidden in the configuration screen, which is now translated (English, French) / Mots de passe et jeton masqués dans l'écran de configuration, maintenant traduit (anglais, français)

## 1.3.1

- Remove loop to read 2 events on the same date / Retrait de la boucle qui lisait 2 événements à la même date

## 1.3.0

- Read the icons of the calendar and insert the events into a calendar / Lecture des icônes du calendrier et ajout des événements à un calendrier

## 1.0.0

- Initial release / Version initiale
