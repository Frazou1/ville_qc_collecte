# Ville de Québec – Info-Collecte (Home Assistant add-on)

[English](#english) · [Français](#français)

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FFrazou1%2Fville_qc_collecte)

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armhf Architecture][armhf-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

---

## English

Home Assistant add-on that reads the garbage and recycling collection calendar of your address on the [Ville de Québec Info-Collecte](https://www.ville.quebec.qc.ca/services/info-collecte/) website.

- Next garbage and recycling dates as MQTT sensors (auto-discovered)
- Status sensor (`success` / `error`) with a clear error message
- Optional: collection events added to a Home Assistant calendar, without duplicates
- Lightweight: the website is read over plain HTTP, no browser needed

### Installation

1. Click the button above, or go to **Settings → Add-ons → Add-on Store → ⋮ → Repositories** and add `https://github.com/Frazou1/ville_qc_collecte`.
2. Install **Ville Quebec Collecte Add-on**.
3. Fill in the **Configuration** tab (your address, MQTT broker, optional calendar).
4. Start the add-on and check its logs.

Full documentation: [ville_qc_collecte/DOCS.md](ville_qc_collecte/DOCS.md) (also shown in the add-on's **Documentation** tab).

---

## Français

Add-on Home Assistant qui lit le calendrier de collecte des ordures et du recyclage de votre adresse sur le site [Info-Collecte de la Ville de Québec](https://www.ville.quebec.qc.ca/services/info-collecte/).

- Prochaines dates d'ordures et de recyclage en capteurs MQTT (découverts automatiquement)
- Capteur de statut (`success` / `error`) avec un message d'erreur clair
- Optionnel : événements de collecte ajoutés à un calendrier Home Assistant, sans doublon
- Léger : le site est lu en HTTP simple, sans navigateur

### Installation

1. Cliquez sur le bouton ci-dessus, ou allez dans **Paramètres → Modules complémentaires → Boutique → ⋮ → Dépôts** et ajoutez `https://github.com/Frazou1/ville_qc_collecte`.
2. Installez **Ville Quebec Collecte Add-on**.
3. Remplissez l'onglet **Configuration** (votre adresse, broker MQTT, calendrier optionnel).
4. Démarrez l'add-on et consultez son journal.

Documentation complète : [ville_qc_collecte/DOCS.md](ville_qc_collecte/DOCS.md) (aussi affichée dans l'onglet **Documentation** de l'add-on).

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg
