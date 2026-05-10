from __future__ import annotations

import threading
from dataclasses import dataclass, field

from core.session import ChatSession


@dataclass
class BrowserSessionState:
    session: ChatSession
    temperature: float
    selected_model: str
    enable_system_prompt: bool = True
    title: str = ""
    saved_basename: str = ""
    epoch: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)
