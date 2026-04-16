from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Feed (legacy single-feed setting, now managed per-podcast in DB)
    rss_feed_url: str = ""
    poll_interval_minutes: int = 60

    # Pipeline
    flowcast_auto_publish: bool = False

    # YouTube
    google_client_id: str = ""
    google_client_secret: str = ""
    youtube_privacy: str = "unlisted"
    youtube_category_id: str = "22"

    # Storage
    data_dir: Path = Path("/app/data")
    max_render_age_days: int = 30

    # App
    secret_key: str = "change-me"
    log_level: str = "INFO"
    app_base_url: str = "http://localhost:8000"
    security_contact: str = "security@your-domain.com"

    # Authentication
    admin_username: str = "admin"
    admin_password: str = "changeme"
    session_max_age: int = 86400 * 7  # 7 days in seconds

    # Derived paths (computed properties)
    @property
    def db_path(self) -> Path:
        return self.data_dir / "db" / "flowcast.db"

    @property
    def db_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path}"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def backgrounds_dir(self) -> Path:
        return self.data_dir / "uploads" / "backgrounds"

    @property
    def fonts_dir(self) -> Path:
        return self.data_dir / "uploads" / "fonts"

    @property
    def downloads_dir(self) -> Path:
        return self.data_dir / "downloads"

    @property
    def renders_dir(self) -> Path:
        return self.data_dir / "renders"

    @property
    def tokens_dir(self) -> Path:
        return self.data_dir / "tokens"

    @property
    def totp_secret_path(self) -> Path:
        return self.data_dir / "tokens" / "totp_secret.txt"

    @property
    def youtube_token_path(self) -> Path:
        return self.data_dir / "tokens" / "youtube_token.json"

    # System font path (installed by Dockerfile via fonts-liberation)
    default_font_path: str = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

    def validate_secrets(self) -> None:
        """Raise RuntimeError if insecure default credentials are detected."""
        errors = []
        if self.secret_key in ("change-me", ""):
            errors.append("SECRET_KEY no puede ser 'change-me' — generá una clave aleatoria")
        if self.admin_password in ("changeme", ""):
            errors.append("ADMIN_PASSWORD no puede ser 'changeme' — cambiala en .env")
        if errors:
            raise RuntimeError(
                "Configuración insegura — la app no puede arrancar:\n"
                + "\n".join(f"  • {e}" for e in errors)
            )

    def ensure_dirs(self) -> None:
        for d in [
            self.data_dir / "db",
            self.backgrounds_dir,
            self.fonts_dir,
            self.downloads_dir,
            self.renders_dir,
            self.tokens_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
