import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox


class PathSetupDialog:
    LABELS = {
        "nombre_biblioteca": "Nombre de la biblioteca:",
        "library_root": "Ruta biblioteca (PDFs):",
        "portadas_root": "Ruta portadas (imágenes):",
        "web_root": "Ruta web (index.html):",
        "catalogo_js_path": "Ruta de catalogo.js:",
    }

    def _auto_fill_catalogo_js(self, *_):
        web = self.entries["web_root"].get().strip()
        if web:
            js = str(Path(web) / "data" / "catalogo.js")
            self.entries["catalogo_js_path"].delete(0, "end")
            self.entries["catalogo_js_path"].insert(0, js)

    def __init__(self, parent, title="Configurar rutas",
                 required=("library_root", "portadas_root", "web_root")):
        self.result = None
        self.required = required
        self.entries = {}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        self._build()

        parent.wait_window(self.dialog)

    def _build(self):
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Configura los datos de la nueva biblioteca:",
                  font=("", 11)).pack(anchor="w", pady=(0, 14))

        # nombre_biblioteca first (as plain text entry, no browse)
        name_row = ttk.Frame(frame)
        name_row.pack(fill="x", pady=5)
        ttk.Label(name_row, text=self.LABELS["nombre_biblioteca"],
                  width=30, anchor="w").pack(side="left")
        self._nombre_var = tk.StringVar(value="")
        name_entry = ttk.Entry(name_row, textvariable=self._nombre_var)
        name_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        self.entries["nombre_biblioteca"] = name_entry

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        for key in ("library_root", "portadas_root", "web_root"):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=5)

            label = self.LABELS.get(key, key)
            ttk.Label(row, text=label, width=30, anchor="w").pack(side="left")

            entry = ttk.Entry(row)
            entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
            self.entries[key] = entry

            btn = ttk.Button(row, text="Examinar...",
                             command=lambda k=key: self._browse(k))
            btn.pack(side="right")

        # ── catalogo_js_path (auto‑completado desde web_root) ──
        js_row = ttk.Frame(frame)
        js_row.pack(fill="x", pady=5)
        ttk.Label(js_row, text=self.LABELS["catalogo_js_path"],
                  width=30, anchor="w").pack(side="left")
        js_entry = ttk.Entry(js_row)
        js_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        self.entries["catalogo_js_path"] = js_entry

        # trace web_root → catalogo_js_path
        self._web_root_after_id = None
        self._web_root_var = tk.StringVar()
        self.entries["web_root"].config(textvariable=self._web_root_var)
        self._web_root_var.trace_add("write", self._on_web_root_changed)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=14)

        btn_row = ttk.Frame(frame)
        btn_row.pack()
        ttk.Button(btn_row, text="Confirmar", command=self._confirm).pack(
            side="left", padx=6)
        ttk.Button(btn_row, text="Cancelar", command=self._cancel).pack(
            side="left", padx=6)

        self.dialog.update_idletasks()
        pw = self.dialog.master.winfo_width()
        ph = self.dialog.master.winfo_height()
        wx = self.dialog.master.winfo_x()
        wy = self.dialog.master.winfo_rooty()
        dw = self.dialog.winfo_reqwidth()
        dh = self.dialog.winfo_reqheight()
        # add a bit of extra width so it doesn't feel cramped
        self.dialog.geometry(
            f"{max(dw, 560)}x{dh}+{wx + (pw - max(dw, 560)) // 2}+{wy + (ph - dh) // 2}")

    def _on_web_root_changed(self, *_):
        if self._web_root_after_id:
            self.dialog.after_cancel(self._web_root_after_id)
        self._web_root_after_id = self.dialog.after(200, self._auto_fill_catalogo_js)

    def _browse(self, key: str):
        path = filedialog.askdirectory(title="Seleccionar directorio",
                                        mustexist=False)
        if path:
            self.entries[key].delete(0, "end")
            self.entries[key].insert(0, path)

    def _confirm(self):
        paths = {}
        for key, entry in self.entries.items():
            val = entry.get().strip()
            if key in self.required and not val:
                messagebox.showwarning(
                    "Campo requerido",
                    f"'{self.LABELS.get(key, key)}' es obligatorio.",
                    parent=self.dialog,
                )
                entry.focus_set()
                return
            paths[key] = val

        missing = [self.LABELS.get(k, k) for k in self.required
                   if k not in ("nombre_biblioteca", "catalogo_js_path")
                   and paths.get(k) and not Path(paths[k]).exists()]
        if missing:
            if not messagebox.askyesno(
                "Rutas no encontradas",
                "Las siguientes rutas no existen:\n\n"
                + "\n".join(missing)
                + "\n\n¿Continuar de todas formas?",
                parent=self.dialog,
            ):
                return

        self.result = paths
        self.dialog.destroy()

    def _cancel(self):
        self.dialog.destroy()
