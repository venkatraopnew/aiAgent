from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_base_url: str = "http://localhost:8000"

    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"

    elevenlabs_api_key: str
    elevenlabs_voice_id: str

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str


settings = Settings()

