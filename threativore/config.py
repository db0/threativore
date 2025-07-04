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
    admin_contact_url: str = env.str("ADMIN_CONTACT_URL", None)
    # DB Stuff
    use_sqlite: bool = env.bool("USE_SQLITE", True) 
    sqlite_filename: str = env.str("SQLITE_FILENAME", "threativore.db")
    postgres_user: str = env("POSTGRES_USER", "postgres")
    postgres_pass = env("POSTGRES_PASS", None)
    postgres_url = env("POSTGRES_URL", None)
    dry_run = env.bool("DRY_RUN", False)
    admin_api_keys: dict = env.dict("ADMIN_API_KEYS", subcast_values=str)
    # Payment and tag stuff
    kofi_webhook_verification_token: str = env("KOFI_WEBHOOK_VERIFICATION_TOKEN", None)
    kofi_tiers: list[str] = env.list("KOFI_TIERS", subcast=str)
    liberapay_cookie: str = env("LIBERAPAY_COOKIE", None)
    liberapay_username: str = env("LIBERAPAY_USERNAME", None)
    liberapay_tiers: dict = env.dict("LIBERAPAY_TIERS", None)
    predefined_custom_emoji_flairs: dict = env.dict("PREDEFINED_CUSTOM_EMOJI_FLAIRS", None, subcast_values=str)
    flag_descriptions: dict = env.dict("FLAG_DESCRIPTIONS", None, subcast_values=str)
    payment_tier_descriptions: dict = env.dict("PAYMENT_TIER_DESCRIPTIONS", None, subcast_values=str)
    predefined_tag_descriptions: dict = env.dict("PREDEFINED_TAG_DESCRIPTIONS", None, subcast_values=str)
    donation_expiration_days: int = env.int("DONATION_EXPIRATION_DAYS", 60)
    trusted_tiers: list[str] = env.list("TRUSTED_TIERS",[], subcast=str)
    trusted_tags: list[str] = env.list("TRUSTED_TAGS",[], subcast=str)
    known_tiers: list[str] = env.list("KNOWN_TIERS",[], subcast=str)
    known_tags: list[str] = env.list("KNOWN_TAGS",[], subcast=str)
    voting_tiers: list[str] = env.list("VOTING_TIERS",[], subcast=str)
    voting_tags: list[str] = env.list("VOTING_TAGS",[], subcast=str)
    vouches_per_user: int = env.int("VOUCHES_PER_USER", 2)
    outsider_emoji: str = env.str("OUTSIDER_EMOJI", None)
    admin_emoji: str = env.str("ADMIN_EMOJI", None)
    voting_flair_priority: dict = env.dict("VOTING_FLAIR_PRIORITY", None, subcast_values=int)
    non_voting_flair_priority: dict = env.dict("NON_VOTING_FLAIR_PRIORITY", None, subcast_values=int)
    application_deny_list: list[str] = env.list("APPLICATION_DENY_LIST", [], subcast=str)
    application_deny_reason: str = env.str("APPLICATION_DENY_REASON", None)
    application_deny_min_length: int = env.int("APPLICATION_DENY_MIN_LENGTH", None)
    # For use with the connection to the lemmy DB directly
    lemmy_db_host: str = env.str("LEMMY_DB_HOST", None)
    lemmy_db_username: str = env.str("LEMMY_DB_USERNAME", None)
    lemmy_db_password: str = env.str("LEMMY_DB_PASSWORD", None)
    lemmy_db_database: str = env.str("LEMMY_DB_DATABASE", None)
    # Governance
    governance_community: str = env.str("GOVERNANCE_COMMUNITY", None)
    # Fediseer
    enable_fediseer_blocklist_refresh: str = env.str("ENABLE_FEDISEER_BLOCKLIST_REFRESH", False)
    fediseer_api_key: str = env.str("FEDISEER_API_KEY", None)
    fediseer_sus_users_per_activity = env.int("FEDISEER_SUS_USERS_PER_ACTIVITY", 20)
    fediseer_sus_activity_per_user = env.int("FEDISEER_SUS_ACTIVITY_PER_USER", 500)
    fediseer_adhoc_blocks = env.list("FEDISEER_ADHOC_BLOCKS",[], subcast=str)
    fediseer_safelist = env.list("FEDISEER_SAFELIST",[], subcast=str)
    fediseer_trusted_instances = env.list("FEDISEER_TRUSTED_INSTANCES",[], subcast=str)
    fediseer_filtered_instances = env.list("FEDISEER_FILTERED_INSTANCES",["lemmy.dbzer0.com,lemmy.world,lemmings.world"], subcast=str)
    fediseer_reason_filters = env.list("FEDISEER_REASON_FILTERS",["__all_pedos__,__all_bigots__"], subcast=str)
    fediseer_min_censures = env.int("FEDISEER_MIN_CENSURES", 1)
    fediseer_changes_warning_threshold = env.int("FEDISEER_CHANGES_WARNING_THRESHOLD", 10)
