"""The race engineer's address (step D2): POST /api/chat with {"question": "..."}.

The one address that isn't a plain read: it asks a model, which costs money (Claude) or time
(Ollama). So it only works on the local app; the public copy (mode: public) says no.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from dpec.assistant.chat import ProviderError
from dpec.assistant.engineer import ask

router = APIRouter()


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@router.post("/chat")
def chat(request: Request, body: Question) -> dict:
    """One question to the race engineer: its answer, and every tool it used."""
    s = request.app.state.settings
    if s.mode == "public":
        raise HTTPException(403, "the race engineer only runs on the local app")
    try:
        a = ask(body.question, s)
    except ProviderError as problem:
        raise HTTPException(503, str(problem)) from None
    return {
        "answer": a.text,
        "calls": a.calls,
        "provider": a.provider,
        "model": a.model,
        "seconds": a.seconds,
        "tokens": a.tokens_in + a.tokens_out,
    }
