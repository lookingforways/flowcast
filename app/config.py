from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Feed
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
    def youtube_token_path(self) -> Path:
        return self.data_dir / "tokens" / "youtube_token.json"

    # System font path (installed by Dockerfile via fonts-liberation)
    default_font_path: str = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

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
