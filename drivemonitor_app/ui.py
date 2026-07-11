from __future__ import annotations
import platform
import socket
import subprocess
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Any
from .config import *
from .sensors import load_sensors
from .smart import load_drives
from .settings import load_settings, save_settings
from .report import create_html_report
from .utils import ensure_normal_user, human_bytes, notify_desktop, temp_color, primary_monitor_geometry

class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        # Application icon for window, panel and task switcher.
        icon_path = Path(__file__).resolve().parent.parent / "icons" / "drivemonitor-64.png"
        self._app_icon = None
        if icon_path.exists():
            try:
                self._app_icon = tk.PhotoImage(file=str(icon_path))
                self.iconphoto(True, self._app_icon)
            except tk.TclError:
                self._app_icon = None

        self.title(f"{APP_NAME} {APP_VERSION} – {socket.gethostname()}")
        self.configure(bg=BG)

        # Fenster automatisch an den Bildschirm anpassen:
        # etwas höher als bisher und rechts am Bildschirmrand positioniert.
        self.update_idletasks()
        virtual_w = self.winfo_screenwidth()
        virtual_h = self.winfo_screenheight()
        monitor_x, monitor_y, screen_w, screen_h = primary_monitor_geometry(virtual_w, virtual_h)

        window_w = min(1040, max(900, screen_w - 40))
        window_h = min(940, max(680, screen_h - 80))

        pos_x = monitor_x + 20
        pos_y = monitor_y + 20
        self.settings = load_settings()
        saved_geometry = self.settings.get("window_geometry", "")
        if isinstance(saved_geometry, str) and saved_geometry:
            try:
                self.geometry(saved_geometry)
            except tk.TclError:
                self.geometry(f"{window_w}x{window_h}+{pos_x}+{pos_y}")
        else:
            self.geometry(f"{window_w}x{window_h}+{pos_x}+{pos_y}")
        self.minsize(900, 680)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.drives: list[dict[str, Any]] = []
        self.sensors: list[dict[str, Any]] = []
        self.selected_device: str | None = None
        self.history: dict[str, list[float]] = {}
        self.drive_buttons: list[tuple[tk.Frame, dict[str, Any]]] = []
        self.after_id = None
        self.previous_snapshot: dict[str, dict[str, Any]] = {}
        self.events: list[str] = []
        self.last_notifications: dict[str, float] = {}

        self.build_header()
        self.build_summary()
        self.build_main()
        self.build_sensors()
        self.after(250, self.refresh)


    def on_close(self) -> None:
        """Persist window geometry and close cleanly."""
        if self.after_id:
            try:
                self.after_cancel(self.after_id)
            except tk.TclError:
                pass
        self.settings["window_geometry"] = self.geometry()
        try:
            save_settings(self.settings)
        except OSError:
            pass
        self.destroy()

    def build_header(self) -> None:
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=18, pady=(10, 6))

        tk.Label(header, text="DriveMonitor", font=("Sans", 20, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(header, text=APP_VERSION, font=("Sans", 9, "bold"),
                 bg=BG, fg=BLUE).pack(side="left", padx=(7, 0), pady=(5, 0))

        self.refresh_btn = tk.Button(
            header, text="Aktualisieren", command=self.refresh,
            relief="flat", padx=12, pady=5, cursor="hand2",
            bg="#e7ecef", fg=TEXT, activebackground="#d9e1e5"
        )
        self.refresh_btn.pack(side="right")
        tk.Button(header, text="Einstellungen", command=self.open_settings,
                  relief="flat", padx=10, pady=5, cursor="hand2",
                  bg="#e7ecef", fg=TEXT, activebackground="#d9e1e5").pack(side="right", padx=(0, 6))
        tk.Button(header, text="Bericht", command=self.save_report,
                  relief="flat", padx=10, pady=5, cursor="hand2",
                  bg="#e7ecef", fg=TEXT, activebackground="#d9e1e5").pack(side="right", padx=(0, 6))
        tk.Button(header, text="Über", command=self.show_about,
                  relief="flat", padx=10, pady=5, cursor="hand2",
                  bg="#e7ecef", fg=TEXT, activebackground="#d9e1e5").pack(side="right", padx=(0, 6))
        self.status = tk.Label(header, text="", font=("Sans", 9),
                               bg=BG, fg=MUTED)
        self.status.pack(side="right", padx=(0, 14))


    def open_settings(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("DriveMonitor-Einstellungen")
        dialog.configure(bg=CARD)
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        body = tk.Frame(dialog, bg=CARD)
        body.pack(fill="both", expand=True, padx=18, pady=16)
        tk.Label(body, text="Aktualisierungsintervall", font=("Sans", 10, "bold"),
                 bg=CARD, fg=TEXT).grid(row=0, column=0, sticky="w", pady=(0, 6))
        refresh_var = tk.StringVar(value=str(self.settings.get("refresh_seconds", 10)))
        combo = ttk.Combobox(body, textvariable=refresh_var, state="readonly",
                             values=("5", "10", "30", "60"), width=8)
        combo.grid(row=0, column=1, sticky="e", padx=(18, 0), pady=(0, 6))
        tk.Label(body, text="Sekunden", bg=CARD, fg=MUTED).grid(
            row=0, column=2, sticky="w", padx=(5, 0), pady=(0, 6))

        notify_var = tk.BooleanVar(
            value=bool(self.settings.get("notifications_enabled", True)))
        tk.Checkbutton(body, text="Desktop-Benachrichtigungen aktivieren",
                       variable=notify_var, bg=CARD, fg=TEXT,
                       activebackground=CARD, selectcolor=CARD).grid(
                           row=1, column=0, columnspan=3, sticky="w", pady=(8, 12))

        buttons = tk.Frame(body, bg=CARD)
        buttons.grid(row=2, column=0, columnspan=3, sticky="e")
        tk.Button(buttons, text="Abbrechen", command=dialog.destroy,
                  relief="flat", padx=10, pady=5,
                  bg="#e7ecef").pack(side="right")

        def apply() -> None:
            self.settings["refresh_seconds"] = int(refresh_var.get())
            self.settings["notifications_enabled"] = bool(notify_var.get())
            try:
                save_settings(self.settings)
            except OSError as exc:
                messagebox.showerror(
                    "Einstellungen",
                    f"Die Einstellungen konnten nicht gespeichert werden:\n{exc}",
                    parent=dialog,
                )
                return
            if self.after_id:
                self.after_cancel(self.after_id)
            self.after_id = self.after(
                self.settings["refresh_seconds"] * 1000, self.refresh)
            dialog.destroy()
            self.status.config(text="Einstellungen gespeichert")

        tk.Button(buttons, text="Speichern", command=apply,
                  relief="flat", padx=12, pady=5, bg=BLUE, fg="white",
                  activebackground=BLUE, activeforeground="white").pack(
                      side="right", padx=(0, 7))
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

    def save_report(self) -> None:
        if not self.drives:
            messagebox.showinfo(
                "SMART-Bericht",
                "Es sind noch keine Laufwerksdaten verfügbar.",
                parent=self,
            )
            return
        default_name = time.strftime("DriveMonitor-Bericht-%Y-%m-%d.html")
        filename = filedialog.asksaveasfilename(
            parent=self,
            title="SMART-Bericht speichern",
            defaultextension=".html",
            initialfile=default_name,
            filetypes=[("HTML-Bericht", "*.html")],
        )
        if not filename:
            return
        try:
            create_html_report(filename, self.drives, socket.gethostname())
        except OSError as exc:
            messagebox.showerror(
                "SMART-Bericht",
                f"Der Bericht konnte nicht gespeichert werden:\n{exc}",
                parent=self,
            )
            return
        self.add_event(f"SMART-Bericht gespeichert: {Path(filename).name}")
        self.render_events()
        messagebox.showinfo(
            "SMART-Bericht",
            f"Der Bericht wurde gespeichert:\n{filename}",
            parent=self,
        )

    def show_about(self) -> None:
        try:
            result = subprocess.run(
                ["smartctl", "--version"],
                text=True, capture_output=True, timeout=3, check=False,
            )
            smartctl_version = (result.stdout.splitlines() or ["unbekannt"])[0]
        except (OSError, subprocess.SubprocessError):
            smartctl_version = "unbekannt"

        system_name = platform.freedesktop_os_release().get(
            "PRETTY_NAME", platform.system()
        ) if hasattr(platform, "freedesktop_os_release") else platform.system()

        messagebox.showinfo(
            "Über DriveMonitor",
            f"{APP_NAME} {APP_VERSION}\n\n"
            "SMART- und Temperaturüberwachung für Linux\n\n"
            f"System: {system_name}\n"
            f"Kernel: {platform.release()}\n"
            f"Python: {platform.python_version()}\n"
            f"Tk: {tk.TkVersion}\n"
            f"smartctl: {smartctl_version}\n\n"
            "Die Oberfläche läuft als normaler Benutzer.\n"
            "Nur der streng begrenzte SMART-Helfer erhält Root-Rechte.\n\n"
            "Hinweis: DriveMonitor ersetzt keine regelmäßige Datensicherung.",
            parent=self,
        )

    def build_summary(self) -> None:
        self.summary = tk.Frame(self, bg=BG)
        self.summary.pack(fill="x", padx=18, pady=(0, 7))

    def build_main(self) -> None:
        self.main = tk.Frame(self, bg=BG)
        self.main.pack(fill="both", expand=True, padx=18, pady=(0, 7))
        self.main.grid_columnconfigure(0, weight=0, minsize=320)
        self.main.grid_columnconfigure(1, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

        left = tk.Frame(self.main, bg=CARD, highlightthickness=1,
                        highlightbackground=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        tk.Label(left, text="Laufwerke", font=("Sans", 11, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w", padx=10, pady=(9, 5))
        self.drive_list = tk.Frame(left, bg=CARD)
        self.drive_list.pack(fill="both", expand=True, padx=7, pady=(0, 7))

        self.detail = tk.Frame(self.main, bg=CARD, highlightthickness=1,
                               highlightbackground=BORDER)
        self.detail.grid(row=0, column=1, sticky="nsew")

    def build_sensors(self) -> None:
        self.bottom_area = tk.Frame(self, bg=BG)
        self.bottom_area.pack(fill="x", padx=18, pady=(0, 10))
        self.bottom_area.grid_columnconfigure(0, weight=3)
        self.bottom_area.grid_columnconfigure(1, weight=2)
        # Genug feste Höhe reservieren, damit Sensortemperaturen auch bei der
        # kleinsten erlaubten Fenstergröße vollständig sichtbar bleiben.
        self.bottom_area.grid_rowconfigure(0, minsize=88)

        self.sensor_area = tk.Frame(self.bottom_area, bg=BG)
        self.sensor_area.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.event_area = tk.Frame(self.bottom_area, bg=BG)
        self.event_area.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    def update_history(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            key = row.get("key")
            temp = row.get("temp")
            if key and isinstance(temp, (int, float)):
                vals = self.history.setdefault(key, [])
                vals.append(float(temp))
                if len(vals) > MAX_HISTORY:
                    del vals[:-MAX_HISTORY]

    def add_event(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        entry = f"{stamp}  {message}"
        if not self.events or self.events[0] != entry:
            self.events.insert(0, entry)
        del self.events[8:]

    def maybe_notify(self, key: str, title: str, message: str,
                     urgency: str = "normal") -> None:
        if not self.settings.get("notifications_enabled", True):
            return
        now = time.time()
        if now - self.last_notifications.get(key, 0) < NOTIFY_COOLDOWN:
            return
        self.last_notifications[key] = now
        notify_desktop(title, message, urgency)

    def process_events(self) -> None:
        current = {d["device"]: d for d in self.drives}

        if not self.previous_snapshot:
            self.add_event(f"{len(self.drives)} Laufwerke erkannt")
        else:
            for device, drive in current.items():
                old = self.previous_snapshot.get(device)
                if old is None:
                    self.add_event(f"{drive['name']} wurde angeschlossen")
                    self.maybe_notify(device + ":added", "Laufwerk angeschlossen",
                                      drive["name"])
                    continue

                old_health = old.get("health")
                new_health = drive.get("health")
                if old_health != new_health:
                    self.add_event(
                        f"{drive['name']}: SMART {old_health} → {new_health}")
                    if new_health == "WARNUNG":
                        self.maybe_notify(device + ":smart", "SMART-Warnung",
                                          drive["name"], "critical")

                old_temp = old.get("temp")
                new_temp = drive.get("temp")
                if isinstance(new_temp, (int, float)):
                    if new_temp >= TEMP_CRITICAL and (
                            not isinstance(old_temp, (int, float))
                            or old_temp < TEMP_CRITICAL):
                        self.add_event(
                            f"{drive['name']}: kritische Temperatur {new_temp:.1f} °C")
                        self.maybe_notify(device + ":critical",
                                          "Kritische Laufwerkstemperatur",
                                          f"{drive['name']}: {new_temp:.1f} °C",
                                          "critical")
                    elif new_temp >= TEMP_WARNING and (
                            not isinstance(old_temp, (int, float))
                            or old_temp < TEMP_WARNING):
                        self.add_event(
                            f"{drive['name']}: Temperaturwarnung {new_temp:.1f} °C")
                        self.maybe_notify(device + ":warm",
                                          "Laufwerk wird warm",
                                          f"{drive['name']}: {new_temp:.1f} °C")

            for device, old in self.previous_snapshot.items():
                if device not in current:
                    self.add_event(f"{old['name']} wurde entfernt")

        self.previous_snapshot = {
            device: {
                "name": drive["name"],
                "health": drive.get("health"),
                "temp": drive.get("temp"),
            }
            for device, drive in current.items()
        }

    def refresh(self) -> None:
        if self.after_id:
            self.after_cancel(self.after_id)
        self.refresh_btn.config(state="disabled")
        self.status.config(text="Wird aktualisiert …")
        self.update_idletasks()

        try:
            self.sensors = load_sensors()
            self.drives = load_drives()
            self.update_history(self.sensors + self.drives)
            self.process_events()
            if not self.selected_device and self.drives:
                self.selected_device = self.drives[0]["device"]
            if self.selected_device and not any(d["device"] == self.selected_device for d in self.drives):
                self.selected_device = self.drives[0]["device"] if self.drives else None
            self.render_summary()
            self.render_drive_list()
            self.render_detail()
            self.render_sensors()
            self.render_events()
            self.status.config(text=time.strftime("Aktualisiert: %H:%M:%S"))
        except Exception as exc:
            self.status.config(text=f"Fehler: {exc}")
        finally:
            self.refresh_btn.config(state="normal")
            self.after_id = self.after(int(self.settings.get("refresh_seconds", 10)) * 1000, self.refresh)

    def render_summary(self) -> None:
        for w in self.summary.winfo_children():
            w.destroy()

        temps = [d["temp"] for d in self.drives if isinstance(d.get("temp"), (int, float))]
        hottest = max(temps) if temps else None
        smart_ok = sum(1 for d in self.drives if d.get("health") == "OK")
        cpu = next((s for s in self.sensors if s.get("group") == "CPU"), None)
        gpu = next((s for s in self.sensors if s.get("group") == "GPU"), None)
        cpu_value = f"{cpu['temp']:.0f}°" if cpu else "—"
        gpu_value = f"{gpu['temp']:.0f}°" if gpu else "—"
        cpu_gpu_color = temp_color(max(
            [sensor["temp"] for sensor in (cpu, gpu) if sensor],
            default=None,
        ))

        items = [
            ("Laufwerke", str(len(self.drives)), "erkannt", BLUE),
            ("SMART", f"{smart_ok}/{len(self.drives)} OK" if self.drives else "—",
             "Gesundheitsstatus", GREEN if smart_ok == len(self.drives) and self.drives else YELLOW),
            ("Höchste Temperatur", "—" if hottest is None else f"{hottest:.1f} °C",
             "aller Laufwerke", temp_color(hottest)),
            ("CPU / GPU", f"{cpu_value} / {gpu_value}",
             "Systemsensoren", cpu_gpu_color),
        ]

        for i, (title, value, sub, color) in enumerate(items):
            box = tk.Frame(self.summary, bg=CARD, highlightthickness=1,
                           highlightbackground=BORDER)
            box.grid(row=0, column=i, sticky="nsew",
                     padx=(0 if i == 0 else 3, 0 if i == len(items)-1 else 3))
            self.summary.grid_columnconfigure(i, weight=1)
            tk.Label(box, text=title, font=("Sans", 8, "bold"),
                     bg=CARD, fg=MUTED).pack(anchor="w", padx=9, pady=(5, 0))
            tk.Label(box, text=value, font=("Sans", 14, "bold"),
                     bg=CARD, fg=color).pack(anchor="w", padx=9)
            tk.Label(box, text=sub, font=("Sans", 7),
                     bg=CARD, fg=MUTED).pack(anchor="w", padx=9, pady=(0, 5))

    def select_drive(self, device: str) -> None:
        self.selected_device = device
        self.render_drive_list()
        self.render_detail()

    def render_drive_list(self) -> None:
        for w in self.drive_list.winfo_children():
            w.destroy()
        self.drive_buttons.clear()

        badge_colors = {"HDD": "#475569", "SSD": "#2563eb", "NVMe": "#7c3aed", "USB": "#0f766e"}
        badge_symbols = {"HDD": "◉", "SSD": "▣", "NVMe": "⚡", "USB": "↯"}

        for drive in self.drives:
            selected = drive["device"] == self.selected_device
            bg = SELECTED if selected else CARD
            frame = tk.Frame(self.drive_list, bg=bg, cursor="hand2",
                             highlightthickness=1,
                             highlightbackground=BLUE if selected else BORDER)
            frame.pack(fill="x", pady=3)

            kind = drive.get("icon", "HDD")
            badge = tk.Frame(frame, width=42, height=42,
                             bg=badge_colors.get(kind, BLUE))
            badge.pack(side="left", padx=(7, 8), pady=7)
            badge.pack_propagate(False)
            icon = tk.Label(badge, text=badge_symbols.get(kind, "•"),
                            font=("Sans", 15, "bold"), bg=badge["bg"], fg="white")
            icon.pack(expand=True)

            info = tk.Frame(frame, bg=bg)
            info.pack(side="left", fill="x", expand=True, pady=6)
            name = drive.get("name") or "Unbekanntes Laufwerk"
            tk.Label(info, text=name, font=("Sans", 9, "bold"),
                     bg=bg, fg=TEXT, anchor="w").pack(fill="x")
            subtitle = f"{kind} · {drive['size']} · {drive['device']}"
            tk.Label(info, text=subtitle, font=("Sans", 7), bg=bg,
                     fg=MUTED, anchor="w").pack(fill="x", pady=(2, 0))

            temp = drive.get("temp")
            temp_label = tk.Label(frame,
                                  text="—" if temp is None else f"{temp:.0f}°",
                                  font=("Sans", 12, "bold"), bg=bg,
                                  fg=temp_color(temp))
            temp_label.pack(side="right", padx=9)

            widgets = [frame, badge, icon, info, temp_label, *info.winfo_children()]
            for widget in widgets:
                widget.bind("<Button-1>",
                            lambda e, dev=drive["device"]: self.select_drive(dev))

    def selected(self) -> dict[str, Any] | None:
        return next((d for d in self.drives if d["device"] == self.selected_device), None)

    def render_detail(self) -> None:
        for w in self.detail.winfo_children():
            w.destroy()
        d = self.selected()
        if not d:
            tk.Label(self.detail, text="Kein Laufwerk erkannt.",
                     bg=CARD, fg=MUTED).pack(pady=40)
            return

        head = tk.Frame(self.detail, bg=CARD)
        head.pack(fill="x", padx=14, pady=(12, 5))
        name_box = tk.Frame(head, bg=CARD)
        name_box.pack(side="left", fill="x", expand=True)
        tk.Label(name_box, text=d["name"], font=("Sans", 15, "bold"),
                 bg=CARD, fg=TEXT, anchor="w").pack(fill="x")
        tk.Label(name_box, text=f"{d['icon']} · {d['device']} · {d['size']}",
                 font=("Sans", 8), bg=CARD, fg=MUTED,
                 anchor="w").pack(fill="x", pady=(2, 0))
        tk.Label(head, text="—" if d["temp"] is None else f"{d['temp']:.1f} °C",
                 font=("Sans", 20, "bold"), bg=CARD,
                 fg=temp_color(d["temp"])).pack(side="right")

        condition_state = d.get("condition_state", "neutral")
        status_colors = {
            "ok": ("#ecfdf5", GREEN),
            "warn": ("#fff7ed", ORANGE),
            "critical": ("#fef2f2", RED),
            "neutral": ("#f8fafc", MUTED),
        }
        status_bg, status_fg = status_colors.get(condition_state, status_colors["neutral"])
        status = tk.Frame(self.detail, bg=status_bg)
        status.pack(fill="x", padx=14, pady=(0, 9))
        tk.Label(status, text=f"Gesamtzustand: {d.get('condition', 'Nicht beurteilbar')}  ·  SMART: {d['health']}",
                 font=("Sans", 9, "bold"), bg=status_bg,
                 fg=status_fg).pack(anchor="w", padx=9, pady=6)

        facts = tk.Frame(self.detail, bg=CARD)
        facts.pack(fill="x", padx=14)
        fields = [
            ("Schnittstelle", d["transport"] or "—"),
            ("Firmware", d["firmware"]),
            ("Seriennummer", d["serial"]),
            ("Betriebsstunden", "—" if d["hours"] is None else f"{d['hours']:,}".replace(",", ".")),
            ("Einschaltungen", "—" if d["cycles"] is None else f"{d['cycles']:,}".replace(",", ".")),
            ("SSD-Lebensdauer", "—" if d["life"] is None else f"{d['life']} %"),
        ]
        for c in range(3):
            facts.grid_columnconfigure(c, weight=1, uniform="facts")
        for i, (label, value) in enumerate(fields):
            r, c = divmod(i, 3)
            cell = tk.Frame(facts, bg="#f8fafc", highlightthickness=1,
                            highlightbackground=BORDER)
            cell.grid(row=r, column=c, sticky="nsew", padx=(0, 6), pady=3)
            tk.Label(cell, text=label, font=("Sans", 7, "bold"),
                     bg="#f8fafc", fg=MUTED).pack(anchor="w", padx=8, pady=(5, 1))
            tk.Label(cell, text=value, font=("Sans", 9), bg="#f8fafc",
                     fg=TEXT, anchor="w").pack(fill="x", padx=8, pady=(0, 6))

        tk.Label(self.detail, text="Wichtige SMART-Werte",
                 font=("Sans", 9, "bold"), bg=CARD, fg=TEXT).pack(
                     anchor="w", padx=14, pady=(9, 3))
        smart_grid = tk.Frame(self.detail, bg=CARD)
        smart_grid.pack(fill="x", padx=14)
        details = list(d.get("smart_details") or [])
        if not details:
            details = [("SMART-Selbstbewertung", "Keine Einzelwerte verfügbar", "neutral")]
        for c in range(2):
            smart_grid.grid_columnconfigure(c, weight=1, uniform="smart")
        for i, (label, value, state) in enumerate(details[:6]):
            r, c = divmod(i, 2)
            cell = tk.Frame(smart_grid, bg="#fafbfc",
                            highlightthickness=1, highlightbackground=BORDER)
            cell.grid(row=r, column=c, sticky="nsew", padx=(0, 6), pady=3)
            indicator = "✓" if state == "ok" else ("!" if state == "warn" else "•")
            color = GREEN if state == "ok" else (RED if state == "warn" else MUTED)
            tk.Label(cell, text=indicator, font=("Sans", 10, "bold"),
                     bg="#fafbfc", fg=color).pack(side="left", padx=(7, 5), pady=6)
            labels = tk.Frame(cell, bg="#fafbfc")
            labels.pack(side="left", fill="x", expand=True, pady=4)
            tk.Label(labels, text=label, font=("Sans", 7), bg="#fafbfc",
                     fg=MUTED, anchor="w").pack(fill="x")
            tk.Label(labels, text=value, font=("Sans", 8, "bold"), bg="#fafbfc",
                     fg=color, anchor="w").pack(fill="x")

        has_crc_warning = any(
            "CRC" in label and state == "warn"
            for label, _value, state in details
        )
        if has_crc_warning:
            note = tk.Frame(self.detail, bg="#fff7ed", highlightthickness=1,
                            highlightbackground="#fed7aa")
            note.pack(fill="x", padx=14, pady=(5, 0))
            tk.Label(
                note,
                text="Hinweis: CRC-Fehler entstehen meist durch Kabel, Stecker oder USB-Adapter und bedeuten nicht automatisch einen Laufwerksdefekt.",
                font=("Sans", 7), bg="#fff7ed", fg=ORANGE,
                anchor="w", justify="left", wraplength=620
            ).pack(fill="x", padx=8, pady=5)

        usage = d.get("usage")
        tk.Label(self.detail, text="Laufwerksbelegung", font=("Sans", 9, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w", padx=14, pady=(9, 3))
        bar = tk.Canvas(self.detail, height=14, bg=BAR_BG, highlightthickness=0)
        bar.pack(fill="x", padx=14)
        percent = usage["percent"] if usage and usage.get("mounted") else 0
        bar.bind("<Configure>", lambda e, c=bar, p=percent: self.draw_usage(c, p))
        if not usage:
            usage_text = "Keine Partition erkannt"
            fs_text = ""
        elif not usage.get("mounted"):
            usage_text = "Partition erkannt, aber nicht eingehängt"
            fs_text = " · ".join(
                f"{part['device']}: {part['filesystem']}"
                for part in usage.get("partitions", [])[:3]
            )
        else:
            usage_text = (
                f"Belegt {human_bytes(usage['used'])} · Frei {human_bytes(usage['free'])} · "
                f"{usage['percent']} %"
            )
            fs_text = " · ".join(
                f"{part['device']}: {part['filesystem']} → {', '.join(part['mountpoints'])}"
                for part in usage.get("partitions", [])[:3] if part.get("mountpoints")
            )
        tk.Label(self.detail, text=usage_text, font=("Sans", 8),
                 bg=CARD, fg=MUTED).pack(anchor="w", padx=14, pady=(3, 0))
        if fs_text:
            tk.Label(self.detail, text=fs_text, font=("Sans", 7),
                     bg=CARD, fg=MUTED, anchor="w", justify="left",
                     wraplength=640).pack(fill="x", padx=14, pady=(1, 8))
        else:
            tk.Frame(self.detail, bg=CARD, height=7).pack()

        tk.Label(self.detail, text="Temperaturverlauf", font=("Sans", 9, "bold"),
                 bg=CARD, fg=TEXT).pack(anchor="w", padx=14)
        chart = tk.Canvas(self.detail, height=54, bg="#fafbfc",
                          highlightthickness=1, highlightbackground=BORDER)
        chart.pack(fill="x", padx=14, pady=(3, 12))
        vals = list(self.history.get(d["key"], []))
        chart.bind("<Configure>", lambda e, c=chart, v=vals: self.draw_chart(c, v))

    def draw_usage(self, canvas: tk.Canvas, percent: int) -> None:
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        canvas.create_rectangle(0, 0, w, h, fill=BAR_BG, outline="")
        canvas.create_rectangle(0, 0, w * max(0, min(100, percent)) / 100, h,
                                fill=GREEN if percent < 85 else YELLOW, outline="")

    def draw_chart(self, canvas: tk.Canvas, values: list[float]) -> None:
        canvas.delete("all")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if len(values) < 2:
            canvas.create_text(w/2, h/2, text="Der Verlauf wird nach einigen Aktualisierungen sichtbar.",
                               fill=MUTED, font=("Sans", 8))
            return
        low, high = min(values), max(values)
        if high - low < 1:
            high = low + 1
        points = []
        for i, val in enumerate(values):
            x = 5 + i * (w - 10) / max(1, len(values)-1)
            y = h - 5 - (val - low) / (high - low) * (h - 10)
            points.extend([x, y])
        canvas.create_line(*points, fill=temp_color(values[-1]),
                           width=2, smooth=True)
        canvas.create_text(7, 6, text=f"{high:.0f}°", anchor="nw",
                           fill=MUTED, font=("Sans", 7))
        canvas.create_text(7, h-6, text=f"{low:.0f}°", anchor="sw",
                           fill=MUTED, font=("Sans", 7))

    def render_sensors(self) -> None:
        for w in self.sensor_area.winfo_children():
            w.destroy()
        tk.Label(self.sensor_area, text="Systemsensoren", font=("Sans", 10, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 3))
        row = tk.Frame(self.sensor_area, bg=BG)
        row.pack(fill="x")
        if not self.sensors:
            tk.Label(row, text="Keine zusätzlichen Sensoren erkannt.",
                     bg=BG, fg=MUTED).pack(anchor="w")
            return
        visible = self.sensors[:6]
        symbols = {"CPU": "CPU", "GPU": "GPU", "RAM": "RAM",
                   "WLAN": "WLAN", "LAN": "LAN", "SENSOR": "TEMP"}
        for i, sensor in enumerate(visible):
            card = tk.Frame(row, bg=CARD, highlightthickness=1,
                            highlightbackground=BORDER)
            card.grid(row=0, column=i, sticky="nsew",
                      padx=(0 if i == 0 else 2, 0 if i == len(visible)-1 else 2))
            row.grid_columnconfigure(i, weight=1)
            kind = symbols.get(sensor.get("icon", "SENSOR"), sensor.get("icon", "TEMP"))
            tk.Label(card, text=kind, font=("Sans", 7, "bold"), bg=CARD,
                     fg=BLUE).pack(anchor="w", padx=7, pady=(5, 0))
            tk.Label(card, text=sensor["name"], font=("Sans", 8, "bold"),
                     bg=CARD, fg=TEXT).pack(anchor="w", padx=7, pady=(1, 0))
            tk.Label(card, text=f"{sensor['temp']:.1f} °C",
                     font=("Sans", 11, "bold"), bg=CARD,
                     fg=temp_color(sensor["temp"])).pack(anchor="w", padx=7, pady=(0, 5))

    def render_events(self) -> None:
        for w in self.event_area.winfo_children():
            w.destroy()

        tk.Label(self.event_area, text="Ereignisse",
                 font=("Sans", 10, "bold"), bg=BG, fg=TEXT).pack(
                     anchor="w", pady=(0, 3))
        box = tk.Frame(self.event_area, bg=CARD, highlightthickness=1,
                       highlightbackground=BORDER)
        box.pack(fill="both", expand=True)

        if not self.events:
            tk.Label(box, text="Noch keine Ereignisse.",
                     font=("Sans", 8), bg=CARD, fg=MUTED).pack(
                         anchor="w", padx=8, pady=8)
            return

        for entry in self.events[:4]:
            tk.Label(box, text=entry, font=("Sans", 7),
                     bg=CARD, fg=TEXT, anchor="w").pack(
                         fill="x", padx=8, pady=1)



def main() -> None:
    ensure_normal_user()
    Dashboard().mainloop()
