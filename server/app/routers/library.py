from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
from app.models import SessionLocal, ResumeLibrary
import json as pyjson

router = APIRouter()


class LibraryItem(BaseModel):
    id: int
    name: str
    kind: str
    source: str
    text: str
    meta: Optional[Any] = None
    createdAt: str
    updatedAt: str


class AddUploadedRequest(BaseModel):
    name: str
    text: str
    meta: Optional[Any] = None


class AddDraftRequest(BaseModel):
    name: str
    text: str
    meta: Optional[Any] = None


@router.get("", response_model=List[LibraryItem])
async def list_library() -> List[LibraryItem]:
    items: List[LibraryItem] = []
    with SessionLocal() as db:
        rows = db.query(ResumeLibrary).order_by(ResumeLibrary.updated_at.desc()).limit(200).all()
        for r in rows:
            try:
                items.append(LibraryItem(
                    id=r.id,
                    name=r.name,
                    kind=r.kind,
                    source=r.source,
                    text=r.text,
                    meta=pyjson.loads(r.meta_json) if r.meta_json else None,
                    createdAt=r.created_at.isoformat()+"Z",
                    updatedAt=r.updated_at.isoformat()+"Z",
                ))
            except Exception:
                continue
    return items


@router.post("/uploaded", response_model=LibraryItem)
async def add_uploaded(body: AddUploadedRequest) -> LibraryItem:
    with SessionLocal() as db:
        row = ResumeLibrary(name=body.name, kind="uploaded", source="upload", text=body.text, meta_json=pyjson.dumps(body.meta) if body.meta else None)
        db.add(row)
        db.commit()
        db.refresh(row)
        return LibraryItem(
            id=row.id,
            name=row.name,
            kind=row.kind,
            source=row.source,
            text=row.text,
            meta=pyjson.loads(row.meta_json) if row.meta_json else None,
            createdAt=row.created_at.isoformat()+"Z",
            updatedAt=row.updated_at.isoformat()+"Z",
        )


@router.post("/draft", response_model=LibraryItem)
async def add_draft(body: AddDraftRequest) -> LibraryItem:
    with SessionLocal() as db:
        row = ResumeLibrary(name=body.name, kind="draft", source="generate", text=body.text, meta_json=pyjson.dumps(body.meta) if body.meta else None)
        db.add(row)
        db.commit()
        db.refresh(row)
        return LibraryItem(
            id=row.id,
            name=row.name,
            kind=row.kind,
            source=row.source,
            text=row.text,
            meta=pyjson.loads(row.meta_json) if row.meta_json else None,
            createdAt=row.created_at.isoformat()+"Z",
            updatedAt=row.updated_at.isoformat()+"Z",
        )


@router.get("/{item_id}", response_model=LibraryItem)
async def get_item(item_id: int) -> LibraryItem:
    with SessionLocal() as db:
        row = db.query(ResumeLibrary).filter(ResumeLibrary.id == item_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        return LibraryItem(
            id=row.id,
            name=row.name,
            kind=row.kind,
            source=row.source,
            text=row.text,
            meta=pyjson.loads(row.meta_json) if row.meta_json else None,
            createdAt=row.created_at.isoformat()+"Z",
            updatedAt=row.updated_at.isoformat()+"Z",
        )
