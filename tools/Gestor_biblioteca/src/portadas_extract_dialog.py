import os
import shutil
import subprocess
import sys
import tempfile
import threading
import io
import fnmatch
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
import tkinter as tk
from typing import Dict, List, Optional, Tuple

from .utils.formatters import format_bytes

try:
    from PIL import Image
except ImportError:
    Image = None


if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _BUNDLED_DIR = sys._MEIPASS
else:
    _BUNDLED_DIR = None


def _get_pdftoppm_path() -> str:
    if _BUNDLED_DIR:
        path = Path(_BUNDLED_DIR) / ('pdftoppm.exe' if sys.platform == 'win32' else 'pdftoppm')
        if path.exists():
            return str(path)
    return shutil.which('pdftoppm') or 'pdftoppm'

try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4
    from mutagen.oggvorbis import OggVorbis
    from mutagen.flac import FLAC
    _HAS_MUTAGEN = True
except ImportError:
    _HAS_MUTAGEN = False


EXTENSIONS = {
    "PDF":      (".pdf",),
    "JPG/JPEG": (".jpg", ".jpeg"),
    "PNG":      (".png",),
    "TIFF":     (".tif", ".tiff"),
    "BMP":      (".bmp",),
    "WEBP":     (".webp",),
    "GIF":      (".gif",),
    "MP3":      (".mp3",),
    "M4A/AAC":  (".m4a", ".aac", ".mp4", ".m4b"),
    "OGG":      (".ogg",),
    "FLAC":     (".flac",),
}

FORMAT_KEYS = list(EXTENSIONS.keys())

FORMATOS_SALIDA = ["jpg", "png", "tiff", "bmp", "webp", "gif"]

OVERWRITE_OPTS = {
    "Saltar si existe": "S",
    "Reemplazar siempre": "R",
    "Preguntar cada vez": "P",
}


def _format_bytes(b: int) -> str:
    return format_bytes(b)


def _parse_exclude_patterns(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _match_exclude(path: str, patterns: List[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(os.path.basename(path), pat):
            return True
    return False


def _extract_cover_from_audio(path: str) -> Optional[bytes]:
    if not _HAS_MUTAGEN:
        return None
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".mp3":
            from mutagen.id3 import ID3
            tags = ID3(path)
            for tag in tags.getall("APIC"):
                return tag.data
        elif ext in (".m4a", ".aac", ".mp4", ".m4b"):
            audio = MP4(path)
            if "covr" in audio:
                return audio["covr"][0]
        elif ext == ".ogg":
            audio = OggVorbis(path)
            for tag in audio.get("metadata_block_picture", []):
                data = base64.b64decode(tag)
                return data
        elif ext == ".flac":
            audio = FLAC(path)
            for pic in audio.pictures:
                return pic.data
    except Exception:
        pass
    return None


# ── cover extraction helpers (shared between both dialogs) ─

def _extract_pdf_cover(src: str, dst: str, page: int,
                       resize: Optional[str]) -> bool:
    tmpdir = tempfile.mkdtemp()
    try:
        prefix = os.path.join(tmpdir, "page")
        cmd = [_get_pdftoppm_path(), "-f", str(page), "-l", str(page),
               "-png", "-r", "150", src, prefix]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        if r.returncode != 0:
            return False

        out_png = None
        for f in os.listdir(tmpdir):
            if f.endswith(".png"):
                out_png = os.path.join(tmpdir, f)
                break
        if not out_png or not os.path.exists(out_png):
            return False

        return _convert_image_file(out_png, dst, resize)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _extract_image_cover(src: str, dst: str, ext: str, fmt: str,
                         resize: Optional[str]) -> bool:
    if Image is None:
        return False

    src_fmt = ext.lstrip(".")
    if src_fmt == "jpeg":
        src_fmt = "jpg"
    if src_fmt == fmt and not resize:
        shutil.copy2(src, dst)
        return True

    return _convert_image_file(src, dst, resize)


def _extract_audio_cover(src: str, dst: str,
                         resize: Optional[str]) -> bool:
    data = _extract_cover_from_audio(src)
    if data is None or Image is None:
        return False
    try:
        img = Image.open(io.BytesIO(data))
        return _save_image_file(img, dst, resize)
    except Exception:
        return False


def _convert_image_file(src: str, dst: str,
                        resize: Optional[str]) -> bool:
    if Image is None:
        return False
    try:
        img = Image.open(src)
        return _save_image_file(img, dst, resize)
    except Exception:
        return False


def _save_image_file(img, dst: str, resize: Optional[str]) -> bool:
    try:
        if resize:
            parsed = _parse_resize_str(resize, img.width, img.height)
            if parsed:
                img = img.resize(parsed, Image.LANCZOS)
        img.save(dst)
        return True
    except Exception:
        return False


def _parse_resize_str(s: str, w: int, h: int) -> Optional[Tuple[int, int]]:
    if s.endswith("%"):
        pct = float(s[:-1]) / 100.0
        return (int(w * pct), int(h * pct))
    if s.endswith("x"):
        nw = int(s[:-1])
        nh = int(h * nw / w)
        return (nw, nh)
    if s.startswith("x"):
        nh = int(s[1:])
        nw = int(w * nh / h)
        return (nw, nh)
    return None


def _build_resize_str(modo: str, valor: str) -> Optional[str]:
    if modo == "original" or not valor:
        return None
    elif modo == "pct":
        return f"{valor}%"
    elif modo == "ancho":
        return f"{valor}x"
    elif modo == "alto":
        return f"x{valor}"
    return None


class PortadasExtractDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Extraer portadas")
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)
        self.minsize(800, 550)

        pw = max(parent.winfo_width(), 800)
        ph = max(parent.winfo_height(), 600)
        px = parent.winfo_x()
        py = parent.winfo_rooty()
        dw = min(1100, max(800, pw - 40))
        dh = min(ph - 30, max(600, ph - 50))
        x = max(0, px + (pw - dw) // 2)
        y = max(0, py + 20)
        self.geometry(f"{dw}x{dh}+{x}+{y}")

        self._cancel_event = threading.Event()
        self._overwrite_lock = threading.Lock()
        self._executor: Optional[ThreadPoolExecutor] = None
        self._running = False
        self._scan_total = 0

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── build ─────────────────────────────────────────────

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        main = ttk.Frame(self, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self._build_config(main)
        self._build_scan(main)
        self._build_progress(main)

    def _build_config(self, parent):
        scrollable = ttk.Frame(parent)
        scrollable.grid(row=0, column=0, columnspan=2, sticky="ew")
        scrollable.grid_columnconfigure(1, weight=1)

        pad = {"padx": 4, "pady": 2}

        ttk.Label(scrollable, text="Directorio ORIGEN:", font=("", 9, "bold")).grid(
            row=0, column=0, sticky="w", **pad)
        self._origen_var = tk.StringVar()
        ttk.Entry(scrollable, textvariable=self._origen_var).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(scrollable, text="Examinar...",
                   command=lambda: self._browse(self._origen_var)).grid(row=0, column=2, **pad)

        ttk.Label(scrollable, text="Directorio DESTINO:", font=("", 9, "bold")).grid(
            row=1, column=0, sticky="w", **pad)
        self._destino_var = tk.StringVar()
        ttk.Entry(scrollable, textvariable=self._destino_var).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(scrollable, text="Examinar...",
                   command=lambda: self._browse(self._destino_var)).grid(row=1, column=2, **pad)

        ttk.Label(scrollable, text="Página:", font=("", 9, "bold")).grid(
            row=2, column=0, sticky="w", **pad)
        self._pagina_var = tk.IntVar(value=1)
        ttk.Spinbox(scrollable, from_=1, to=999, textvariable=self._pagina_var, width=8).grid(
            row=2, column=1, sticky="w", **pad)

        ttk.Label(scrollable, text="Formato de salida:", font=("", 9, "bold")).grid(
            row=3, column=0, sticky="w", **pad)
        self._formato_var = tk.StringVar(value="jpg")
        ttk.Combobox(scrollable, textvariable=self._formato_var,
                     values=FORMATOS_SALIDA, state="readonly", width=10).grid(
            row=3, column=1, sticky="w", **pad)

        ttk.Label(scrollable, text="Resolución:", font=("", 9, "bold")).grid(
            row=4, column=0, sticky="w", **pad)
        res_frame = ttk.Frame(scrollable)
        res_frame.grid(row=4, column=1, columnspan=2, sticky="w", **pad)
        self._res_modo = tk.StringVar(value="alto")
        self._res_valor = tk.StringVar(value="300")

        for label, mode in [("Original", "original"), ("%", "pct"),
                            ("Ancho", "ancho"), ("Alto", "alto")]:
            ttk.Radiobutton(res_frame, text=label,
                            variable=self._res_modo, value=mode).pack(side="left", padx=(0, 4))
        ttk.Label(res_frame, text="  Valor:").pack(side="left", padx=(6, 2))
        ttk.Entry(res_frame, textvariable=self._res_valor, width=6).pack(side="left")

        ttk.Label(scrollable, text="Formatos a procesar:", font=("", 9, "bold")).grid(
            row=5, column=0, sticky="nw", **pad)
        fmt_frame = ttk.Frame(scrollable)
        fmt_frame.grid(row=5, column=1, columnspan=2, sticky="w", **pad)
        self._fmt_vars: Dict[str, tk.BooleanVar] = {}
        for i, key in enumerate(FORMAT_KEYS):
            v = tk.BooleanVar(value=True)
            self._fmt_vars[key] = v
            cb = ttk.Checkbutton(fmt_frame, text=key, variable=v)
            cb.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 12))
        btn_row = (len(FORMAT_KEYS) + 3) // 4
        bf = ttk.Frame(fmt_frame)
        bf.grid(row=btn_row, column=0, columnspan=4, sticky="w", pady=(4, 0))
        ttk.Button(bf, text="Seleccionar todo", command=self._fmt_all).pack(side="left", padx=(0, 6))
        ttk.Button(bf, text="Seleccionar ninguno", command=self._fmt_none).pack(side="left")

        ttk.Label(scrollable, text="Sobrescritura:", font=("", 9, "bold")).grid(
            row=6, column=0, sticky="w", **pad)
        self._over_var = tk.StringVar(value="Saltar si existe")
        ttk.Combobox(scrollable, textvariable=self._over_var,
                     values=list(OVERWRITE_OPTS.keys()), state="readonly", width=20).grid(
            row=6, column=1, sticky="w", **pad)

        ttk.Label(scrollable, text="Trabajos en paralelo:", font=("", 9, "bold")).grid(
            row=7, column=0, sticky="w", **pad)
        self._hilos_var = tk.IntVar(value=4)
        ttk.Spinbox(scrollable, from_=1, to=16, textvariable=self._hilos_var, width=6).grid(
            row=7, column=1, sticky="w", **pad)

        ttk.Label(scrollable, text="Excluir patrones:", font=("", 9, "bold")).grid(
            row=8, column=0, sticky="nw", **pad)
        self._exclude_text = tk.Text(scrollable, height=3, width=40)
        self._exclude_text.grid(row=8, column=1, columnspan=2, sticky="ew", **pad)
        self._exclude_text.insert("1.0", "./Portadas\n*.json\n*.js")

    def _build_scan(self, parent):
        frame = ttk.LabelFrame(parent, text="Resumen", padding=6)
        frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(6, 0))
        frame.grid_columnconfigure(0, weight=1)

        top_row = ttk.Frame(frame)
        top_row.pack(fill="x")
        self._scan_btn = ttk.Button(top_row, text="Escanear directorio",
                                    command=self._scan_dir)
        self._scan_btn.pack(side="left")
        self._scan_info = ttk.Label(top_row, text="", font=("", 9))
        self._scan_info.pack(side="left", padx=(12, 0))

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, pady=(4, 0))
        cols = ("tipo", "count", "size")
        self._scan_tree = ttk.Treeview(tree_frame, columns=cols,
                                       show="headings", height=6)
        self._scan_tree.heading("tipo", text="Tipo")
        self._scan_tree.heading("count", text="Archivos")
        self._scan_tree.heading("size", text="Tamaño")
        self._scan_tree.column("tipo", width=120)
        self._scan_tree.column("count", width=80, anchor="center")
        self._scan_tree.column("size", width=100, anchor="center")
        scb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self._scan_tree.yview)
        self._scan_tree.configure(yscrollcommand=scb.set)
        self._scan_tree.pack(side="left", fill="both", expand=True)
        scb.pack(side="right", fill="y")

    def _build_progress(self, parent):
        frame = ttk.Frame(parent)
        frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        frame.grid_columnconfigure(0, weight=1)

        self._prog = ttk.Progressbar(frame, mode="determinate")
        self._prog.pack(fill="x")

        info_row = ttk.Frame(frame)
        info_row.pack(fill="x", pady=(4, 0))
        self._current_file = ttk.Label(info_row, text="", font=("", 9))
        self._current_file.pack(side="left")
        self._counters = ttk.Label(info_row, text="", font=("", 9))
        self._counters.pack(side="right")

        log_frame = ttk.LabelFrame(frame, text="Log", padding=2)
        log_frame.pack(fill="both", expand=True, pady=(4, 0))
        self._log_text = tk.Text(log_frame, height=8, state="disabled", wrap="word")
        lsc = ttk.Scrollbar(log_frame, orient="vertical",
                            command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=lsc.set)
        self._log_text.pack(side="left", fill="both", expand=True)
        lsc.pack(side="right", fill="y")

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x", pady=(6, 0))
        self._start_btn = ttk.Button(btn_row, text="Iniciar extracción",
                                     command=self._start_extraction)
        self._start_btn.pack(side="left", padx=(0, 4))
        self._cancel_btn = ttk.Button(btn_row, text="Cancelar",
                                      command=self._cancel, state="disabled")
        self._cancel_btn.pack(side="left", padx=(0, 4))
        ttk.Button(btn_row, text="Cerrar", command=self._on_close).pack(side="right")

    # ── helpers ───────────────────────────────────────────

    def _browse(self, var):
        path = filedialog.askdirectory(parent=self)
        if path:
            var.set(path)

    def _fmt_all(self):
        for v in self._fmt_vars.values():
            v.set(True)

    def _fmt_none(self):
        for v in self._fmt_vars.values():
            v.set(False)

    def _log(self, msg: str):
        self._log_text.configure(state="normal")
        self._log_text.insert("end", msg + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _on_close(self):
        if self._running:
            if not messagebox.askyesno("Cancelar",
                    "Hay una extracción en curso. ¿Cancelar y cerrar?",
                    parent=self):
                return
            self._cancel()
        self.parent.focus_set()
        self.destroy()

    # ── scanning ──────────────────────────────────────────

    def _get_selected_exts(self) -> List[str]:
        exts = []
        for key, var in self._fmt_vars.items():
            if var.get():
                exts.extend(EXTENSIONS[key])
        return exts

    def _build_exclude_list(self) -> List[str]:
        exclude = _parse_exclude_patterns(
            self._exclude_text.get("1.0", "end-1c"))

        origen = os.path.realpath(self._origen_var.get().strip())
        destino = os.path.realpath(self._destino_var.get().strip())

        # Si destino está dentro de origen, excluirlo automáticamente
        if destino.startswith(origen + os.sep) or destino == origen:
            rel = os.path.relpath(destino, origen)
            if rel not in exclude:
                exclude.append(rel)

        return exclude

    def _scan_dir(self):
        origen = self._origen_var.get().strip()
        if not origen or not os.path.isdir(origen):
            messagebox.showerror("Error", "El directorio ORIGEN no existe.",
                                 parent=self)
            return

        for item in self._scan_tree.get_children():
            self._scan_tree.delete(item)

        exts = self._get_selected_exts()
        exclude = self._build_exclude_list()

        total = 0
        counts: Dict[str, int] = {}
        sizes: Dict[str, int] = {}

        for dirpath, dirnames, filenames in os.walk(origen):
            rel = os.path.relpath(dirpath, origen)
            if rel != "." and _match_exclude(rel, exclude):
                continue
            for f in filenames:
                if f.startswith("[portada]_"):
                    continue
                if _match_exclude(f, exclude):
                    continue
                ext = os.path.splitext(f)[1].lower()
                for key, vexts in EXTENSIONS.items():
                    if ext in vexts:
                        if key in self._fmt_vars and self._fmt_vars[key].get():
                            counts[key] = counts.get(key, 0) + 1
                            try:
                                fp = os.path.join(dirpath, f)
                                sizes[key] = sizes.get(key, 0) + os.path.getsize(fp)
                            except OSError:
                                pass
                            total += 1
                        break

        self._scan_total = total

        if total == 0:
            self._scan_info.config(text="No se encontraron archivos compatibles.")
            return

        for key in FORMAT_KEYS:
            c = counts.get(key, 0)
            if c > 0:
                self._scan_tree.insert("", "end",
                    values=(key, c, _format_bytes(sizes.get(key, 0))))

        total_size = sum(sizes.values())
        self._scan_tree.insert("", "end",
            values=("TOTAL", total, _format_bytes(total_size)))
        self._scan_info.config(text=f"→ {total} archivo(s) encontrados")
        children = self._scan_tree.get_children()
        if children:
            self._scan_tree.item(children[-1], tags=("bold",))

    # ── extraction ────────────────────────────────────────

    def _start_extraction(self):
        origen = self._origen_var.get().strip()
        destino = self._destino_var.get().strip()
        if not origen or not os.path.isdir(origen):
            messagebox.showerror("Error", "El directorio ORIGEN no existe.",
                                 parent=self)
            return
        if not destino:
            messagebox.showerror("Error",
                                 "Debes indicar un directorio DESTINO.",
                                 parent=self)
            return

        os.makedirs(destino, exist_ok=True)

        if self._scan_total == 0:
            self._scan_dir()
            if self._scan_total == 0:
                return

        args = self._gather_args()
        files = self._collect_files(args)
        if not files:
            return

        self._running = True
        self._cancel_event.clear()
        self._start_btn.configure(state="disabled")
        self._cancel_btn.configure(state="normal")
        self._scan_btn.configure(state="disabled")

        self._log("Iniciando extracción...")
        self.after(0, lambda: self._prog.configure(maximum=len(files)))

        self._executor = ThreadPoolExecutor(max_workers=args["hilos"])

        n_workers = min(args["hilos"], len(files))
        chunk_size = max(1, len(files) // n_workers)
        chunks = [files[i:i + chunk_size] for i in range(0, len(files), chunk_size)]

        futures = []
        for chunk in chunks:
            futures.append(self._executor.submit(self._run_extraction_batch, chunk, args))

        threading.Thread(target=self._monitor_batches,
                         args=(futures,), daemon=True).start()

    def _gather_args(self) -> dict:
        return {
            "origen":   self._origen_var.get().strip(),
            "destino":  self._destino_var.get().strip(),
            "pagina":   self._pagina_var.get(),
            "formato":  self._formato_var.get(),
            "res_modo": self._res_modo.get(),
            "res_valor": self._res_valor.get().strip(),
            "overwrite": OVERWRITE_OPTS.get(self._over_var.get(), "S"),
            "hilos":    self._hilos_var.get(),
            "exts":     self._get_selected_exts(),
            "exclude":  self._build_exclude_list(),
        }

    def _run_extraction_batch(self, files: List[str], args: dict) -> Tuple[int, int, int]:
        processed = errors = skipped = 0
        for fp in files:
            if self._cancel_event.is_set():
                break
            rel = os.path.relpath(fp, args["origen"])
            self.after(0, lambda r=rel: self._current_file.config(text=f"📄 {r}"))
            result = self._process_one(fp, rel, args)
            if result == "ok":
                processed += 1
            elif result == "skip":
                skipped += 1
            else:
                errors += 1
        return processed, errors, skipped

    def _monitor_batches(self, futures):
        processed = errors = skipped = 0
        for future in as_completed(futures):
            p, e, s = future.result()
            processed += p
            errors += e
            skipped += s
            self.after(0, lambda p=processed, e=errors, s=skipped:
                       self._update_progress(p, e, s))
        self.after(0, self._finish)

    def _collect_files(self, args) -> List[str]:
        files = []
        for dirpath, dirnames, filenames in os.walk(args["origen"]):
            rel = os.path.relpath(dirpath, args["origen"])
            if rel != "." and _match_exclude(rel, args["exclude"]):
                continue
            for f in filenames:
                if f.startswith("[portada]_"):
                    continue
                if _match_exclude(f, args["exclude"]):
                    continue
                ext = os.path.splitext(f)[1].lower()
                if ext in args["exts"]:
                    files.append(os.path.join(dirpath, f))
        return files

    def _process_one(self, filepath: str, rel_path: str, args: dict) -> str:
        destino = args["destino"]
        formato = args["formato"]
        overwrite = args["overwrite"]

        name = os.path.splitext(os.path.basename(filepath))[0]
        dir_rel = os.path.dirname(rel_path)
        subdir = os.path.join(destino, dir_rel) if dir_rel != "." else destino
        os.makedirs(subdir, exist_ok=True)

        out = os.path.join(subdir, f"[portada]_{name}.{formato}")

        if os.path.exists(out):
            if overwrite == "S":
                self.after(0, lambda o=out: self._log(f"  ⏭ Saltado: {o}"))
                return "skip"
            elif overwrite == "P":
                with self._overwrite_lock:
                    resp = [False]
                    ev = threading.Event()
                    def ask():
                        resp[0] = messagebox.askyesno(
                            "Sobrescribir",
                            f"¿Sobrescribir?\n{out}",
                            parent=self)
                        ev.set()
                    self.after(0, ask)
                    ev.wait()
                    if not resp[0]:
                        self.after(0, lambda o=out: self._log(f"  ⏭ Saltado: {o}"))
                        return "skip"

        try:
            ext = os.path.splitext(filepath)[1].lower()
            resize = self._resize_str(args)

            ok = False
            if ext == ".pdf":
                ok = self._process_pdf(filepath, out, args["pagina"], resize)
            elif ext in (".mp3", ".m4a", ".aac", ".mp4", ".m4b", ".ogg", ".flac"):
                ok = self._process_audio(filepath, out, resize)
            else:
                ok = self._process_image(filepath, out, ext, formato, resize)

            if ok:
                self.after(0, lambda o=out: self._log(f"  ✓ {o}"))
                return "ok"
            else:
                self.after(0, lambda f=filepath: self._log(f"  ⚠ Error: {f}"))
                return "error"
        except Exception as e:
            self.after(0, lambda e=e: self._log(f"  ⚠ {e}"))
            return "error"

    def _resize_str(self, args: dict) -> Optional[str]:
        return _build_resize_str(args.get("res_modo", ""), args.get("res_valor", ""))

    def _process_pdf(self, src: str, dst: str, page: int,
                     resize: Optional[str]) -> bool:
        return _extract_pdf_cover(src, dst, page, resize)

    def _process_image(self, src: str, dst: str, ext: str,
                       fmt: str, resize: Optional[str]) -> bool:
        return _extract_image_cover(src, dst, ext, fmt, resize)

    def _process_audio(self, src: str, dst: str,
                       resize: Optional[str]) -> bool:
        return _extract_audio_cover(src, dst, resize)

    def _convert_image(self, src: str, dst: str,
                       resize: Optional[str]) -> bool:
        return _convert_image_file(src, dst, resize)

    def _save_image(self, img, dst: str, resize: Optional[str]) -> bool:
        return _save_image_file(img, dst, resize)

    @staticmethod
    def _parse_resize_str(s: str, w: int, h: int) -> Optional[Tuple[int, int]]:
        return _parse_resize_str(s, w, h)

    def _update_progress(self, processed, errors, skipped):
        done = processed + errors + skipped
        self._prog["value"] = done
        self._counters.config(
            text=f"✓ {processed}  ⚠ {errors}  ⏭ {skipped}")

    def _finish(self):
        self._running = False
        self._start_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        self._scan_btn.configure(state="normal")
        self._current_file.config(text="")
        self._log("Extracción finalizada.")
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    def _cancel(self):
        self._cancel_event.set()
        self._cancel_btn.configure(state="disabled")
        self._log("Cancelando... (esperando trabajos en curso)")


class SinglePortadaExtractDialog(tk.Toplevel):
    def __init__(self, parent, item, library_root, portadas_root,
                 web_root, on_done=None):
        super().__init__(parent)
        self.parent = parent
        self._item = item
        self._library_root = library_root
        self._portadas_root = portadas_root
        self._web_root = web_root
        self._on_done = on_done
        self.title("Extraer portada")
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)
        self.minsize(520, 380)

        pw = max(parent.winfo_width(), 520)
        ph = max(parent.winfo_height(), 400)
        px = parent.winfo_x()
        py = parent.winfo_rooty()
        dw = min(650, max(520, pw - 80))
        dh = min(450, max(380, ph - 120))
        x = max(0, px + (pw - dw) // 2)
        y = max(0, py + 40)
        self.geometry(f"{dw}x{dh}+{x}+{y}")

        self._cancel_event = threading.Event()
        self._running = False

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── build ─────────────────────────────────────────────

    def _build(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        main = ttk.Frame(self, padding=10)
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_rowconfigure(4, weight=1)
        main.grid_columnconfigure(1, weight=1)

        pad = {"padx": 4, "pady": 2}

        # Source path (read-only)
        ttk.Label(main, text="Archivo origen:", font=("", 9, "bold")).grid(
            row=0, column=0, sticky="w", **pad)
        source_path = (
            str(Path(self._library_root) / self._item.destino / self._item.nombre_legible)
            if self._library_root and self._item.destino and self._item.nombre_legible else "")
        self._origen_var = tk.StringVar(value=source_path)
        ttk.Entry(main, textvariable=self._origen_var, state="readonly").grid(
            row=0, column=1, sticky="ew", **pad)

        # Dest directory (read-only)
        ttk.Label(main, text="Directorio destino:", font=("", 9, "bold")).grid(
            row=1, column=0, sticky="w", **pad)
        dest_dir = (str(Path(self._portadas_root) / self._item.destino)
                    if self._portadas_root and self._item.destino else "")
        self._destino_var = tk.StringVar(value=dest_dir)
        ttk.Entry(main, textvariable=self._destino_var, state="readonly").grid(
            row=1, column=1, sticky="ew", **pad)

        # Output filename preview
        stem = Path(self._item.nombre_legible).stem if self._item.nombre_legible else "output"
        self._log_output = f"[portada]_{stem}"
        ttk.Label(main, text="Archivo salida:", font=("", 9, "bold")).grid(
            row=2, column=0, sticky="w", **pad)
        self._out_label = ttk.Label(main, text=f"{self._log_output}.{{formato}}")
        self._out_label.grid(row=2, column=1, sticky="w", **pad)

        # Options row
        opt_frame = ttk.Frame(main)
        opt_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        opt_frame.grid_columnconfigure(3, weight=1)

        ttk.Label(opt_frame, text="Página:", font=("", 9, "bold")).grid(
            row=0, column=0, sticky="w", **pad)
        self._pagina_var = tk.IntVar(value=1)
        ttk.Spinbox(opt_frame, from_=1, to=999,
                    textvariable=self._pagina_var, width=6).grid(
            row=0, column=1, sticky="w", **pad)

        ttk.Label(opt_frame, text="Formato:", font=("", 9, "bold")).grid(
            row=0, column=2, sticky="w", padx=(16, 4), pady=2)
        self._formato_var = tk.StringVar(value="jpg")
        self._formato_combo = ttk.Combobox(
            opt_frame, textvariable=self._formato_var,
            values=FORMATOS_SALIDA, state="readonly", width=8)
        self._formato_combo.grid(row=0, column=3, sticky="w", **pad)
        self._formato_combo.bind("<<ComboboxSelected>>", self._update_out_label)

        ttk.Label(opt_frame, text="Resolución:", font=("", 9, "bold")).grid(
            row=1, column=0, sticky="w", **pad)
        res_frame = ttk.Frame(opt_frame)
        res_frame.grid(row=1, column=1, columnspan=3, sticky="w", **pad)
        self._res_modo = tk.StringVar(value="alto")
        self._res_valor = tk.StringVar(value="300")

        for lbl, mode in [("Original", "original"), ("%", "pct"),
                          ("Ancho", "ancho"), ("Alto", "alto")]:
            ttk.Radiobutton(res_frame, text=lbl,
                            variable=self._res_modo, value=mode).pack(
                side="left", padx=(0, 4))
        ttk.Label(res_frame, text="  Valor:").pack(side="left", padx=(6, 2))
        ttk.Entry(res_frame, textvariable=self._res_valor, width=6).pack(side="left")

        # Log area
        log_frame = ttk.LabelFrame(main, text="Log", padding=2)
        log_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        self._log_text = tk.Text(log_frame, height=5, state="disabled", wrap="word")
        lsc = ttk.Scrollbar(log_frame, orient="vertical",
                            command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=lsc.set)
        self._log_text.grid(row=0, column=0, sticky="nsew")
        lsc.grid(row=0, column=1, sticky="ns")

        # Buttons
        btn_row = ttk.Frame(main)
        btn_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self._extract_btn = ttk.Button(btn_row, text="Extraer",
                                       command=self._start_extraction)
        self._extract_btn.pack(side="left", padx=(0, 4))
        self._cancel_btn = ttk.Button(btn_row, text="Cancelar",
                                      command=self._cancel, state="disabled")
        self._cancel_btn.pack(side="left", padx=(0, 4))
        ttk.Button(btn_row, text="Cerrar", command=self._on_close).pack(
            side="right")

    def _update_out_label(self, event=None):
        fmt = self._formato_var.get()
        self._out_label.config(text=f"{self._log_output}.{fmt}")

    # ── helpers ───────────────────────────────────────────

    def _log(self, msg: str):
        self._log_text.configure(state="normal")
        self._log_text.insert("end", msg + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _on_close(self):
        if self._running:
            if not messagebox.askyesno("Cancelar",
                    "Hay una extracción en curso. ¿Cancelar y cerrar?",
                    parent=self):
                return
            self._cancel()
        self.parent.focus_set()
        self.destroy()

    # ── extraction ────────────────────────────────────────

    def _start_extraction(self):
        source = self._origen_var.get().strip()
        if not source or not os.path.isfile(source):
            messagebox.showerror("Error", "El archivo origen no existe.",
                                 parent=self)
            return

        dest_dir = self._destino_var.get().strip()
        if not dest_dir:
            messagebox.showerror("Error",
                                 "El directorio destino no está configurado.",
                                 parent=self)
            return

        os.makedirs(dest_dir, exist_ok=True)

        formato = self._formato_var.get()
        stem = Path(self._item.nombre_legible).stem if self._item.nombre_legible else "output"
        out_path = os.path.join(dest_dir, f"[portada]_{stem}.{formato}")

        self._running = True
        self._cancel_event.clear()
        self._extract_btn.configure(state="disabled")
        self._cancel_btn.configure(state="normal")

        self._log(f"Extrayendo portada de:\n  {source}")
        self._log(f"Destino: {out_path}")

        threading.Thread(target=self._extract_thread,
                         args=(source, out_path), daemon=True).start()

    def _extract_thread(self, src: str, dst: str):
        if self._cancel_event.is_set():
            self.after(0, self._finish)
            return

        ext = os.path.splitext(src)[1].lower()
        resize = _build_resize_str(self._res_modo.get(),
                                   self._res_valor.get().strip())
        page = self._pagina_var.get()
        fmt = self._formato_var.get()

        if ext == ".pdf":
            ok = _extract_pdf_cover(src, dst, page, resize)
        elif ext in (".mp3", ".m4a", ".aac", ".mp4", ".m4b", ".ogg", ".flac"):
            ok = _extract_audio_cover(src, dst, resize)
        else:
            ok = _extract_image_cover(src, dst, ext, fmt, resize)

        if ok:
            self.after(0, lambda: self._log("✓ Portada extraída correctamente"))
        else:
            self.after(0, lambda: self._log("⚠ Error al extraer portada"))

        self.after(0, lambda: self._on_extract_done(ok, dst))

    def _on_extract_done(self, success: bool, out_path: str):
        if success:
            rel = (os.path.relpath(out_path, self._web_root)
                   if self._web_root else Path(out_path).name)
            if self._on_done:
                self._on_done(self._item, rel)
        self._finish()

    def _finish(self):
        self._running = False
        self._extract_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")

    def _cancel(self):
        self._cancel_event.set()
        self._cancel_btn.configure(state="disabled")
        self._log("Cancelando...")
