from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _run_dir() -> Path:
    """Return the workspace .run directory, creating it if needed."""
    try:
        # __file__: .../server/app/utils/runlog.py
        # parents[3]: workspace root
        root = Path(__file__).resolve().parents[3]
    except Exception:
        root = Path.cwd()
    d = root / ".run"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_qa(
    *,
    question: str,
    context: Optional[str],
    provider: Optional[str],
    answer: str,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """Append a single JSON line with Q&A info to .run/qa.log.

    To avoid oversized logs, store only small previews of large fields.
    """
    ctx = (context or "")
    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "question": str(question)[:2000],
        "question_len": len(question or ""),
        "context_preview": ctx[:1000],
        "context_len": len(ctx),
        "provider": provider or "",
        "answer_preview": str(answer)[:2000],
        "answer_len": len(answer or ""),
    }
    if meta:
        # Shallow merge for small metadata like durations, model names, etc.
        for k, v in meta.items():
            # Keep values JSON-serializable
            try:
                json.dumps(v)
                record[k] = v
            except Exception:
                record[k] = str(v)

    run_dir = _run_dir()
    path = run_dir / "qa.log"
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # Best-effort logging; never raise
        pass
