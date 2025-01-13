from environs import Env

env = Env()
env.read_env()  # read .env file, if it exists

class Config:
    lemmy_domain: str = env.str("LEMMY_DOMAIN")
    lemmy_username: str = env.str("LEMMY_USERNAME")
    lemmy_password: str = env.str("LEMMY_PASSWORD")
    threativore_admin_url: str = env.str("THREATIVORE_ADMIN_URL")
    threativore_appeal_usernames: list = env.list("THREATIVORE_APPEAL_USERNAMES")
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
    dry_run = env.bool("DRY_RUN", False)
    admin_api_keys: dict = env.dict("ADMIN_API_KEYS", subcast_values=str)
    kofi_webhook_verification_token: str = env("KOFI_WEBHOOK_VERIFICATION_TOKEN", None)
    # For use with the connection to the lemmy DB directly
    lemmy_db_host: str = env.str("LEMMY_DB_HOST", None)
    lemmy_db_username: str = env.str("LEMMY_DB_USERNAME", None)
    lemmy_db_password: str = env.str("LEMMY_DB_PASSWORD", None)
    lemmy_db_database: str = env.str("LEMMY_DB_DATABASE", None)
    donation_expiration_days: int = env.int("DONATION_EXPIRATION_DAYS", 60)