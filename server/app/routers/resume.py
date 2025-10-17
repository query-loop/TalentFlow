from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import Optional
import io

try:
    from pypdf import PdfReader  # type: ignore
except Exception:
    PdfReader = None  # type: ignore

try:
    import docx  # python-docx
except Exception:
    docx = None  # type: ignore

router = APIRouter()


class ResumeParseRequest(BaseModel):
    name: str
    mime: Optional[str] = None
    size: Optional[int] = None
    text: Optional[str] = None  # Optional OCR/plaintext sent by client


class ResumeParseResponse(BaseModel):
    id: str
    name: str
    mime: Optional[str] = None
    size: Optional[int] = None
    text: Optional[str] = None


@router.post("/parse", response_model=ResumeParseResponse)
async def parse_resume(body: ResumeParseRequest) -> ResumeParseResponse:
    # For now we just echo an ID and the provided metadata/text; storage optional
    import time
    rid = f"res_{int(time.time()*1000)}"
    return ResumeParseResponse(id=rid, name=body.name, mime=body.mime, size=body.size, text=body.text)


@router.post("/parse-file", response_model=ResumeParseResponse)
async def parse_resume_file(file: UploadFile = File(...)) -> ResumeParseResponse:
    content = await file.read()
    text: Optional[str] = None
    mime = file.content_type or ""
    name = file.filename or "resume"
    # Try PDF
    if (mime == "application/pdf" or name.lower().endswith(".pdf")) and PdfReader is not None:
        try:
            reader = PdfReader(io.BytesIO(content))
            parts = []
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or "")
                except Exception:
                    continue
            text = "\n".join(p for p in parts if p)
        except Exception:
            text = None
    # Try DOCX
    elif (mime.endswith("wordprocessingml.document") or name.lower().endswith(".docx")) and docx is not None:
        try:
            doc = docx.Document(io.BytesIO(content))
            text = "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            text = None
    # Try plain text
    elif mime.startswith("text/") or name.lower().endswith(".txt"):
        try:
            text = content.decode("utf-8", errors="ignore")
        except Exception:
            text = None

    import time
    rid = f"res_{int(time.time()*1000)}"
    return ResumeParseResponse(id=rid, name=name, mime=mime, size=len(content), text=text)
