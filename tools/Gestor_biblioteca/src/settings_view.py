import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from tkinter import ttk


CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"

DEFAULT_CONFIG = {
    "library_root": "",
    "portadas_root": "",
    "web_root": "",
    "last_json": "",
    "catalogo_js_path": "",
    "scan_exclude": ["./Portadas", "./99 - No Clasificados", "*.json", "*.js"],
    "backup_count": 2,
    "mover_items_fisicamente": True,
    "upload_portada_comportamiento": "copiar",
    "upload_documento_comportamiento": "copiar",
    "theme": "default",
    "nombre_biblioteca": "",
    "recent_libraries": [],
    "export_formato_default": "json",
    "export_incluir_portadas": False,
    "export_incluir_pdfs": False,
    "import_comportamiento_default": "saltar",
    "import_carpeta_default": "Importados",
    "import_modo_destino_default": "estructura",
    "delete_defaults": {
        "item": {"borrar_pdf": False, "borrar_portada": False},
        "dir": {
            "accion_fichas": "subir",
            "accion_pdfs": "mover",
            "accion_portadas": "mover",
            "accion_subdirectorios": "heredar",
            "accion_mantenidos": "mover_a_raiz",
        },
    },
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


class SettingsView(ttk.Frame):
    def __init__(self, parent, on_config_saved=None):
        super().__init__(parent)
        self.on_config_saved = on_config_saved
        self.config_data = load_config()
        self._build()

    def _build(self):
        canvas = tk.Canvas(self, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable = ttk.Frame(canvas)

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._canvas_window = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self._canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._build_content(scrollable)

        _bind_mousewheel(canvas, scrollable)

    def _build_content(self, parent):
        pad = {"padx": 10, "pady": 5}

        ttk.Label(parent, text="Configuración", font=("", 14, "bold")).pack(
            anchor="w", padx=10, pady=(15, 10)
        )

        # ── Nombre de la biblioteca ──
        name_frame = ttk.Frame(parent)
        name_frame.pack(fill="x", **pad)
        ttk.Label(name_frame, text="Nombre de la biblioteca:", width=30, anchor="w").pack(side="left")
        self._nombre_var = tk.StringVar(value="")
        name_entry = ttk.Entry(name_frame, textvariable=self._nombre_var)
        name_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))

        ttk.Separator(parent, orient="horizontal").pack(fill="x", **pad)

        ttk.Label(parent, text="Rutas", font=("", 12, "bold")).pack(
            anchor="w", padx=10, pady=(5, 10)
        )

        fields = [
            ("library_root", "Ruta biblioteca (PDFs):"),
            ("portadas_root", "Ruta portadas (imágenes):"),
            ("web_root", "Ruta web (index.html):"),
        ]

        self.entries = {}
        for key, label in fields:
            frame = ttk.Frame(parent)
            frame.pack(fill="x", **pad)

            ttk.Label(frame, text=label, width=30, anchor="w").pack(side="left")

            entry = ttk.Entry(frame)
            entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
            self.entries[key] = entry

            btn = ttk.Button(frame, text="Examinar...", command=lambda k=key: self._browse(k))
            btn.pack(side="right")

        # ── Ruta catalogo.js ──
        js_frame = ttk.Frame(parent)
        js_frame.pack(fill="x", **pad)

        ttk.Label(js_frame, text="Ruta de catalogo.js:", width=30, anchor="w").pack(side="left")

        self.js_path_var = tk.StringVar(value="")
        js_entry = ttk.Entry(js_frame, textvariable=self.js_path_var)
        js_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        ttk.Button(
            js_frame,
            text="Examinar...",
            command=self._browse_js_path,
        ).pack(side="right")

        self._build_exclude_section(parent)
        self._build_backup_section(parent)
        self._build_drag_section(parent)
        self._build_theme_section(parent)
        self._build_import_export_section(parent)
        self._build_delete_section(parent)

        ttk.Separator(parent, orient="horizontal").pack(fill="x", **pad)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(**pad)

        ttk.Button(btn_frame, text="Guardar configuración", command=self._save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Restablecer valores", command=self._reset).pack(side="left", padx=5)

        self.status_label = ttk.Label(parent, text="")
        self.status_label.pack(**pad)

    def _build_exclude_section(self, parent):
        pad = {"padx": 10, "pady": 5}

        exclude_frame = ttk.LabelFrame(parent, text="Ignorar en las búsquedas", padding=10)
        exclude_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(
            exclude_frame,
            text="Archivos o directorios a ignorar al buscar cambios (uno por línea):",
        ).pack(anchor="w")

        text_frame = ttk.Frame(exclude_frame)
        text_frame.pack(fill="x", pady=5)

        self.exclude_text = tk.Text(text_frame, height=5, width=50)
        self.exclude_text.pack(side="left", fill="x", expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.exclude_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.exclude_text.configure(yscrollcommand=scrollbar.set)

        exclude_list = self.config_data.get("scan_exclude", DEFAULT_CONFIG.get("scan_exclude", []))
        self.exclude_text.insert("1.0", "\n".join(exclude_list))

    def _build_backup_section(self, parent):
        pad = {"padx": 10, "pady": 5}

        backup_frame = ttk.LabelFrame(parent, text="Copias de seguridad", padding=10)
        backup_frame.pack(fill="x", padx=10, pady=5)

        row = ttk.Frame(backup_frame)
        row.pack(fill="x")

        ttk.Label(row, text="Número de copias a mantener al abrir un JSON:").pack(side="left")
        self.backup_spin = ttk.Spinbox(row, from_=0, to=99, width=5)
        self.backup_spin.pack(side="left", padx=(8, 0))
        self.backup_spin.set(self.config_data.get("backup_count", DEFAULT_CONFIG["backup_count"]))

        ttk.Label(
            backup_frame,
            text="0 = deshabilitar copias automáticas",
            font=("", 9),
            foreground="gray",
        ).pack(anchor="w", pady=(4, 0))

    def _build_drag_section(self, parent):
        pad = {"padx": 10, "pady": 5}
        drag_frame = ttk.LabelFrame(parent, text="Comportamiento", padding=10)
        drag_frame.pack(fill="x", padx=10, pady=5)

        self._mover_var = tk.BooleanVar(
            value=self.config_data.get("mover_items_fisicamente", True)
        )
        ttk.Checkbutton(
            drag_frame,
            text="Mover físicamente los archivos al cambiar de directorio",
            variable=self._mover_var,
        ).pack(anchor="w")
        ttk.Label(
            drag_frame,
            text="Si está activado, al arrastrar un item a otro directorio los archivos PDF y\n"
                 "portadas se mueven en disco. Si no, solo se actualiza el catálogo.",
            font=("", 9),
            foreground="gray",
        ).pack(anchor="w", pady=(4, 0))

        ttk.Separator(drag_frame, orient="horizontal").pack(fill="x", pady=8)

        ttk.Label(drag_frame, text="Al subir archivos", font=("", 10, "bold")).pack(anchor="w")

        row_p = ttk.Frame(drag_frame)
        row_p.pack(fill="x", pady=(5, 2))
        ttk.Label(row_p, text="Portadas:", width=25, anchor="w").pack(side="left")
        self._up_portada_var = tk.StringVar(
            value=self.config_data.get("upload_portada_comportamiento", "copiar")
        )
        ttk.Combobox(
            row_p, textvariable=self._up_portada_var,
            values=["copiar", "mover"], state="readonly", width=12,
        ).pack(side="left")

        row_d = ttk.Frame(drag_frame)
        row_d.pack(fill="x", pady=2)
        ttk.Label(row_d, text="Documentos:", width=25, anchor="w").pack(side="left")
        self._up_documento_var = tk.StringVar(
            value=self.config_data.get("upload_documento_comportamiento", "copiar")
        )
        ttk.Combobox(
            row_d, textvariable=self._up_documento_var,
            values=["copiar", "mover"], state="readonly", width=12,
        ).pack(side="left")

    def _build_theme_section(self, parent):
        theme_frame = ttk.LabelFrame(parent, text="Apariencia", padding=10)
        theme_frame.pack(fill="x", padx=10, pady=5)

        row = ttk.Frame(theme_frame)
        row.pack(fill="x")

        ttk.Label(row, text="Tema de la interfaz:").pack(side="left")

        style = ttk.Style()
        native = list(style.theme_names())
        sv_themes = ["sv-light", "sv-dark"]
        all_themes = sv_themes + [t for t in native if t not in sv_themes]
        self._theme_var = tk.StringVar(
            value=self.config_data.get("theme", DEFAULT_CONFIG["theme"])
        )
        theme_combo = ttk.Combobox(
            row,
            textvariable=self._theme_var,
            values=all_themes,
            state="readonly",
            width=20,
        )
        theme_combo.pack(side="left", padx=(8, 0))

        self._theme_preview = ttk.Label(
            theme_frame,
            text="",
            font=("", 9),
            foreground="gray",
        )
        self._theme_preview.pack(anchor="w", pady=(4, 0))
        self._update_theme_preview()

        theme_combo.bind("<<ComboboxSelected>>", self._on_theme_selected)

    def _on_theme_selected(self, event=None):
        self._update_theme_preview()

    def _update_theme_preview(self):
        theme = self._theme_var.get()
        descs = {
            "sv-light": "Tema moderno Sun Valley (modo claro)",
            "sv-dark": "Tema moderno Sun Valley (modo oscuro)",
            "clam": "Moderna y consistente entre plataformas",
            "alt": "Similar a clam, con variaciones sutiles",
            "default": "Tema nativo del sistema",
            "classic": "Estilo clásico de Tk (relieves 3D)",
        }
        desc = descs.get(theme, "")
        if desc:
            self._theme_preview.config(text=desc)
        else:
            self._theme_preview.config(text="")

    def _build_import_export_section(self, parent):
        pad = {"padx": 10, "pady": 5}
        frame = ttk.LabelFrame(parent, text="Importar / Exportar", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame, text="Exportación", font=("", 10, "bold")).pack(anchor="w")

        row1 = ttk.Frame(frame)
        row1.pack(fill="x", pady=(5, 2))
        ttk.Label(row1, text="Formato por defecto:", width=25, anchor="w").pack(side="left")
        self._export_formato_var = tk.StringVar(
            value=self.config_data.get("export_formato_default", DEFAULT_CONFIG["export_formato_default"])
        )
        ttk.Combobox(
            row1,
            textvariable=self._export_formato_var,
            values=["json", "zip"],
            state="readonly",
            width=12,
        ).pack(side="left")

        row2 = ttk.Frame(frame)
        row2.pack(fill="x", pady=2)
        self._export_portadas_var = tk.BooleanVar(
            value=self.config_data.get("export_incluir_portadas", DEFAULT_CONFIG["export_incluir_portadas"])
        )
        ttk.Checkbutton(
            row2, text="Incluir portadas por defecto",
            variable=self._export_portadas_var,
        ).pack(anchor="w", padx=(25, 0))

        row3 = ttk.Frame(frame)
        row3.pack(fill="x", pady=2)
        self._export_pdfs_var = tk.BooleanVar(
            value=self.config_data.get("export_incluir_pdfs", DEFAULT_CONFIG["export_incluir_pdfs"])
        )
        ttk.Checkbutton(
            row3, text="Incluir PDFs por defecto",
            variable=self._export_pdfs_var,
        ).pack(anchor="w", padx=(25, 0))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=8)

        ttk.Label(frame, text="Importación", font=("", 10, "bold")).pack(anchor="w")

        row4 = ttk.Frame(frame)
        row4.pack(fill="x", pady=(5, 2))
        ttk.Label(row4, text="Comportamiento con duplicados:", width=25, anchor="w").pack(side="left")
        self._import_dup_var = tk.StringVar(
            value=self.config_data.get("import_comportamiento_default", DEFAULT_CONFIG["import_comportamiento_default"])
        )
        ttk.Combobox(
            row4,
            textvariable=self._import_dup_var,
            values=["saltar", "sobrescribir", "importar_todos"],
            state="readonly",
            width=15,
        ).pack(side="left")

        row5 = ttk.Frame(frame)
        row5.pack(fill="x", pady=2)
        ttk.Label(row5, text="Modo destino:", width=25, anchor="w").pack(side="left")
        self._import_modo_var = tk.StringVar(
            value=self.config_data.get("import_modo_destino_default", DEFAULT_CONFIG["import_modo_destino_default"])
        )
        ttk.Combobox(
            row5,
            textvariable=self._import_modo_var,
            values=["estructura", "carpeta_fija"],
            state="readonly",
            width=15,
        ).pack(side="left")

        row6 = ttk.Frame(frame)
        row6.pack(fill="x", pady=2)
        ttk.Label(row6, text="Carpeta por defecto:", width=25, anchor="w").pack(side="left")
        self._import_carpeta_var = tk.StringVar(
            value=self.config_data.get("import_carpeta_default", DEFAULT_CONFIG["import_carpeta_default"])
        )
        ttk.Entry(row6, textvariable=self._import_carpeta_var, width=20).pack(side="left")

    def _build_delete_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Eliminación", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        delete_defaults = self.config_data.get("delete_defaults", DEFAULT_CONFIG["delete_defaults"])

        ttk.Label(frame, text="Al eliminar una ficha", font=("", 10, "bold")).pack(anchor="w")
        item_def = delete_defaults.get("item", {})
        self._del_item_pdf_var = tk.BooleanVar(
            value=item_def.get("borrar_pdf", False)
        )
        self._del_item_portada_var = tk.BooleanVar(
            value=item_def.get("borrar_portada", False)
        )
        ttk.Checkbutton(
            frame, text="Borrar PDF por defecto",
            variable=self._del_item_pdf_var,
        ).pack(anchor="w", padx=(15, 0), pady=2)
        ttk.Checkbutton(
            frame, text="Borrar portada por defecto",
            variable=self._del_item_portada_var,
        ).pack(anchor="w", padx=(15, 0), pady=2)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=8)

        ttk.Label(frame, text="Al eliminar un directorio", font=("", 10, "bold")).pack(anchor="w")
        dir_def = delete_defaults.get("dir", {})

        sub = ttk.Frame(frame)
        sub.pack(fill="x", padx=(15, 0), pady=4)
        ttk.Label(sub, text="Fichas:", width=14, anchor="w").pack(side="left")
        self._del_dir_fichas_var = tk.StringVar(
            value=dir_def.get("accion_fichas", "subir")
        )
        ttk.Combobox(
            sub, textvariable=self._del_dir_fichas_var,
            values=["subir", "eliminar"], state="readonly", width=14,
        ).pack(side="left")

        sub2 = ttk.Frame(frame)
        sub2.pack(fill="x", padx=(15, 0), pady=4)
        ttk.Label(sub2, text="PDFs:", width=14, anchor="w").pack(side="left")
        self._del_dir_pdfs_var = tk.StringVar(
            value=dir_def.get("accion_pdfs", "mover")
        )
        ttk.Combobox(
            sub2, textvariable=self._del_dir_pdfs_var,
            values=["mover", "borrar", "mantener"], state="readonly", width=14,
        ).pack(side="left")

        sub3 = ttk.Frame(frame)
        sub3.pack(fill="x", padx=(15, 0), pady=4)
        ttk.Label(sub3, text="Portadas:", width=14, anchor="w").pack(side="left")
        self._del_dir_portadas_var = tk.StringVar(
            value=dir_def.get("accion_portadas", "mover")
        )
        ttk.Combobox(
            sub3, textvariable=self._del_dir_portadas_var,
            values=["mover", "borrar", "mantener"], state="readonly", width=14,
        ).pack(side="left")

        sub4 = ttk.Frame(frame)
        sub4.pack(fill="x", padx=(15, 0), pady=4)
        ttk.Label(sub4, text="Subdirectorios:", width=14, anchor="w").pack(side="left")
        self._del_dir_subdirs_var = tk.StringVar(
            value=dir_def.get("accion_subdirectorios", "heredar")
        )
        ttk.Combobox(
            sub4, textvariable=self._del_dir_subdirs_var,
            values=["heredar", "eliminar_todo", "solo_limpiar", "mantener_intactos"],
            state="readonly", width=18,
        ).pack(side="left")

        sub5 = ttk.Frame(frame)
        sub5.pack(fill="x", padx=(15, 0), pady=4)
        ttk.Label(sub5, text="Mantenidos:", width=14, anchor="w").pack(side="left")
        self._del_dir_mant_var = tk.StringVar(
            value=dir_def.get("accion_mantenidos", "mover_a_raiz")
        )
        ttk.Combobox(
            sub5, textvariable=self._del_dir_mant_var,
            values=["mover_a_raiz", "no_borrar"], state="readonly", width=14,
        ).pack(side="left")

    def _browse_js_path(self):
        path = filedialog.asksaveasfilename(
            title="Seleccionar ruta de catalogo.js",
            defaultextension=".js",
            filetypes=[("JavaScript", "*.js")],
        )
        if path:
            self.js_path_var.set(path)
            config = {**self.config_data, "catalogo_js_path": path}
            save_config(config)
            self.config_data = config

    def _browse(self, key: str):
        path = filedialog.askdirectory(title="Seleccionar directorio")
        if path:
            self.entries[key].delete(0, "end")
            self.entries[key].insert(0, path)

    def _save(self):
        config = {}
        for key, entry in self.entries.items():
            config[key] = entry.get().strip()
        config["nombre_biblioteca"] = self._nombre_var.get().strip()
        config["catalogo_js_path"] = self.js_path_var.get().strip()

        exclude_text = self.exclude_text.get("1.0", "end-1c").strip()
        config["scan_exclude"] = [line.strip() for line in exclude_text.split("\n") if line.strip()]

        try:
            config["backup_count"] = int(self.backup_spin.get())
        except ValueError:
            config["backup_count"] = DEFAULT_CONFIG["backup_count"]
        config["mover_items_fisicamente"] = self._mover_var.get()
        config["upload_portada_comportamiento"] = self._up_portada_var.get()
        config["upload_documento_comportamiento"] = self._up_documento_var.get()
        config["theme"] = self._theme_var.get()
        config["export_formato_default"] = self._export_formato_var.get()
        config["export_incluir_portadas"] = self._export_portadas_var.get()
        config["export_incluir_pdfs"] = self._export_pdfs_var.get()
        config["import_comportamiento_default"] = self._import_dup_var.get()
        config["import_modo_destino_default"] = self._import_modo_var.get()
        config["import_carpeta_default"] = self._import_carpeta_var.get().strip() or "Importados"

        config["delete_defaults"] = {
            "item": {
                "borrar_pdf": self._del_item_pdf_var.get(),
                "borrar_portada": self._del_item_portada_var.get(),
            },
            "dir": {
                "accion_fichas": self._del_dir_fichas_var.get(),
                "accion_pdfs": self._del_dir_pdfs_var.get(),
                "accion_portadas": self._del_dir_portadas_var.get(),
                "accion_subdirectorios": self._del_dir_subdirs_var.get(),
                "accion_mantenidos": self._del_dir_mant_var.get(),
            },
        }

        missing = []
        for key, label in [("library_root", "Ruta biblioteca"), ("portadas_root", "Ruta portadas"), ("web_root", "Ruta web")]:
            if config.get(key) and not Path(config[key]).exists():
                missing.append(label)

        if missing:
            if not messagebox.askyesno(
                "Rutas no encontradas",
                f"Las siguientes rutas no existen:\n\n" + "\n".join(missing) + "\n\n¿Guardar de todas formas?",
            ):
                return

        save_config(config)
        self.config_data = config
        self.status_label.config(text="Configuración guardada.", foreground="green")

        if self.on_config_saved:
            self.on_config_saved(config)

    def _reset(self):
        for key, entry in self.entries.items():
            entry.delete(0, "end")
            entry.insert(0, "")
        self._nombre_var.set("")
        self.js_path_var.set("")
        self.exclude_text.delete("1.0", "end")
        defaults = DEFAULT_CONFIG.get("scan_exclude", [])
        self.exclude_text.insert("1.0", "\n".join(defaults))
        self.backup_spin.set(DEFAULT_CONFIG["backup_count"])
        self._mover_var.set(DEFAULT_CONFIG.get("mover_items_fisicamente", True))
        self._up_portada_var.set(DEFAULT_CONFIG["upload_portada_comportamiento"])
        self._up_documento_var.set(DEFAULT_CONFIG["upload_documento_comportamiento"])
        self._theme_var.set(DEFAULT_CONFIG["theme"])
        self._update_theme_preview()
        self._export_formato_var.set(DEFAULT_CONFIG["export_formato_default"])
        self._export_portadas_var.set(DEFAULT_CONFIG["export_incluir_portadas"])
        self._export_pdfs_var.set(DEFAULT_CONFIG["export_incluir_pdfs"])
        self._import_dup_var.set(DEFAULT_CONFIG["import_comportamiento_default"])
        self._import_modo_var.set(DEFAULT_CONFIG["import_modo_destino_default"])
        self._import_carpeta_var.set(DEFAULT_CONFIG["import_carpeta_default"])

        dd = DEFAULT_CONFIG["delete_defaults"]
        self._del_item_pdf_var.set(dd["item"]["borrar_pdf"])
        self._del_item_portada_var.set(dd["item"]["borrar_portada"])
        self._del_dir_fichas_var.set(dd["dir"]["accion_fichas"])
        self._del_dir_pdfs_var.set(dd["dir"]["accion_pdfs"])
        self._del_dir_portadas_var.set(dd["dir"]["accion_portadas"])
        self._del_dir_subdirs_var.set(dd["dir"]["accion_subdirectorios"])
        self._del_dir_mant_var.set(dd["dir"]["accion_mantenidos"])

        self.status_label.config(text="")

    def set_fields_from_config(self, config: dict):
        for key, entry in self.entries.items():
            val = config.get(key, "")
            entry.delete(0, "end")
            if val:
                entry.insert(0, val)
        self._nombre_var.set(config.get("nombre_biblioteca", ""))
        self.js_path_var.set(config.get("catalogo_js_path", ""))

    def get_config(self) -> dict:
        config = {}
        for key, entry in self.entries.items():
            val = entry.get().strip()
            if val:
                config[key] = val
            else:
                config[key] = self.config_data.get(key, "")
        config["nombre_biblioteca"] = self._nombre_var.get().strip() or self.config_data.get("nombre_biblioteca", "")
        config["catalogo_js_path"] = self.js_path_var.get().strip() or self.config_data.get("catalogo_js_path", "")
        return config


def _bind_mousewheel(canvas, scrollable):
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    def _on_linux_scroll(event):
        canvas.yview_scroll(-1 if event.num == 4 else 1, "units")

    canvas.bind("<MouseWheel>", _on_mousewheel)
    canvas.bind("<Button-4>", _on_linux_scroll, add="+")
    canvas.bind("<Button-5>", _on_linux_scroll, add="+")

    def _bind_recursive(w):
        w.bind("<MouseWheel>", _on_mousewheel, add="+")
        w.bind("<Button-4>", _on_linux_scroll, add="+")
        w.bind("<Button-5>", _on_linux_scroll, add="+")
        for child in w.winfo_children():
            _bind_recursive(child)

    _bind_recursive(scrollable)
