"""Media library endpoints — Google Drive + Instagram integration."""
import logging
import re
import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.media_item import MediaItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media", tags=["media"])


@router.get("/items")
async def list_media(
    category: str | None = None,
    search: str | None = None,
    source_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all active media items, optionally filtered."""
    query = select(MediaItem).where(MediaItem.is_active == True).order_by(MediaItem.created_at.desc())
    if category:
        query = query.where(MediaItem.category == category)
    if source_type:
        query = query.where(MediaItem.source_type == source_type)
    if search:
        query = query.where(MediaItem.name.ilike(f"%{search}%"))
    result = await db.execute(query)
    items = result.scalars().all()
    return [
        {
            "id": i.id,
            "name": i.name,
            "description": i.description,
            "drive_file_id": i.drive_file_id,
            "drive_url": i.drive_url,
            "thumbnail_url": i.thumbnail_url,
            "mime_type": i.mime_type,
            "category": i.category,
            "source_type": i.source_type,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }
        for i in items
    ]


@router.post("/items")
async def create_media(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add a media item (Google Drive, Instagram, or generic link)."""
    data = await request.json()
    url = data.get("drive_url", "").strip()
    name = data.get("name", "").strip()

    if not url or not name:
        raise HTTPException(400, "name e drive_url são obrigatórios")

    # Auto-detect source type
    source_type = _detect_source_type(url)
    thumbnail_url = None
    drive_file_id = ""

    if source_type == "instagram":
        ig_id = _extract_instagram_id(url)
        drive_file_id = ig_id or url
        # Instagram embeds don't have simple thumbnail API, use placeholder
        thumbnail_url = None
    elif source_type == "drive":
        drive_file_id = _extract_drive_id(url) or url
        if drive_file_id and drive_file_id != url:
            thumbnail_url = f"https://drive.google.com/thumbnail?id={drive_file_id}&sz=w400"
    else:
        drive_file_id = url

    item = MediaItem(
        name=name,
        description=data.get("description"),
        drive_file_id=drive_file_id,
        drive_url=url,
        thumbnail_url=thumbnail_url,
        mime_type=data.get("mime_type"),
        category=data.get("category", "outro"),
        source_type=source_type,
        created_by=user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {
        "id": item.id,
        "name": item.name,
        "drive_url": item.drive_url,
        "thumbnail_url": item.thumbnail_url,
        "category": item.category,
        "source_type": item.source_type,
    }


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    name: str = Form(""),
    category: str = Form("outro"),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a file to Google Drive and create a media item."""
    from app.core.config import settings

    if not settings.GOOGLE_SERVICE_ACCOUNT_JSON:
        raise HTTPException(400, "Google Drive não configurado. Configure GOOGLE_SERVICE_ACCOUNT_JSON.")

    file_name = name.strip() or file.filename or "arquivo"

    try:
        import json
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        import io

        # Parse service account credentials
        creds_data = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = service_account.Credentials.from_service_account_info(
            creds_data, scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        service = build("drive", "v3", credentials=creds)

        # Read file content
        content = await file.read()
        media_body = MediaIoBaseUpload(io.BytesIO(content), mimetype=file.content_type or "application/octet-stream")

        # Upload to Google Drive
        file_metadata = {"name": file.filename or file_name}
        if settings.GOOGLE_DRIVE_FOLDER_ID:
            file_metadata["parents"] = [settings.GOOGLE_DRIVE_FOLDER_ID]

        result = service.files().create(
            body=file_metadata, media_body=media_body, fields="id,webViewLink"
        ).execute()

        drive_file_id = result["id"]
        drive_url = result.get("webViewLink", f"https://drive.google.com/file/d/{drive_file_id}/view")

        # Make file publicly accessible (view only)
        try:
            service.permissions().create(
                fileId=drive_file_id,
                body={"type": "anyone", "role": "reader"},
            ).execute()
        except Exception as e:
            logger.warning(f"Could not set file permissions: {e}")

        thumbnail_url = f"https://drive.google.com/thumbnail?id={drive_file_id}&sz=w400"

        item = MediaItem(
            name=file_name,
            description=description or None,
            drive_file_id=drive_file_id,
            drive_url=drive_url,
            thumbnail_url=thumbnail_url,
            mime_type=file.content_type,
            category=category,
            source_type="drive",
            created_by=user.id,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)

        return {
            "id": item.id,
            "name": item.name,
            "drive_url": item.drive_url,
            "drive_file_id": drive_file_id,
            "thumbnail_url": thumbnail_url,
            "category": item.category,
            "source_type": "drive",
        }

    except ImportError:
        raise HTTPException(500, "Google API libraries não instaladas (google-api-python-client, google-auth)")
    except Exception as e:
        logger.error(f"Upload to Google Drive failed: {e}")
        raise HTTPException(500, f"Erro no upload: {str(e)}")


@router.delete("/items/{item_id}")
async def delete_media(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft-delete a media item."""
    result = await db.execute(select(MediaItem).where(MediaItem.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(404, "Item não encontrado")
    item.is_active = False
    await db.commit()
    return {"ok": True}


@router.get("/suggest/{ticket_id}")
async def suggest_media(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI suggests relevant media items based on ticket context."""
    from app.models.ticket import Ticket
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")

    # Get all active media
    media_result = await db.execute(select(MediaItem).where(MediaItem.is_active == True))
    all_media = media_result.scalars().all()

    if not all_media:
        return {"suggestions": [], "reason": "Nenhuma mídia na biblioteca"}

    # Use AI to suggest relevant media
    try:
        from app.core.config import settings
        if not settings.ANTHROPIC_API_KEY:
            return {"suggestions": [], "reason": "API de IA não configurada"}

        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        media_list = "\n".join([
            f"- ID: {m.id} | Nome: {m.name} | Categoria: {m.category} | Tipo: {m.source_type} | Descrição: {m.description or 'N/A'}"
            for m in all_media
        ])

        prompt = f"""Analise o ticket abaixo e sugira quais mídias da biblioteca seriam úteis para enviar ao cliente.

TICKET:
- Assunto: {ticket.subject}
- Categoria: {ticket.category or 'N/A'}
- Prioridade: {ticket.priority}
- Tags: {', '.join(ticket.tags) if ticket.tags else 'N/A'}

MÍDIAS DISPONÍVEIS:
{media_list}

Responda APENAS com os IDs das mídias relevantes separados por vírgula, ou "nenhuma" se nenhuma for relevante.
Formato: id1,id2,id3"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        answer = response.content[0].text.strip().lower()
        if answer == "nenhuma":
            return {"suggestions": [], "reason": "Nenhuma mídia relevante para este ticket"}

        suggested_ids = [sid.strip() for sid in answer.split(",") if sid.strip()]
        suggestions = [
            {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "drive_url": m.drive_url,
                "thumbnail_url": m.thumbnail_url,
                "category": m.category,
                "source_type": m.source_type,
            }
            for m in all_media if m.id in suggested_ids
        ]
        return {"suggestions": suggestions, "reason": "Sugestões baseadas no contexto do ticket"}

    except Exception as e:
        logger.warning(f"AI media suggestion failed: {e}")
        # Fallback: suggest by matching category
        category_map = {
            "garantia": "video", "troca": "video", "defeito_garantia": "video",
            "suporte_tecnico": "manual", "carregador": "video",
        }
        suggested_cat = category_map.get(ticket.category)
        if suggested_cat:
            fallback = [
                {
                    "id": m.id, "name": m.name, "description": m.description,
                    "drive_url": m.drive_url, "thumbnail_url": m.thumbnail_url,
                    "category": m.category, "source_type": m.source_type,
                }
                for m in all_media if m.category == suggested_cat
            ]
            return {"suggestions": fallback[:5], "reason": f"Sugestões por categoria ({suggested_cat})"}
        return {"suggestions": [], "reason": "Sem sugestões disponíveis"}


# ── Helpers ──

def _detect_source_type(url: str) -> str:
    """Auto-detect if URL is Instagram, Google Drive, or generic link."""
    url_lower = url.lower()
    if "instagram.com" in url_lower or "instagr.am" in url_lower:
        return "instagram"
    if "drive.google.com" in url_lower or "docs.google.com" in url_lower:
        return "drive"
    return "link"


def _extract_instagram_id(url: str) -> str | None:
    """Extract Instagram post/reel ID from URL."""
    patterns = [
        r'instagram\.com/(?:p|reel|reels)/([a-zA-Z0-9_-]+)',
        r'instagr\.am/p/([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _extract_drive_id(url: str) -> str | None:
    """Extract Google Drive file ID from various URL formats."""
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'/open\?id=([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/d/([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
