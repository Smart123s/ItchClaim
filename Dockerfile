FROM python:3.12

ENV ITCHCLAIM_DOCKER TRUE

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED 1

COPY . .

VOLUME [ "/data" ]

ENTRYPOINT [ "python", "itchclaim.py" ]
