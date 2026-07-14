from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence

from .theme import BORDER, CARD, MUTED


class Sparkline(tk.Canvas):
    """Kleine, ruhige Verlaufsgrafik ohne externe Abhängigkeiten."""

    def __init__(
        self,
        master: tk.Misc,
        values: Sequence[float] | None = None,
        *,
        line_color: str,
        height: int = 38,
        background: str = CARD,
    ) -> None:
        super().__init__(
            master,
            height=height,
            bg=background,
            highlightthickness=0,
            bd=0,
        )
        self._values = list(values or [])
        self._line_color = line_color
        self.bind("<Configure>", lambda _event: self._draw())
        self.after_idle(self._draw)

    def set_values(self, values: Sequence[float]) -> None:
        self._values = list(values)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        width = max(2, self.winfo_width())
        height = max(2, self.winfo_height())
        pad_x, pad_y = 3, 5
        self.create_line(pad_x, height - pad_y, width - pad_x, height - pad_y, fill=BORDER)

        if len(self._values) < 2:
            self.create_text(
                width / 2,
                height / 2,
                text="Verlauf wird aufgebaut",
                fill=MUTED,
                font=("Sans", 7),
            )
            return

        low = min(self._values)
        high = max(self._values)
        span = max(high - low, 1.0)
        usable_width = max(1, width - 2 * pad_x)
        usable_height = max(1, height - 2 * pad_y)
        points: list[float] = []
        last_index = len(self._values) - 1
        for index, value in enumerate(self._values):
            x = pad_x + usable_width * index / last_index
            y = pad_y + usable_height * (high - value) / span
            points.extend((x, y))

        self.create_line(*points, fill=self._line_color, width=2, smooth=True, splinesteps=12)
        self.create_oval(
            points[-2] - 2.5,
            points[-1] - 2.5,
            points[-2] + 2.5,
            points[-1] + 2.5,
            fill=self._line_color,
            outline=self._line_color,
        )
