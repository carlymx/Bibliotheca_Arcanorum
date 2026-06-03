import json
import os
import random
import re
import ssl
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk

import urllib.request


_GITHUB_API = "https://api.github.com/repos/CaRLymx/Bibliotheca_Arcanorum/releases/latest"
_USER_AGENT = "GestorBiblioteca/1.0"


def parse_version(tag: str):
    digits = re.findall(r"\d+", tag)
    return tuple(int(x) for x in digits) if digits else (0, 0, 0)


def urlopen_with_fallback(req, timeout=10):
    try:
        import certifi
        try:
            return urllib.request.urlopen(
                req, timeout=timeout, cafile=certifi.where()
            )
        except Exception:
            pass
    except ImportError:
        pass
    ctx = ssl._create_unverified_context()
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def _subprocess_env() -> dict:
    env = dict(os.environ)
    for k in ("APPIMAGE", "APPDIR", "OWD"):
        env.pop(k, None)
    lp_key = "LD_LIBRARY_PATH"
    lp_orig = env.get(lp_key + "_ORIG")
    if lp_orig is not None:
        env[lp_key] = lp_orig
    else:
        env.pop(lp_key, None)
    return env


def open_url(url: str):
    import shutil

    DEVNULL = subprocess.DEVNULL

    if sys.platform == "darwin":
        try:
            subprocess.run(["open", url], check=True, timeout=5,
                           stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL)
            return
        except Exception:
            pass
    elif sys.platform == "win32":
        try:
            os.startfile(url)
            return
        except Exception:
            pass
    else:
        is_url = url.startswith(("http://", "https://"))

        xdg = shutil.which("xdg-open")
        if not xdg:
            for p in ("/usr/bin/xdg-open", "/usr/local/bin/xdg-open"):
                if os.path.isfile(p):
                    xdg = p
                    break
        if xdg:
            try:
                subprocess.run([xdg, url], check=True, timeout=5,
                               stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL,
                               env=_subprocess_env())
                return
            except Exception:
                pass

        try:
            import webbrowser
            if webbrowser.open(url):
                return
        except Exception:
            pass

        if is_url:
            for browser in ("firefox", "google-chrome", "chromium",
                            "chromium-browser", "brave-browser"):
                path = shutil.which(browser)
                if path:
                    try:
                        subprocess.run([path, url], check=True, timeout=10,
                                       stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL,
                                       env=_subprocess_env())
                        return
                    except Exception:
                        pass
        else:
            for fm in ("nautilus", "nemo", "thunar", "dolphin", "pcmanfm", "caja"):
                path = shutil.which(fm)
                if path:
                    try:
                        subprocess.run([path, url], check=True, timeout=10,
                                       stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL,
                                       env=_subprocess_env())
                        return
                    except Exception:
                        pass


class UpdateCheckerDialog:
    def __init__(self, parent, current_version):
        self._running = True
        self.tag = ""
        self.url = ""

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Buscar actualizaciones")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(True, True)
        self.dialog.minsize(520, 320)
        self.dialog.geometry("600x400")
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

        frame = ttk.Frame(self.dialog, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame, text=f"Versión actual: v{current_version}", font=("", 11)
        ).pack(anchor="w")

        log_frame = ttk.LabelFrame(frame, text="Registro", padding=8)
        log_frame.pack(fill="both", expand=True, pady=(10, 14))

        self._text = tk.Text(
            log_frame, wrap="word", height=12,
            state="disabled", font=("Consolas", 10),
        )
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=scroll.set)
        self._text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x")

        self._release_btn = ttk.Button(
            btn_frame, text="Ir a Release", state="disabled",
            command=self._go_release
        )
        self._release_btn.pack(side="right", padx=(4, 0))

        ttk.Button(btn_frame, text="Cerrar", command=self._on_close).pack(side="right")

        self._log(f"Iniciando comprobación (v{current_version})...")

        self._current = current_version
        threading.Thread(target=self._do_check, daemon=True).start()

    def _log(self, msg):
        if not self._running:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        text = f"[{ts}] {msg}\n"
        self.dialog.after(0, lambda: self._append_text(text))

    def _append_text(self, text):
        if not self._running:
            return
        try:
            self._text.configure(state="normal")
            self._text.insert("end", text)
            self._text.see("end")
            self._text.configure(state="disabled")
        except tk.TclError:
            pass

    def _on_close(self):
        self._running = False
        try:
            self.dialog.destroy()
        except tk.TclError:
            pass

    def _go_release(self):
        if self.url:
            open_url(self.url)
            self._on_close()

    def _do_check(self):
        def _delay():
            time.sleep(random.uniform(1, 3))

        try:
            self._log("Conectando con api.github.com...")
            _delay()
            req = urllib.request.Request(
                _GITHUB_API,
                headers={"Accept": "application/vnd.github.v3+json",
                         "User-Agent": _USER_AGENT},
            )
            resp = urlopen_with_fallback(req)
            data = json.loads(resp.read().decode())
            latest_tag = data.get("tag_name", "").lstrip("vV")
            if not latest_tag:
                _delay()
                self._log("No se pudo obtener la versión disponible.")
                return

            current_v = parse_version(self._current)
            latest_v = parse_version(latest_tag)

            _delay()
            self._log(f"Comparando v{self._current} vs v{latest_tag}...")
            _delay()
            if latest_v > current_v:
                self.tag = data.get("tag_name", "")
                self.url = data.get("html_url", "")
                self._log(f"¡Nueva versión disponible: {self.tag}!")
                self.dialog.after(0, self._enable_release)
            else:
                self._log(f"Tienes la última versión: v{self._current}")
        except Exception as e:
            _delay()
            self._log(f"Error: {e}")

    def _enable_release(self):
        if not self._running:
            return
        try:
            self._release_btn.configure(state="normal")
        except tk.TclError:
            pass
