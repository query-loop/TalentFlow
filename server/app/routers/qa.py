from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.ai.agent import agent_answer
from app.utils.runlog import log_qa

router = APIRouter()


class QARequest(BaseModel):
    question: str
    context: Optional[str] = None


class QAResponse(BaseModel):
    answer: str
    provider: str


@router.post("", response_model=QAResponse)
async def ask(body: QARequest) -> QAResponse:
    data = agent_answer(body.question, body.context)
    answer = data.get("answer", "")
    provider = data.get("provider", "fallback")
    # Log to .run/qa.log for debugging prompt-based answering
    try:
        log_qa(question=body.question, context=body.context, provider=provider, answer=answer)
    except Exception:
        pass
    return QAResponse(answer=answer, provider=provider)
