from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str
   
    AUTO_TAP: bool = True

    AUTO_CONNECT_WALLETS: bool = False

    SCORE: list[int] = [5, 30]

    SQUAD_NAME: str = 'yummy_squad'

    REF_ID: str = 'CGYJGk91pub'

    AUTO_TASKS: bool = True

    AUTO_CLAIM_REF_REWARD: bool = True

    AUTO_TOKENFLIP: bool = False

    AUTO_EMPIRE: bool = True

    EMPIRE_LEVEL: int = 1

    AUTO_RESOLVE_EMPIRE: bool = False

    AUTO_RENEW_LICENSE: bool = False

    USE_RANDOM_DELAY_IN_RUN: bool = True
    RANDOM_DELAY_IN_RUN: list[int] = [5, 30]

    NIGHT_MODE: bool = False

    RECONNECT_WALLETS: bool = False

    USE_PROXY_FROM_FILE: bool = False

    WEBSOCKETS_WITHOUT_PROXY: bool = False

    TWO_CAPTCHA_API_TOKEN: str

    FREE_SPINS_NOTIFICATIONS: bool = False

    NOTIFICATIONS_BOT_TOKEN: str = ''

    ADMIN_TG_USER_ID: int = 0

    DEBUG: bool = False


settings = Settings()