# Use FlareSolverr base image
# It's a python based image with Chromium and all dependencies preinstalled
FROM ghcr.io/flaresolverr/flaresolverr:v3.4.6

USER root

# Delete flaresolverr app directory from base image
# FlareSolverr is included in ItchClaim as a git submodule
RUN rm -rf /app

ENV ITCHCLAIM_DOCKER=TRUE

WORKDIR /app

COPY requirements.txt .

# FlareSolverr dependencies are included in the base image
# note: FROM ghcr.io/flaresolverr/flaresolverr:v3.4.3
RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=1

COPY . .

VOLUME [ "/data" ]

ENTRYPOINT [ "python", "itchclaim.py" ]
