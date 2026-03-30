from __future__ import annotations

import io
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.template import Template
from app.schemas.template import TemplateCreate, TemplateOut, TemplateUpdate

router = APIRouter(prefix="/api/templates", tags=["templates"])

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.get("", response_model=list[TemplateOut])
async def list_templates(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Template).order_by(Template.is_default.desc(), Template.id))
    return result.scalars().all()


@router.post("", response_model=TemplateOut, status_code=201)
async def create_template(body: TemplateCreate, session: AsyncSession = Depends(get_session)):
    tmpl = Template(**body.model_dump())
    session.add(tmpl)
    await session.commit()
    await session.refresh(tmpl)
    return tmpl


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: int, session: AsyncSession = Depends(get_session)):
    tmpl = await session.get(Template, template_id)
    if tmpl is None:
        raise HTTPException(404, "Template not found")
    return tmpl


@router.put("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: int, body: TemplateUpdate, session: AsyncSession = Depends(get_session)
):
    tmpl = await session.get(Template, template_id)
    if tmpl is None:
        raise HTTPException(404, "Template not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(tmpl, k, v)
    await session.commit()
    await session.refresh(tmpl)
    return tmpl


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: int, session: AsyncSession = Depends(get_session)):
    tmpl = await session.get(Template, template_id)
    if tmpl is None:
        raise HTTPException(404, "Template not found")
    if tmpl.is_default:
        raise HTTPException(400, "Cannot delete the default template. Set another as default first.")
    await session.delete(tmpl)
    await session.commit()


@router.post("/{template_id}/default", response_model=TemplateOut)
async def set_default_template(template_id: int, session: AsyncSession = Depends(get_session)):
    tmpl = await session.get(Template, template_id)
    if tmpl is None:
        raise HTTPException(404, "Template not found")

    # Clear existing default
    result = await session.execute(select(Template).where(Template.is_default == True))  # noqa: E712
    for t in result.scalars():
        t.is_default = False

    tmpl.is_default = True
    await session.commit()
    await session.refresh(tmpl)
    return tmpl


@router.post("/{template_id}/background", response_model=TemplateOut)
async def upload_background(
    template_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    tmpl = await session.get(Template, template_id)
    if tmpl is None:
        raise HTTPException(404, "Template not found")

    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"Unsupported image type: {file.content_type}. Use JPEG, PNG, or WebP.")

    content = await file.read()
    # Validate it's actually an image
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(400, "Invalid image file")

    bg_dir = settings.backgrounds_dir
    bg_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "bg.png").suffix or ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    dest = bg_dir / filename
    dest.write_bytes(content)

    # Delete old background if it exists
    if tmpl.background_path and Path(tmpl.background_path).exists():
        Path(tmpl.background_path).unlink()

    tmpl.background_path = str(dest)
    await session.commit()
    await session.refresh(tmpl)
    return tmpl


@router.get("/{template_id}/background")
async def get_background(template_id: int, session: AsyncSession = Depends(get_session)):
    tmpl = await session.get(Template, template_id)
    if tmpl is None:
        raise HTTPException(404, "Template not found")

    if tmpl.background_path and Path(tmpl.background_path).exists():
        return FileResponse(tmpl.background_path)

    # Return default background
    default_bg = Path(__file__).parent.parent / "static" / "img" / "default_bg.png"
    if default_bg.exists():
        return FileResponse(str(default_bg))

    raise HTTPException(404, "No background image configured")


@router.post("/{template_id}/watermark", response_model=TemplateOut)
async def upload_watermark(
    template_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    tmpl = await session.get(Template, template_id)
    if tmpl is None:
        raise HTTPException(404, "Template not found")

    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Unsupported image type.")

    content = await file.read()
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(400, "Invalid image file")

    bg_dir = settings.backgrounds_dir
    ext = Path(file.filename or "logo.png").suffix or ".png"
    filename = f"wm_{uuid.uuid4().hex}{ext}"
    dest = bg_dir / filename
    dest.write_bytes(content)

    if tmpl.watermark_path and Path(tmpl.watermark_path).exists():
        Path(tmpl.watermark_path).unlink()

    tmpl.watermark_path = str(dest)
    await session.commit()
    await session.refresh(tmpl)
    return tmpl
