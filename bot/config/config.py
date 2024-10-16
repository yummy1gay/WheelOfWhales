from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str
   
    AUTO_TAP: bool = True

    SQUAD_NAME: str = ''

    REF_ID: str = ''

    AUTO_TASKS: bool = False

    NIGHT_MODE: bool = False

    USE_PROXY_FROM_FILE: bool = False


settings = Settings()


