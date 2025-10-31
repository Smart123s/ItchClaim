# Use FlareSolverr base image
# It's a python based image with Chromium and all dependencies preinstalled
FROM ghcr.io/flaresolverr/flaresolverr:v3.4.3

USER root

# Delete flaresolverr app directory
# It will be replaced with ItchClaim app
# FlareSolverr will be installed via pip
RUN rm -rf /app

ENV ITCHCLAIM_DOCKER=TRUE

WORKDIR /app

# Temporarily a fork of FlareSolverr is used, built from git source
RUN apt update && \
    apt install -y git && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1

COPY . .

VOLUME [ "/data" ]

ENTRYPOINT [ "python", "itchclaim.py" ]
