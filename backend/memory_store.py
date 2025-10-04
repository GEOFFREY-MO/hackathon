"""
Lightweight persistent memory store for chat conversations.
Stores JSONL under instance/memory.jsonl and provides simple retrieval.

If MEM0 is available (optional) and MEM0_ENABLED=1, a best-effort
integration shim will add/search memory via mem0 as well.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional


class FileMemoryStore:
    """Simple JSONL file-backed memory store per user and shop.

    Each line: {"ts": float, "shop_id": int, "user_id": int, "role": str, "content": str, "meta": {}}
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("")

    def add(self, shop_id: int, user_id: int, role: str, content: str, meta: Optional[Dict] = None) -> None:
        record = {
            "ts": time.time(),
            "shop_id": int(shop_id) if shop_id is not None else None,
            "user_id": int(user_id) if user_id is not None else None,
            "role": str(role or ""),
            "content": str(content or ""),
            "meta": meta or {},
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_recent(self, shop_id: int, user_id: int, limit: int = 8) -> List[Dict]:
        lines = []
        try:
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                        if (shop_id is None or obj.get("shop_id") == shop_id) and (
                            user_id is None or obj.get("user_id") == user_id
                        ):
                            lines.append(obj)
                    except Exception:
                        pass
        except FileNotFoundError:
            return []
        return sorted(lines, key=lambda x: x.get("ts", 0.0))[-limit:]

    def search(self, shop_id: int, user_id: int, query: str, limit: int = 5) -> List[Dict]:
        """Naive keyword search by token overlap. Best-effort, fast."""
        q_tokens = set((query or "").lower().split())
        scored: List[Dict] = []
        try:
            with self.path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                        if (shop_id is None or obj.get("shop_id") == shop_id) and (
                            user_id is None or obj.get("user_id") == user_id
                        ):
                            text = (obj.get("content") or "").lower()
                            score = len(q_tokens.intersection(text.split()))
                            if score > 0:
                                obj["_score"] = score
                                scored.append(obj)
                    except Exception:
                        pass
        except FileNotFoundError:
            return []
        scored.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return scored[:limit]


class OptionalMem0:
    """Thin shim around mem0 if present. Safe no-ops when unavailable."""

    def __init__(self):
        self.enabled = False
        self.client = None
        try:
            if os.getenv("MEM0_ENABLED", "0") == "1":
                # Attempt import
                from importlib import import_module

                mod = import_module("mem0")
                # Some distributions expose Memory; keep try/except broad
                Memory = getattr(mod, "Memory", None)
                if Memory is not None:
                    self.client = Memory()
                    self.enabled = True
        except Exception:
            self.enabled = False
            self.client = None

    def add(self, text: str, user_id: Optional[int] = None, metadata: Optional[Dict] = None) -> None:
        if not self.enabled or not self.client:
            return
        try:
            # Best-effort; API surface may vary by version
            self.client.add(text=text, user_id=user_id, metadata=metadata or {})
        except Exception:
            pass

    def search(self, query: str, user_id: Optional[int] = None, k: int = 5) -> List[str]:
        if not self.enabled or not self.client:
            return []
        try:
            results = self.client.search(query=query, user_id=user_id, k=k)
            # Normalize to list of strings if objects returned
            out: List[str] = []
            for r in results or []:
                if isinstance(r, str):
                    out.append(r)
                elif isinstance(r, dict) and "text" in r:
                    out.append(str(r["text"]))
                else:
                    out.append(str(r))
            return out
        except Exception:
            return []


