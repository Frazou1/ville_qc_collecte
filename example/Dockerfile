FROM python:3.11-slim

# Installer Chromium et son driver
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    fonts-liberation \
    libnss3 \
    libxss1 \
    libgtk2.0-0 \
    libgbm-dev \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Installer les packages Python
RUN pip install --no-cache-dir selenium==4.* webdriver-manager==4.* \
    beautifulsoup4 paho-mqtt

# Copier les fichiers de l’add-on
COPY run.sh /run.sh
COPY script.py /script.py

RUN chmod a+x /run.sh

# Commande lancée au démarrage du conteneur
CMD [ "/run.sh" ]
