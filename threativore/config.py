from environs import Env

env = Env()
env.read_env()  # read .env file, if it exists

class Config:
    lemmy_domain: str = env.str("LEMMY_DOMAIN")
    lemmy_username: str = env.str("LEMMY_USERNAME")
    lemmy_password: str = env.str("LEMMY_USERNAME")
    threativore_admin_url: str = env.str("THREATIVORE_ADMIN_URL")
    threativore_appeal_urls: list = env.list("THREATIVORE_APPEAL_URLS")
    discord_webhook = env("DISCORDWEBHOOK", None)
    slack_webhook = env("SLACKWEBHOOK", None)
    threativore_verbosity: int = env.int("THREATIVORE_VERBOSITY", 0) 
    threativore_quiet: int = env.int("THREATIVORE_QUIET", 0) 
    # DB Stuff
    use_sqlite: bool = env.bool("USE_SQLITE", True) 
    sqlite_filename: str = env.str("SQLITE_FILENAME", "threativore.db")
    postgres_user: str = env("POSTGRES_USER", "postgres")
    postgres_pass = env("POSTGRES_PASS", None)
    postgres_url = env("POSTGRES_URL", None)
