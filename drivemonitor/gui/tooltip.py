from __future__ import annotations

import tkinter as tk


class ToolTip:
    """Small, dependency-free tooltip for Tkinter widgets.

    Only one tooltip may be visible at a time. This prevents duplicate
    popups when the same explanation is attached to a card and its labels.
    """

    _active: "ToolTip | None" = None

    def __init__(self, widget: tk.Misc, text: str, delay_ms: int = 450) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._job: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._job = self.widget.after(self.delay_ms, self._show)

    def _cancel(self) -> None:
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def _show(self) -> None:
        if self._window is not None or not self.text:
            return
        active = ToolTip._active
        if active is not None and active is not self:
            active._hide()
        try:
            x = self.widget.winfo_rootx() + 14
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        except tk.TclError:
            return
        window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            window,
            text=self.text,
            justify="left",
            wraplength=360,
            bg="#fffbea",
            fg="#1f2937",
            relief="solid",
            borderwidth=1,
            font=("Sans", 8),
            padx=8,
            pady=5,
        )
        label.pack()
        self._window = window
        ToolTip._active = self

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._window is not None:
            try:
                self._window.destroy()
            except tk.TclError:
                pass
            self._window = None
        if ToolTip._active is self:
            ToolTip._active = None
