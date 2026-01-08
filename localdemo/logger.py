# apps/hybridcontrol/logger.py
from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass


@dataclass
class LogRow:
    ts: float
    face_present: int
    looking: int
    yaw: float
    pitch: float

    hand_present: int
    cursor_x: int
    cursor_y: int
    pinch: int
    pinch_d: float

    armed: int
    confidence: float
    allow_move: int
    allow_click: int

    click_fired: int
    note: str


class CSVLogger:
    """
    Simple CSV logger for evaluation.
    Writes one row per frame.
    """
    def __init__(self, path: str):
        self.path = path
        self._fh = None
        self._writer = None
        self._open()

    def _open(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        new_file = not os.path.exists(self.path)
        self._fh = open(self.path, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)

        if new_file:
            self._writer.writerow([
                "ts",
                "face_present", "looking", "yaw", "pitch",
                "hand_present", "cursor_x", "cursor_y", "pinch", "pinch_d",
                "armed", "confidence", "allow_move", "allow_click",
                "click_fired",
                "note",
            ])
            self._fh.flush()

    def log(self, row: LogRow):
        self._writer.writerow([
            f"{row.ts:.6f}",
            row.face_present, row.looking, f"{row.yaw:.5f}", f"{row.pitch:.5f}",
            row.hand_present, row.cursor_x, row.cursor_y, row.pinch, f"{row.pinch_d:.6f}",
            row.armed, f"{row.confidence:.5f}", row.allow_move, row.allow_click,
            row.click_fired,
            row.note,
        ])
        # flush periodically is fine; for now flush each row to avoid data loss on crash
        self._fh.flush()

    def close(self):
        try:
            if self._fh:
                self._fh.flush()
                self._fh.close()
        finally:
            self._fh = None
            self._writer = None
