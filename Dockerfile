FROM python:3.9.0

RUN mkdir /essim-external-model/
WORKDIR /essim-building-model

COPY . .

RUN pip install -r requirements.txt

ENTRYPOINT python3 -m essim_external_model.py
