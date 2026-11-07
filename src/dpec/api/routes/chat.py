"""The race engineer's address (step D2): POST /api/chat with {"question": "..."}.

The one address that isn't a plain read: it asks a model, which costs money (Claude) or time
(Ollama). So it only works on the local app; the public copy (mode: public) says no.
GET /api/chat/recorded is what the public copy shows instead (Lesson 20b): the answers the
engineer gave on its exam (dpec eval-ai), read from the newest saved run in reports/ai/.
"""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from dpec.assistant.chat import ProviderError
from dpec.assistant.engineer import ask
from dpec.assistant.evals import QUESTIONS, REPORTS, load_questions

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


def newest_run(folder: Path = REPORTS) -> Path | None:
    """The newest exam run (eval-<provider>-<model>-<date>.csv); on the same day, the biggest."""
    runs = [(p.stem[-10:], len(p.read_text().splitlines()), p) for p in folder.glob("eval-*.csv")]
    return max(runs)[2] if runs else None


@router.get("/chat/recorded")
def recorded() -> dict:
    """The engineer's recorded exam answers, with each question's text. Works in both modes.
    (No inputs on purpose: a visitor can't point it at another folder.)"""
    return recorded_answers(REPORTS, QUESTIONS)


def recorded_answers(folder: Path, questions: Path) -> dict:
    run = newest_run(folder)
    if run is None or not questions.exists():
        return {"recorded_on": None, "provider": None, "model": None, "passed": 0, "answers": []}
    text = {q["id"]: q["question"] for q in load_questions(questions)}
    r = pd.read_csv(run, keep_default_na=False)
    answers = [
        {
            "id": row.id,
            "kind": row.kind,
            "question": text.get(row.id, ""),
            "answer": row.answer,
            "passed": str(row.passed) == "True",
            "misses": row.misses,
            "tools": str(row.tools).split(),
            "seconds": float(row.seconds),
            "tokens": int(row.tokens_in) + int(row.tokens_out),
            "provider": row.provider,
        }
        for row in r.itertuples()
    ]
    return {
        "recorded_on": run.stem[-10:],
        "provider": r["provider"].iloc[0] if len(r) else None,
        "model": r["model"].iloc[0] if len(r) else None,
        "passed": sum(a["passed"] for a in answers),
        "answers": answers,
    }
