FROM python:3.11

COPY . .

RUN pip install .

ENTRYPOINT [ "python", "itchclaim.py" ]
