# Threativore docker setup

You can easily run threativore alongside your existing docker containers for Lemmy.  If you used the `docker-compose` method of installing Lemmy this is even easier.

### Docker Compose

_Note: Remember to modify the yaml as needed, for example granting access to the Lemmy networks_

#### Using Volumes (and sqlite)

Modify your existing `docker-compose.yml` and add threativore as another container.  An example may look like
```yaml
  threativore:
    image: ghcr.io/db0/threativore:latest
    hostname: "threativore"
    user: 991:991
    # See .env_template for description of each variable
    environment:
      - LEMMY_DOMAIN=<<yourlemmydomain.foo >>
      - LEMMY_USERNAME=<<Your Bot's Username (created within Lemmy)>>
      - LEMMY_PASSWORD=<<Your Bot's Password (created within Lemmy)>>
      - USE_SQLITE=1
      - THREATIVORE_ADMIN_URL=<<Full URL to your own admin profile, such as lemmy.foo/u/yourusername>>
    restart: unless-stopped
    # Ensure ./path/to/threativore exists in your docker host
    volumes:
      - ./path/to/threativore:/app/instance:Z
    ports:
      - 8000:8080
```

#### Using postgres (separate container)
```yaml
  threativore:
    image: ghcr.io/db0/threativore:latest
    hostname: "threativore"
    user: 991:991
    # See .env_template for description of each variable
    environment:
      - LEMMY_DOMAIN=<<yourlemmydomain.foo >>
      - LEMMY_USERNAME=<<Your Bot's Username (created within Lemmy)>>
      - LEMMY_PASSWORD=<<Your Bot's Password (created within Lemmy)>>
      - USE_SQLITE=0
      - THREATIVORE_ADMIN_URL=<<Full URL to your own admin profile, such as lemmy.foo/u/yourusername>>
      - POSTGRES_USER=<<postgres username>>
      - POSTGRES_URL=<<postgres url>>
      - POSTGRES_PASS=<<postgres password>>
```
