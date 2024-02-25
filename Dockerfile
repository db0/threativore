FROM docker.io/python:3.11-slim-bookworm
LABEL org.opencontainers.image.source https://github.com/db0/threativore

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN <<EOF
    set -eu
    apt-get -qq update
    apt-get -qq upgrade
    apt-get -qq install --no-install-recommends apt-utils dumb-init dnsutils > /dev/null
    apt-get -qq autoremove
    apt-get clean
    ln -s /usr/lib/libssl.so /usr/lib/libssl.so.1.1
    rm -rf /var/lib/apt/lists/*
    groupadd -r -g 991 threativore
    useradd -r -u 991 -g 991 -s /sbin/false -M threativore
    chown -R 991:991 /app
EOF

COPY --chown=991:991 . .
ENV PYTHONPATH='/app'
RUN python -m pip install --no-cache-dir -r requirements.txt
USER threativore
ENTRYPOINT [ "/usr/bin/dumb-init", "--" ]
STOPSIGNAL SIGINT
CMD ["python", "run.py"]
