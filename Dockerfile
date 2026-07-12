# Use FlareSolverr base image
# It's a python based image with Chromium and all dependencies preinstalled
FROM ghcr.io/flaresolverr/flaresolverr:v3.5.0

USER root

# Delete flaresolverr app directory from base image.
# FlareSolverr is included in ItchClaim as a git submodule.
# Preserve /app/chromedriver from the base image
RUN cp -a /app/chromedriver /tmp/chromedriver \
    && rm -rf /app \
    && mkdir -p /app \
    && mv /tmp/chromedriver /app/chromedriver

ENV ITCHCLAIM_DOCKER=TRUE

WORKDIR /app

COPY requirements.txt .

# FlareSolverr dependencies are included in the base image
# note: FROM ghcr.io/flaresolverr/flaresolverr
RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1

COPY . .

VOLUME [ "/data" ]

ENTRYPOINT [ "python", "itchclaim.py" ]
