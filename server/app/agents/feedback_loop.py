"""Feedback Loop Agent

Stores feedback events and trains a lightweight online ranker from labeled
outcomes. Storage uses MinIO when a client is provided; in-memory storage is
used when no client is passed (useful for tests and dev).
"""
from __future__ import annotations

from typing import Optional, Dict, Any, List
import time
import json
import math
import uuid
import logging

from app.agents.scorer import score_profile
from app import storage

logger = logging.getLogger(__name__)


class FeedbackStore:
    def __init__(self, client=None, bucket: Optional[str] = None, prefix: str = "feedback/"):
        self.client = client
        self.bucket = bucket or storage.MINIO_BUCKET
        self.prefix = prefix
        self._mem: List[Dict[str, Any]] = []

    def record(self, entry: Dict[str, Any]) -> str:
        """Record feedback entry. If a MinIO client is provided, write JSON object
        to `prefix/{uuid}.json`. Otherwise store in-memory list and return an id.
        """
        entry = dict(entry)
        entry["ts"] = time.time()
        key = f"{self.prefix}{uuid.uuid4().hex}.json"
        if self.client:
            try:
                storage.upload_bytes(json.dumps(entry).encode("utf-8"), key, client=self.client, bucket=self.bucket)
                return key
            except Exception:
                logger.exception("Failed to write feedback to MinIO; falling back to memory")

        # memory fallback
        self._mem.append(entry)
        return key

    def list_memory(self) -> List[Dict[str, Any]]:
        return list(self._mem)


class Ranker:
    """Simple online logistic regressor over scorer features."""

    def __init__(self, feature_names: Optional[List[str]] = None):
        if feature_names is None:
            feature_names = ["embedding", "keyword_coverage", "ats"]
        self.feature_names = feature_names
        self.weights: Dict[str, float] = {f: 0.0 for f in self.feature_names}
        self.bias: float = 0.0

    def predict_raw(self, features: Dict[str, float]) -> float:
        s = self.bias
        for f in self.feature_names:
            s += self.weights.get(f, 0.0) * float(features.get(f, 0.0))
        return s

    def predict(self, features: Dict[str, float]) -> float:
        raw = self.predict_raw(features)
        # sigmoid
        return 1.0 / (1.0 + math.exp(-raw))

    def update(self, features: Dict[str, float], label: int, lr: float = 0.1) -> None:
        # label is 1 or 0
        pred = self.predict(features)
        error = float(label) - pred
        # gradient ascent on log-likelihood (or gradient descent on cross-entropy)
        for f in self.feature_names:
            g = error * float(features.get(f, 0.0))
            self.weights[f] += lr * g
        self.bias += lr * error


class FeedbackLoop:
    def __init__(self, store: Optional[FeedbackStore] = None, ranker: Optional[Ranker] = None, embed_model: Optional[str] = None):
        self.store = store or FeedbackStore(client=None)
        self.ranker = ranker or Ranker()
        self.embed_model = embed_model

    def record_feedback(self, profile: Dict[str, Any], job: Dict[str, Any], label: int, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Record feedback and perform an online training step on the ranker.

        label: 1 (positive) or 0 (negative).
        Returns the storage key or internal id.
        """
        # compute scorer features
        sc = score_profile(profile, job, embed_model=self.embed_model)
        entry = {
            "profile": profile,
            "job": job,
            "features": sc,
            "label": int(label),
            "metadata": metadata or {},
        }
        key = self.store.record(entry)
        # online update
        features = {k: sc.get(k, 0.0) for k in ["embedding", "keyword_coverage", "ats"]}
        self.ranker.update(features, label)
        return key

    def score_with_ranker(self, profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, float]:
        sc = score_profile(profile, job, embed_model=self.embed_model)
        features = {k: sc.get(k, 0.0) for k in ["embedding", "keyword_coverage", "ats"]}
        raw = self.ranker.predict_raw(features)
        prob = self.ranker.predict(features)
        return {"features": features, "raw": raw, "probability": prob}
