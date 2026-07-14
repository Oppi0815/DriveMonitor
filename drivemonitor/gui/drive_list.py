from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from drivemonitor.core.models import DriveInfo
from .theme import BLUE, BORDER, CARD, MUTED, SELECTED, TEXT, temp_color


class DriveList(tk.Frame):
    """Robuste Laufwerksauswahl mit klickbarer kompletter Kartenfläche."""

    def __init__(
        self,
        master: tk.Misc,
        on_select: Callable[[str], None],
    ) -> None:
        super().__init__(master, bg=CARD)
        self._on_select = on_select

    def render(self, drives: list[DriveInfo], selected_device: str | None) -> None:
        for widget in self.winfo_children():
            widget.destroy()

        for drive in drives:
            self._add_drive(drive, drive.device == selected_device)

    def _add_drive(self, drive: DriveInfo, selected: bool) -> None:
        bg = SELECTED if selected else CARD
        card = tk.Frame(
            self,
            bg=bg,
            highlightthickness=1,
            highlightbackground=BLUE if selected else BORDER,
            cursor="hand2",
            takefocus=True,
        )
        card.pack(fill="x", pady=2)

        kind = tk.Label(
            card,
            text=drive.kind,
            width=6,
            font=("Sans", 8, "bold"),
            bg=bg,
            fg=BLUE,
            cursor="hand2",
        )
        kind.pack(side="left", padx=5, pady=8)

        info = tk.Frame(card, bg=bg, cursor="hand2")
        info.pack(side="left", fill="x", expand=True, pady=5)
        name = tk.Label(
            info,
            text=drive.name,
            font=("Sans", 9, "bold"),
            bg=bg,
            fg=TEXT,
            anchor="w",
            cursor="hand2",
        )
        name.pack(fill="x")
        subtitle = tk.Label(
            info,
            text=f"{drive.device} · {drive.size}",
            font=("Sans", 7),
            bg=bg,
            fg=MUTED,
            anchor="w",
            cursor="hand2",
        )
        subtitle.pack(fill="x")

        temperature = tk.Label(
            card,
            text="—" if drive.temperature is None else f"{drive.temperature:.0f}°",
            font=("Sans", 11, "bold"),
            bg=bg,
            fg=temp_color(drive.temperature),
            cursor="hand2",
        )
        temperature.pack(side="right", padx=8)

        # Das Ereignis wird rekursiv an die Karte und alle Unterelemente gebunden.
        # Dadurch reagieren auch Modellname, Gerätename und Temperatur zuverlässig.
        self._bind_tree(card, drive.device)

    def _bind_tree(self, widget: tk.Misc, device: str) -> None:
        widget.bind("<Button-1>", lambda _event, dev=device: self._on_select(dev))
        widget.bind("<Return>", lambda _event, dev=device: self._on_select(dev))
        widget.bind("<space>", lambda _event, dev=device: self._on_select(dev))
        for child in widget.winfo_children():
            self._bind_tree(child, device)
