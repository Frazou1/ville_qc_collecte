# On part d'une image Python légère
FROM python:3.11-slim

# Installations système pour que Chrome/Chromium + Selenium fonctionnent
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Installer les packages Python nécessaires
RUN pip install --no-cache-dir selenium==4.* webdriver-manager==4.* \
    beautifulsoup4 paho-mqtt

# Copier les fichiers de l'add-on
COPY run.sh /run.sh
COPY script.py /script.py

# Rendre exécutable
RUN chmod a+x /run.sh

# Point d'entrée
CMD [ "/run.sh" ]
