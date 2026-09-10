from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "Auditoria API"
    API_PREFIX_V1: str = Field(
        default="/api/v1",
        validation_alias=AliasChoices("API_PREFIX_V1", "API_V1_PREFIX"),
    )
    IS_DEBUG: bool = False
    CORS_ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS", "CORS_ORIGINS"),
    )
    DATABASE_URL: str
    
    # Configuração de registro público.
    # Default FECHADO (B-M25): esquecer a variável não pode abrir o
    # cadastro. Clientes entram por POST /onboarding/principal-user, e
    # abrir o registro público é uma decisão que precisa ser declarada.
    ALLOW_PUBLIC_REGISTRATION: bool = False
    
    # JWT / Auth
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 15
    # Vida do refresh token (POST /auth/refresh) — ver docs/plano_implementacao.md, item A.10
    JWT_REFRESH_EXPIRES_DAYS: int = 7

    # SMTP / Email
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    SMTP_USE_TLS: bool = True

    @field_validator("IS_DEBUG", mode="before")
    @classmethod
    def parse_is_debug(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        normalized = str(value).strip().lower()
        return normalized in ("1", "true", "yes", "on")

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


settings = Settings()