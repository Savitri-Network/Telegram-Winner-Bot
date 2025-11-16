FROM python:3.11-slim

WORKDIR /app

# Copia requirements e invalida la cache quando cambiano
COPY requirements.txt /app/requirements.txt
ARG PIP_REINSTALL=1
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r /app/requirements.txt

# Copia il codice
COPY . /app

# Rende opzionale l'entrypoint
RUN chmod +x /app/entrypoint.sh || true

ENV PYTHONUNBUFFERED=1 TZ=UTC

ENTRYPOINT ["/app/entrypoint.sh"]
