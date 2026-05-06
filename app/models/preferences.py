from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppPreferences(Base):
    __tablename__ = "app_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    ui_font: Mapped[str] = mapped_column(String(64), nullable=False, default="cantarell")
    ui_font_size: Mapped[str] = mapped_column(String(8), nullable=False, default="L")
