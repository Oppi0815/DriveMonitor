from __future__ import annotations

import queue
import socket
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path

from drivemonitor.config import APP_NAME, APP_VERSION, REFRESH_MS
from drivemonitor.core.analysis import analyse
from drivemonitor.core.dashboard import build_dashboard_summary
from drivemonitor.core.debug import build_debug_report
from drivemonitor.core.events import Event, summarize_events
from drivemonitor.core.history import (
    load_drive_temperature_history,
    load_previous_smart_values,
    load_sensor_temperature_history,
    store_snapshot,
)
from drivemonitor.core.models import DriveInfo, SensorInfo
from drivemonitor.core.preferences import mark_welcome_shown, welcome_was_shown
from drivemonitor.core.sensors import load_sensors
from drivemonitor.core.smart import load_drives
from drivemonitor.core.systeminfo import load_system_info
from drivemonitor.maintenance.checks import read_status
from .drive_list import DriveList
from .sparkline import Sparkline
from .theme import BG, BLUE, BORDER, CARD, GREEN, MUTED, RED, TEXT, YELLOW, temp_color
from .tooltip import ToolTip


class MainWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION} – {socket.gethostname()}")
        self.configure(bg=BG)
        self._set_icon()
        self._place_on_primary_screen()
        self.drives: list[DriveInfo] = []
        self.sensors: list[SensorInfo] = []
        self.events: list[Event] = []
        self.selected_device: str | None = None
        self.refresh_job: str | None = None
        self.refresh_generation = 0
        self.refresh_in_progress = False
        self.closing = False
        self._result_queue: queue.Queue[tuple] = queue.Queue()
        self.last_refresh_at: float | None = None
        self.last_check_value: tk.Label | None = None
        self.last_check_subtitle: tk.Label | None = None
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Control-d>", lambda _event: self._show_debug_report())
        self.bind("<F1>", lambda _event: self._show_about())
        self.after(100, self._poll_results)
        self.after(200, self.refresh)
        self._update_footer()
        self.after(1_000, self._update_last_check_card)


    def _set_icon(self) -> None:
        icon = Path(__file__).resolve().parents[2] / "icons" / "drivemonitor-64.png"
        if icon.exists():
            try:
                self._icon = tk.PhotoImage(file=str(icon))
                self.iconphoto(True, self._icon)
            except tk.TclError:
                self._icon = None

    def _place_on_primary_screen(self) -> None:
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        width, height = min(1180, sw - 40), min(900, sh - 80)
        x, y = max(10, (sw - width) // 2), max(10, (sh - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(860, 620)

    def _build(self) -> None:
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=18, pady=(14, 8))
        tk.Label(header, text="DriveMonitor", font=("Sans", 23, "bold"), bg=BG, fg=TEXT).pack(side="left")
        tk.Label(header, text=APP_VERSION, font=("Sans", 9, "bold"), bg=BG, fg=BLUE).pack(side="left", padx=8)
        self.status = tk.Label(header, text="Bereit", bg=BG, fg=MUTED)
        self.status.pack(side="right", padx=10)
        self.button = tk.Button(header, text="Aktualisieren", command=self.refresh, relief="flat", padx=12, pady=6)
        self.button.pack(side="right")
        self.about_button = tk.Button(header, text="Über", command=self._show_about, relief="flat", padx=10, pady=6)
        self.about_button.pack(side="right", padx=(0, 6))
        ToolTip(self.about_button, "Zeigt Programmversion, Systeminformationen, Lizenz und GitHub-Projekt.")

        # Der komplette Inhaltsbereich unterhalb der Kopfzeile ist scrollbar.
        # So bleiben auch bei einem kleinen Fenster Laufwerksdetails und
        # Systemsensoren erreichbar, während die Kopfzeile sichtbar bleibt.
        content_host = tk.Frame(self, bg=BG)
        content_host.pack(fill="both", expand=True)

        self.main_canvas = tk.Canvas(content_host, bg=BG, highlightthickness=0)
        self.main_scrollbar = tk.Scrollbar(content_host, orient="vertical", command=self.main_canvas.yview)
        self.page = tk.Frame(self.main_canvas, bg=BG)
        self._page_window = self.main_canvas.create_window((0, 0), window=self.page, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        self.page.bind("<Configure>", self._update_main_scrollregion)
        self.main_canvas.bind("<Configure>", self._resize_main_page)
        self.main_canvas.bind("<Enter>", self._bind_main_mousewheel)
        self.main_canvas.bind("<Leave>", self._unbind_main_mousewheel)
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.main_scrollbar.pack(side="right", fill="y")

        self.hero = tk.Frame(self.page, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        self.hero.pack(fill="x", padx=18, pady=(0, 8))

        self.summary = tk.Frame(self.page, bg=BG)
        self.summary.pack(fill="x", padx=18, pady=(0, 6))

        self.health_strip = tk.Frame(self.page, bg=CARD, highlightthickness=1, highlightbackground=BORDER, cursor="hand2")
        self.health_strip.pack(fill="x", padx=18, pady=(0, 8))
        self.health_strip.bind("<Button-1>", lambda _event: self._show_events())

        body = tk.Frame(self.page, bg=BG)
        body.pack(fill="both", padx=18, pady=(0, 10))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(left, text="Laufwerke", font=("Sans", 12, "bold"), bg=CARD, fg=TEXT).pack(anchor="w", padx=12, pady=(11, 8))
        self.drive_list = DriveList(left, self._select)
        self.drive_list.pack(fill="both", expand=True, padx=7, pady=(0, 7))

        self.detail = tk.Frame(body, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        self.detail.grid(row=0, column=1, sticky="nsew")

        self.bottom = tk.Frame(self.page, bg=BG)
        self.bottom.pack(fill="x", padx=18, pady=(0, 10))

        self.footer = tk.Frame(self.page, bg=BG)
        self.footer.pack(fill="x", padx=18, pady=(0, 12))
        self.footer_label = tk.Label(
            self.footer,
            text=self._footer_text(),
            font=("Sans", 7),
            bg=BG,
            fg=MUTED,
        )
        self.footer_label.pack(anchor="w")

    def _update_main_scrollregion(self, _event=None) -> None:
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))

    def _resize_main_page(self, event) -> None:
        # Die innere Seite bleibt so breit wie der sichtbare Canvas. Dadurch
        # entsteht nur vertikales, niemals unnötiges horizontales Scrollen.
        self.main_canvas.itemconfigure(self._page_window, width=event.width)

    def _bind_main_mousewheel(self, _event=None) -> None:
        self.bind_all("<MouseWheel>", self._on_main_mousewheel)
        self.bind_all("<Button-4>", self._on_main_mousewheel)
        self.bind_all("<Button-5>", self._on_main_mousewheel)

    def _unbind_main_mousewheel(self, _event=None) -> None:
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _on_main_mousewheel(self, event) -> str:
        if getattr(event, "num", None) == 4:
            steps = -1
        elif getattr(event, "num", None) == 5:
            steps = 1
        else:
            delta = getattr(event, "delta", 0)
            steps = -1 if delta > 0 else 1
        self.main_canvas.yview_scroll(steps, "units")
        return "break"

    def refresh(self) -> None:
        # Während eine Prüfung läuft, wird keine zweite Hintergrundabfrage
        # gestartet. Das verhindert Doppelklicks und überlappende automatische
        # Aktualisierungen, die unnötig SMART und die Paketverwaltung belasten.
        if self.closing or self.refresh_in_progress:
            return
        if self.refresh_job:
            try:
                self.after_cancel(self.refresh_job)
            except tk.TclError:
                pass
            self.refresh_job = None
        self.refresh_in_progress = True
        self.refresh_generation += 1
        generation = self.refresh_generation
        self.button.config(state="disabled")
        self.status.config(text="Daten und Systemupdates werden gelesen …")
        threading.Thread(target=self._collect, args=(generation,), daemon=True).start()

    def _collect(self, generation: int) -> None:
        try:
            drives = load_drives()
            sensors = load_sensors()
            system = load_system_info()
            # Die Systemupdates werden bei jeder Prüfung neu gelesen. Dadurch
            # übernimmt das Dashboard Änderungen aus der Aktualisierungsverwaltung
            # sofort, ohne dass DriveMonitor neu gestartet werden muss.
            maintenance = read_status()
            previous = load_previous_smart_values()
            analysis = analyse(drives, sensors, previous, maintenance.reboot_required, maintenance.updates_available)
            self._result_queue.put(("ok", generation, drives, sensors, system, maintenance, analysis.events))
        except Exception as exc:
            self._result_queue.put(("error", generation, str(exc)))

    def _poll_results(self) -> None:
        # Tkinter wird ausschließlich im GUI-Thread aktualisiert. Der
        # Hintergrund-Thread legt seine Ergebnisse nur in dieser Queue ab.
        if self.closing:
            return
        try:
            while True:
                result = self._result_queue.get_nowait()
                kind, generation, *payload = result
                if generation != self.refresh_generation:
                    continue
                if kind == "ok":
                    self._apply(*payload)
                else:
                    self._failed(payload[0])
                self._finish_refresh_cycle()
        except queue.Empty:
            pass
        self.after(100, self._poll_results)

    def _finish_refresh_cycle(self) -> None:
        self.refresh_in_progress = False
        if not self.closing:
            self.button.config(state="normal")
            self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        if self.closing:
            return
        if self.refresh_job:
            try:
                self.after_cancel(self.refresh_job)
            except tk.TclError:
                pass
        self.refresh_job = self.after(REFRESH_MS, self.refresh)

    def _failed(self, message: str) -> None:
        self.status.config(text=f"Fehler: {message}")

    def _on_close(self) -> None:
        self.closing = True
        if self.refresh_job:
            try:
                self.after_cancel(self.refresh_job)
            except tk.TclError:
                pass
            self.refresh_job = None
        self.destroy()

    def _apply(self, drives, sensors, system, maintenance, events) -> None:
        self.drives, self.sensors, self.events = drives, sensors, events
        self.last_refresh_at = time.time()
        if not self.selected_device and drives:
            self.selected_device = drives[0].device
        if self.selected_device and not any(d.device == self.selected_device for d in drives):
            self.selected_device = drives[0].device if drives else None

        self._render_hero(system, maintenance)
        self._render_summary(system, maintenance)
        self._render_health_strip()
        self._render_list()
        self._render_detail()
        self._render_bottom()

        try:
            store_snapshot(self.drives, self.sensors)
        except Exception:
            pass

        self.status.config(text=time.strftime("Aktualisiert: %H:%M:%S"))
        self._update_footer()
        if not welcome_was_shown():
            self.after(250, self._show_welcome)

    def _render_hero(self, system, maintenance) -> None:
        for widget in self.hero.winfo_children():
            widget.destroy()

        dashboard = build_dashboard_summary(self.events)
        score_color = GREEN if dashboard.score >= 90 else (YELLOW if dashboard.score >= 70 else RED)
        state_symbol = "●"

        left = tk.Frame(self.hero, bg=CARD)
        left.pack(side="left", padx=18, pady=14)
        tk.Label(left, text="Rechnerzustand", font=("Sans", 9, "bold"), bg=CARD, fg=MUTED).pack(anchor="w")
        line = tk.Frame(left, bg=CARD)
        line.pack(anchor="w", pady=(2, 0))
        tk.Label(line, text=state_symbol, font=("Sans", 18, "bold"), bg=CARD, fg=score_color).pack(side="left", padx=(0, 8))
        tk.Label(line, text=f"{dashboard.score} %", font=("Sans", 24, "bold"), bg=CARD, fg=score_color).pack(side="left")
        tk.Label(left, text=dashboard.grade, font=("Sans", 9, "bold"), bg=CARD, fg=score_color).pack(anchor="w")

        center = tk.Frame(self.hero, bg=CARD)
        center.pack(side="left", fill="both", expand=True, padx=(8, 18), pady=14)
        tk.Label(center, text=dashboard.headline, font=("Sans", 13, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(center, text=dashboard.explanation, font=("Sans", 9), bg=CARD, fg=MUTED, wraplength=570, justify="left").pack(anchor="w", pady=(3, 4))
        tk.Label(center, text=dashboard.recommendation, font=("Sans", 9, "bold"), bg=CARD, fg=TEXT, wraplength=570, justify="left").pack(anchor="w")

        checks = tk.Frame(self.hero, bg="#f8fafc", highlightthickness=1, highlightbackground=BORDER)
        checks.pack(side="right", padx=14, pady=12)
        smart_ok = not any(event.level in {"warning", "critical"} and event.category == "SMART" for event in self.events)
        temp_ok = not any(event.level in {"warning", "critical"} and event.category == "Sensoren" for event in self.events)
        updates_ok = not maintenance.reboot_required and maintenance.updates_available in {0, None}
        rows = [
            ("SMART", smart_ok, f"{len(self.drives)} Laufwerke geprüft"),
            ("Temperaturen", temp_ok, "im Normalbereich" if temp_ok else "bitte prüfen"),
            ("Linux Mint", updates_ok, "aktuell" if updates_ok else "Systemupdates prüfen"),
        ]
        for title, ok, subtitle in rows:
            row = tk.Frame(checks, bg="#f8fafc")
            row.pack(fill="x", padx=10, pady=4)
            tk.Label(row, text="✓" if ok else "!", font=("Sans", 10, "bold"), bg="#f8fafc", fg=GREEN if ok else YELLOW).pack(side="left", padx=(0, 7))
            text = tk.Frame(row, bg="#f8fafc")
            text.pack(side="left")
            tk.Label(text, text=title, font=("Sans", 8, "bold"), bg="#f8fafc", fg=TEXT).pack(anchor="w")
            tk.Label(text, text=subtitle, font=("Sans", 7), bg="#f8fafc", fg=MUTED).pack(anchor="w")

    def _show_welcome(self) -> None:
        mark_welcome_shown()
        dialog = tk.Toplevel(self)
        dialog.title("Willkommen bei DriveMonitor Professional")
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.grab_set()

        card = tk.Frame(dialog, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(padx=18, pady=18)
        tk.Label(card, text="DriveMonitor Professional", font=("Sans", 18, "bold"), bg=CARD, fg=TEXT).pack(padx=28, pady=(22, 2))
        tk.Label(card, text="Willkommen", font=("Sans", 11, "bold"), bg=CARD, fg=GREEN).pack()
        message = (
            "Alle erkannten Laufwerke werden regelmäßig geprüft.\n\n"
            "Die SMART- und Temperaturhistorie wird im Hintergrund aufgebaut. "
            "Nach mehreren Messungen stehen aussagekräftige Verlaufsgrafiken "
            "und Trendbewertungen zur Verfügung."
        )
        tk.Label(card, text=message, font=("Sans", 9), bg=CARD, fg=MUTED, justify="center", wraplength=430).pack(padx=28, pady=18)
        tk.Button(card, text="Los geht’s", command=dialog.destroy, relief="flat", padx=18, pady=7).pack(pady=(0, 22))
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - dialog.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - dialog.winfo_height()) // 2)
        dialog.geometry(f"+{x}+{y}")

    def _footer_text(self) -> str:
        checked = self._last_check_text() if self.last_refresh_at is not None else "noch nicht geprüft"
        return f"DriveMonitor Professional {APP_VERSION} · Letzte SMART-Prüfung: {checked} · Entwickelt für Linux Mint"

    def _update_footer(self) -> None:
        if hasattr(self, "footer_label") and self.footer_label.winfo_exists():
            self.footer_label.config(text=self._footer_text())

    def _card(self, parent, title, value, subtitle, color, tooltip: str | None = None):
        frame = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        tk.Label(frame, text=title, font=("Sans", 8, "bold"), bg=CARD, fg=MUTED).pack(anchor="w", padx=11, pady=(8, 1))
        tk.Label(frame, text=value, font=("Sans", 16, "bold"), bg=CARD, fg=color).pack(anchor="w", padx=11)
        tk.Label(frame, text=subtitle, font=("Sans", 7), bg=CARD, fg=MUTED).pack(anchor="w", padx=11, pady=(1, 8))
        if tooltip:
            ToolTip(frame, tooltip)
            for child in frame.winfo_children():
                ToolTip(child, tooltip)
        return frame

    def _sensor_card(self, parent: tk.Misc, sensor: SensorInfo) -> tk.Frame:
        frame = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        tk.Label(frame, text=sensor.group, font=("Sans", 8, "bold"), bg=CARD, fg=MUTED).pack(anchor="w", padx=10, pady=(7, 0))
        tk.Label(
            frame,
            text=f"{sensor.temperature:.1f} °C",
            font=("Sans", 15, "bold"),
            bg=CARD,
            fg=temp_color(sensor.temperature),
        ).pack(anchor="w", padx=10)
        try:
            points = load_sensor_temperature_history(sensor.key, limit=18)
            values = [point.temperature for point in points]
        except Exception:
            values = []
        Sparkline(
            frame,
            values,
            line_color=temp_color(sensor.temperature),
            height=26,
        ).pack(fill="x", padx=8, pady=(0, 1))
        tk.Label(frame, text=sensor.name, font=("Sans", 7), bg=CARD, fg=MUTED).pack(anchor="w", padx=10, pady=(0, 7))
        return frame

    def _render_summary(self, system, maintenance) -> None:
        for widget in self.summary.winfo_children():
            widget.destroy()

        temps = [drive.temperature for drive in self.drives if drive.temperature is not None]
        hottest = max(temps) if temps else None
        ok_count = sum(drive.health == "OK" for drive in self.drives)
        dashboard = build_dashboard_summary(self.events)
        state_color = GREEN if dashboard.score >= 90 else (YELLOW if dashboard.score >= 70 else RED)

        if maintenance.reboot_required:
            update_value, update_subtitle, update_color = "Neustart", "empfohlen", RED
        elif maintenance.updates_available is None:
            update_value, update_subtitle, update_color = "—", "Status unbekannt", MUTED
        elif maintenance.updates_available == 0:
            update_value, update_subtitle, update_color = "Aktuell", "Keine Updates verfügbar", GREEN
        else:
            update_value, update_subtitle, update_color = str(maintenance.updates_available), "Systemupdates verfügbar", BLUE

        items = [
            ("Laufwerke", str(len(self.drives)), f"{ok_count} SMART geprüft", BLUE, "Anzahl der erkannten Laufwerke und erfolgreich geprüften SMART-Zustände."),
            ("Temperaturen", "—" if hottest is None else f"{hottest:.1f} °C", "Maximum aller Laufwerke", temp_color(hottest), "Höchste aktuell gemessene Laufwerkstemperatur."),
            ("Systemupdates", update_value, update_subtitle, update_color, "Verfügbare Aktualisierungen der Linux-Mint-Paketverwaltung."),
        ]
        for index, item in enumerate(items):
            self.summary.grid_columnconfigure(index, weight=1)
            self._card(self.summary, *item).grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=(0 if index == 0 else 4, 4),
            )

        self.summary.grid_columnconfigure(3, weight=1)
        last_card = tk.Frame(self.summary, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        last_card.grid(row=0, column=3, sticky="nsew", padx=(4, 0))
        tk.Label(last_card, text="Letzte Prüfung", font=("Sans", 8, "bold"), bg=CARD, fg=MUTED).pack(anchor="w", padx=11, pady=(8, 1))
        self.last_check_value = tk.Label(last_card, text=self._last_check_text(), font=("Sans", 16, "bold"), bg=CARD, fg=GREEN)
        self.last_check_value.pack(anchor="w", padx=11)
        self.last_check_subtitle = tk.Label(last_card, text="automatisch aktualisiert", font=("Sans", 7), bg=CARD, fg=MUTED)
        self.last_check_subtitle.pack(anchor="w", padx=11, pady=(1, 8))
        ToolTip(last_card, "Zeitpunkt der letzten vollständig abgeschlossenen SMART-, Sensor- und Systemupdate-Prüfung.")

    def _last_check_text(self) -> str:
        if self.last_refresh_at is None:
            return "Noch nicht"
        seconds = max(0, int(time.time() - self.last_refresh_at))
        if seconds < 10:
            return "gerade eben"
        if seconds < 60:
            return f"vor {seconds} s"
        minutes = seconds // 60
        if minutes == 1:
            return "vor 1 Minute"
        if minutes < 60:
            return f"vor {minutes} Minuten"
        hours = minutes // 60
        if hours == 1:
            return "vor 1 Stunde"
        return f"vor {hours} Stunden"

    def _update_last_check_card(self) -> None:
        if self.last_check_value is not None and self.last_check_value.winfo_exists():
            self.last_check_value.config(text=self._last_check_text())
        self._update_footer()
        self.after(1_000, self._update_last_check_card)

    def _render_health_strip(self) -> None:
        for widget in self.health_strip.winfo_children():
            widget.destroy()

        summary = summarize_events(self.events)
        color = GREEN if summary.level in {"ok", "info"} else (YELLOW if summary.level == "warning" else RED)
        active_events = [event for event in self.events if event.level != "ok"]
        warnings = sum(event.level == "warning" for event in active_events)
        critical = sum(event.level == "critical" for event in active_events)
        information = sum(event.level == "info" for event in active_events)

        tk.Label(self.health_strip, text="●", font=("Sans", 12, "bold"), bg=CARD, fg=color, cursor="hand2").pack(side="left", padx=(12, 6), pady=8)
        tk.Label(self.health_strip, text=summary.title, font=("Sans", 9, "bold"), bg=CARD, fg=color, cursor="hand2").pack(side="left")
        if critical:
            compact_message = f"{critical} kritisch · {warnings} Warnungen · {information} Informationen"
        elif warnings:
            warning_text = "1 Warnung" if warnings == 1 else f"{warnings} Warnungen"
            compact_message = f"{warning_text} · {information} Informationen"
        elif information:
            info_text = "1 Information" if information == 1 else f"{information} Informationen"
            compact_message = f"{info_text} · keine Warnungen"
        else:
            compact_message = "Keine Warnungen oder kritischen Ereignisse"
        tk.Label(self.health_strip, text=compact_message, font=("Sans", 8), bg=CARD, fg=MUTED, cursor="hand2").pack(side="left", padx=10)

        category_levels = {"SMART": "ok", "Sensoren": "ok", "Systemupdates": "ok"}
        for event in self.events:
            current = category_levels.get(event.category, "ok")
            ranks = {"ok": 0, "info": 1, "warning": 2, "critical": 3}
            if ranks.get(event.level, 0) > ranks.get(current, 0):
                category_levels[event.category] = event.level

        count = len(active_events)
        tk.Label(self.health_strip, text=f"{count} Meldung" if count == 1 else f"{count} Meldungen", font=("Sans", 8, "bold"), bg=CARD, fg=BLUE, cursor="hand2").pack(side="right", padx=(4, 12), pady=7)
        for category in ("Systemupdates", "Sensoren", "SMART"):
            level = category_levels[category]
            component_color = GREEN if level in {"ok", "info"} else (YELLOW if level == "warning" else RED)
            tk.Label(self.health_strip, text=f"● {category}", font=("Sans", 8, "bold"), bg=CARD, fg=component_color, cursor="hand2").pack(side="right", padx=(4, 8), pady=7)

        for child in self.health_strip.winfo_children():
            child.bind("<Button-1>", lambda _event: self._show_events())

    def _render_list(self) -> None:
        self.drive_list.render(self.drives, self.selected_device)

    def _select(self, device: str) -> None:
        self.selected_device = device
        self._render_list()
        self._render_detail()

    def _render_detail(self) -> None:
        for widget in self.detail.winfo_children():
            widget.destroy()
        drive = next((item for item in self.drives if item.device == self.selected_device), None)
        if not drive:
            tk.Label(self.detail, text="Kein Laufwerk erkannt.", bg=CARD, fg=MUTED).pack(pady=40)
            return

        head = tk.Frame(self.detail, bg=CARD)
        head.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(head, text=drive.name, font=("Sans", 17, "bold"), bg=CARD, fg=TEXT).pack(side="left")
        tk.Label(head, text="—" if drive.temperature is None else f"{drive.temperature:.1f} °C", font=("Sans", 20, "bold"), bg=CARD, fg=temp_color(drive.temperature)).pack(side="right")

        smart_fg = GREEN if drive.health == "OK" else YELLOW
        tk.Label(
            self.detail,
            text=f"SMART-Zustand: {drive.health}",
            font=("Sans", 10, "bold"),
            bg="#ecfdf5" if drive.health == "OK" else "#fff7ed",
            fg=smart_fg,
            anchor="w",
            padx=10,
            pady=7,
        ).pack(fill="x", padx=16)

        facts = tk.Frame(self.detail, bg=CARD)
        facts.pack(fill="x", padx=16, pady=10)
        fields = [
            ("Gerät", drive.device),
            ("Typ", drive.kind),
            ("Kapazität", drive.size),
            ("Schnittstelle", drive.transport or "—"),
            ("Firmware", drive.firmware),
            ("Seriennummer", drive.serial),
            ("Betriebsstunden", "—" if drive.power_on_hours is None else f"{drive.power_on_hours:,}".replace(",", ".")),
            ("Einschaltungen", "—" if drive.power_cycles is None else str(drive.power_cycles)),
            ("SSD-Lebensdauer", "—" if drive.life_remaining is None else f"{drive.life_remaining} %"),
        ]
        for index, (label, value) in enumerate(fields):
            row, column = divmod(index, 2)
            facts.grid_columnconfigure(column, weight=1)
            cell = tk.Frame(facts, bg=CARD)
            cell.grid(row=row, column=column, sticky="ew", padx=(0, 20), pady=4)
            tk.Label(cell, text=label, font=("Sans", 7, "bold"), bg=CARD, fg=MUTED).pack(anchor="w")
            tk.Label(cell, text=value, font=("Sans", 9), bg=CARD, fg=TEXT).pack(anchor="w")

        try:
            history = load_drive_temperature_history(drive.device, limit=24)
            history_values = [point.temperature for point in history]
        except Exception:
            history_values = []
        chart_background = "#f8fafc"
        chart_box = tk.Frame(self.detail, bg=chart_background, highlightthickness=1, highlightbackground=BORDER)
        chart_box.pack(fill="x", padx=16, pady=(5, 8))
        chart_header = tk.Frame(chart_box, bg=chart_background)
        chart_header.pack(fill="x", padx=10, pady=(7, 0))
        tk.Label(chart_header, text="Temperaturverlauf", font=("Sans", 9, "bold"), bg=chart_background, fg=TEXT).pack(side="left")
        if history_values:
            stats = f"Min {min(history_values):.0f}°  ·  Max {max(history_values):.0f}°  ·  {len(history_values)} Messungen"
        else:
            stats = "Trend wird aufgebaut"
        tk.Label(chart_header, text=stats, font=("Sans", 7), bg=chart_background, fg=MUTED).pack(side="right")
        Sparkline(
            chart_box,
            history_values,
            line_color=temp_color(drive.temperature),
            height=44,
            background=chart_background,
        ).pack(fill="x", padx=8, pady=(1, 6))

        tk.Label(self.detail, text="Wichtige SMART-Werte", font=("Sans", 10, "bold"), bg=CARD, fg=TEXT).pack(anchor="w", padx=16, pady=(8, 4))
        for item in drive.smart_items:
            row = tk.Frame(self.detail, bg=CARD)
            row.pack(fill="x", padx=16, pady=2)
            label_widget = tk.Label(row, text=item.label, bg=CARD, fg=TEXT)
            label_widget.pack(side="left")
            item_color = GREEN if item.state == "ok" else (RED if item.state == "critical" else (YELLOW if item.state in {"warn", "warning"} else BLUE if item.state == "info" else MUTED))
            value_widget = tk.Label(row, text=item.value, bg=CARD, fg=item_color, font=("Sans", 9, "bold"))
            value_widget.pack(side="right")
            explanations = {
                "CRC-Fehler": "CRC-Fehler entstehen meist durch SATA-Kabel oder Steckverbindungen. Entscheidend ist, ob der Zähler weiter steigt.",
                "Wiederzugewiesene Sektoren": "Bereits ersetzte fehlerhafte Sektoren. Ein steigender Wert sollte ernst genommen werden.",
                "Ausstehende Sektoren": "Sektoren, die derzeit nicht zuverlässig gelesen werden können.",
                "Unkorrigierbare Fehler": "Fehler, die vom Laufwerk nicht korrigiert werden konnten.",
                "Unkorrigierbare Sektoren": "Sektoren, deren Daten nicht wiederhergestellt werden konnten.",
                "Medien-/Datenfehler": "Vom NVMe-Laufwerk erkannte Fehler beim Lesen oder Schreiben.",
                "Fehlerprotokolleinträge": "Kumulativer NVMe-Protokollzähler; allein kein Hinweis auf einen Defekt.",
                "Kritische Warnungen": "NVMe-Warnstatus für ernsthafte Laufwerksprobleme.",
            }
            if item.label in explanations:
                ToolTip(row, explanations[item.label])
                ToolTip(label_widget, explanations[item.label])
                ToolTip(value_widget, explanations[item.label])
            if item.state == "info" and item.label == "Fehlerprotokolleinträge":
                tk.Label(self.detail, text="ℹ Kumulativer NVMe-Zähler; allein kein Hinweis auf einen Defekt.", bg=CARD, fg=MUTED, font=("Sans", 7), anchor="w").pack(fill="x", padx=16, pady=(0, 3))

        drive_events = [event for event in self.events if event.device == drive.device]
        if drive_events:
            tk.Label(self.detail, text="Analyse", font=("Sans", 10, "bold"), bg=CARD, fg=TEXT).pack(anchor="w", padx=16, pady=(10, 4))
            for event in drive_events[:3]:
                event_color = RED if event.level == "critical" else (YELLOW if event.level == "warning" else BLUE)
                tk.Label(self.detail, text=f"● {event.message}", bg=CARD, fg=event_color, font=("Sans", 8), anchor="w", justify="left", wraplength=650).pack(fill="x", padx=16, pady=1)

        if drive.error:
            tk.Label(self.detail, text=drive.error, bg=CARD, fg=YELLOW, wraplength=600, justify="left").pack(anchor="w", padx=16, pady=10)

    def _render_bottom(self) -> None:
        for widget in self.bottom.winfo_children():
            widget.destroy()
        tk.Label(self.bottom, text="Systemsensoren", font=("Sans", 11, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        row = tk.Frame(self.bottom, bg=BG)
        row.pack(fill="x", pady=(4, 0))
        for index, sensor in enumerate(self.sensors[:6]):
            row.grid_columnconfigure(index, weight=1)
            self._sensor_card(row, sensor).grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=(0 if index == 0 else 3, 0 if index == min(5, len(self.sensors) - 1) else 3),
            )

    def _show_events(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("DriveMonitor – Ereignisse")
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.geometry("760x520")

        header = tk.Frame(dialog, bg=BG)
        header.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(header, text="Systemereignisse", font=("Sans", 16, "bold"), bg=BG, fg=TEXT).pack(side="left")
        tk.Button(header, text="Debug-Bericht", command=lambda: self._show_debug_report(dialog), relief="flat", padx=10, pady=5).pack(side="right")

        dashboard = build_dashboard_summary(self.events)
        score_color = GREEN if dashboard.score >= 90 else (YELLOW if dashboard.score >= 70 else RED)
        overview = tk.Frame(dialog, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        overview.pack(fill="x", padx=16, pady=(0, 10))
        score_box = tk.Frame(overview, bg=CARD)
        score_box.pack(side="left", padx=14, pady=10)
        tk.Label(score_box, text="Rechnerzustand", font=("Sans", 8, "bold"), bg=CARD, fg=MUTED).pack(anchor="w")
        tk.Label(score_box, text=f"{dashboard.score} %", font=("Sans", 22, "bold"), bg=CARD, fg=score_color).pack(anchor="w")
        tk.Label(score_box, text=dashboard.grade, font=("Sans", 8, "bold"), bg=CARD, fg=score_color).pack(anchor="w")

        message_box = tk.Frame(overview, bg=CARD)
        message_box.pack(side="left", fill="both", expand=True, padx=(10, 14), pady=10)
        tk.Label(message_box, text=dashboard.headline, font=("Sans", 10, "bold"), bg=CARD, fg=TEXT).pack(anchor="w")
        tk.Label(message_box, text=dashboard.explanation, font=("Sans", 8), bg=CARD, fg=MUTED, wraplength=510, justify="left").pack(anchor="w", pady=(2, 4))
        tk.Label(message_box, text=f"Empfehlung: {dashboard.recommendation}", font=("Sans", 8), bg=CARD, fg=TEXT, wraplength=510, justify="left").pack(anchor="w")

        canvas = tk.Canvas(dialog, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=BG)
        content.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 14))
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=(0, 14))

        visible = sorted(self.events, key=lambda event: event.rank, reverse=True)
        if not visible:
            tk.Label(content, text="● Heute keine Auffälligkeiten", font=("Sans", 11, "bold"), bg=BG, fg=GREEN).pack(anchor="w", pady=12)
        for event in visible:
            color = RED if event.level == "critical" else (YELLOW if event.level == "warning" else BLUE)
            symbol = "✖" if event.level == "critical" else ("⚠" if event.level == "warning" else "ℹ")
            level_name = "Kritisch" if event.level == "critical" else ("Beobachten" if event.level == "warning" else "Information")
            card = tk.Frame(content, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
            card.pack(fill="x", pady=5)
            tk.Label(card, text=f"{symbol} {level_name} · {event.title}", font=("Sans", 10, "bold"), bg=CARD, fg=color).pack(anchor="w", padx=12, pady=(9, 2))
            tk.Label(card, text=event.message, font=("Sans", 9), bg=CARD, fg=TEXT, justify="left", wraplength=670).pack(anchor="w", padx=12)
            if event.recommendation:
                tk.Label(card, text=f"Empfehlung: {event.recommendation}", font=("Sans", 8), bg=CARD, fg=MUTED, justify="left", wraplength=670).pack(anchor="w", padx=12, pady=(4, 9))
            else:
                tk.Frame(card, bg=CARD, height=7).pack()


    def _show_about(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Über DriveMonitor Professional")
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.grab_set()

        card = tk.Frame(dialog, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        card.pack(padx=20, pady=20)

        icon_path = Path(__file__).resolve().parents[2] / "icons" / "drivemonitor-128.png"
        if icon_path.exists():
            try:
                dialog._about_icon = tk.PhotoImage(file=str(icon_path))
                tk.Label(card, image=dialog._about_icon, bg=CARD).pack(pady=(20, 8))
            except tk.TclError:
                pass

        system = load_system_info()
        python_version = __import__("platform").python_version()

        tk.Label(
            card,
            text="DriveMonitor Professional",
            font=("Sans", 18, "bold"),
            bg=CARD,
            fg=TEXT,
        ).pack(padx=42)
        tk.Label(
            card,
            text=f"Version {APP_VERSION}",
            font=("Sans", 10, "bold"),
            bg=CARD,
            fg=BLUE,
        ).pack(pady=(3, 8))
        tk.Label(
            card,
            text="Gesundheitsmonitor für Laufwerke und Hardware unter Linux Mint",
            font=("Sans", 9),
            bg=CARD,
            fg=MUTED,
        ).pack(padx=28, pady=(0, 14))

        separator = tk.Frame(card, bg=BORDER, height=1)
        separator.pack(fill="x", padx=28, pady=(0, 12))

        details = tk.Frame(card, bg=CARD)
        details.pack(fill="x", padx=34)
        rows = (
            ("Betriebssystem", system.operating_system),
            ("Kernel", system.kernel),
            ("Python", python_version),
            ("Lizenz", "GNU GPL v3"),
        )
        for row, (label, value) in enumerate(rows):
            tk.Label(details, text=label, font=("Sans", 8, "bold"), bg=CARD, fg=MUTED).grid(
                row=row, column=0, sticky="w", padx=(0, 22), pady=2
            )
            tk.Label(details, text=value, font=("Sans", 8), bg=CARD, fg=TEXT).grid(
                row=row, column=1, sticky="w", pady=2
            )

        tk.Label(
            card,
            text="© 2026 Horst Oppermann",
            font=("Sans", 9),
            bg=CARD,
            fg=MUTED,
        ).pack(pady=(14, 4))

        link = tk.Label(
            card,
            text="github.com/Oppi0815/DriveMonitor",
            font=("Sans", 9, "underline"),
            bg=CARD,
            fg=BLUE,
            cursor="hand2",
        )
        link.pack(pady=(2, 14))
        link.bind("<Button-1>", lambda _event: webbrowser.open("https://github.com/Oppi0815/DriveMonitor"))

        tk.Button(card, text="Schließen", command=dialog.destroy, relief="flat", padx=18, pady=6).pack(
            pady=(0, 20)
        )
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - dialog.winfo_width()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - dialog.winfo_height()) // 2)
        dialog.geometry(f"+{x}+{y}")

    def _show_debug_report(self, parent: tk.Toplevel | None = None) -> None:
        dialog = tk.Toplevel(parent or self)
        dialog.title("DriveMonitor – Debug-Bericht")
        dialog.configure(bg=BG)
        dialog.transient(parent or self)
        dialog.geometry("820x600")
        text = tk.Text(dialog, wrap="none", font=("Monospace", 9), bg=CARD, fg=TEXT)
        text.pack(fill="both", expand=True, padx=12, pady=12)
        text.insert("1.0", build_debug_report(self.drives, self.sensors, self.events))
        text.config(state="disabled")


def run_app() -> None:
    MainWindow().mainloop()
