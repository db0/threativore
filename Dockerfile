FROM python:3.11

COPY . .

RUN python -m pip install -r requirements.txt

ENV LEMMY_DOMAIN=
ENV LEMMY_USERNAME=
ENV LEMMY_PASSWORD=
ENV USE_SQLITE=0
ENV THREATIVORE_ADMIN_URL=
ENV POSTGRES_URL=
ENV POSTGRES_PASS=

CMD python run.py