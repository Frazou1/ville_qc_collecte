FROM python:3.12-slim

# Plus besoin de Chromium : le site est lu en HTTP simple
# Chromium no longer needed: the website is read over plain HTTP
RUN pip install --no-cache-dir requests beautifulsoup4 paho-mqtt==1.6.1

COPY script.py /script.py

# -u : journaux non mis en tampon / unbuffered logs
CMD [ "python3", "-u", "/script.py" ]
