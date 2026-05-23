import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from io import BytesIO
from pathlib import Path
from typing import Callable, List, Optional

from ..models import Item
from ..portada_mgr import upload as upload_portada, find_existing
from ..portadas_extract_dialog import SinglePortadaExtractDialog
from ..utils.tooltip import ToolTip, make_btn as _icon_btn


_BATCH_FIELDS = [
    ("tipo", "Tipo", "combo",
     ["manual", "suplemento", "campaña", "aventura", "revista",
      "documento", "info", "imagen", "mapa", "hoja_pj", "pantalla",
      "musica", "otro"]),
    ("edicion", "Edición", "combo",
     ["1ª", "2ª", "3ª", "4ª", "indeterminada"]),
    ("confianza", "Confianza", "combo",
     ["alta", "media", "baja"]),
    ("escaneado", "Escaneado", "check", None),
    ("oculto", "Mostrar en web", "check", None),
]


try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


class DetailView(ttk.Frame):
    def __init__(self, parent, on_item_changed: Callable[[Item], None] = None):
        super().__init__(parent)
        self.on_item_changed = on_item_changed
        self._item: Optional[Item] = None
        self._batch_items: List[Item] = []
        self._dir_name: Optional[str] = None
        self._dirty = False
        self._loading = False
        self._web_root: str = ""
        self._portadas_root: str = ""
        self._library_root: str = ""
        self._on_dir_rename: Optional[Callable[[str, str], None]] = None
        self._on_dir_delete: Optional[Callable[[str], None]] = None

        self._build()
        self._build_batch()
        self._build_directory()

    def set_web_root(self, path: str):
        self._web_root = path

    def set_portadas_root(self, path: str):
        self._portadas_root = path

    def set_library_root(self, path: str):
        self._library_root = path

    # ── build ──────────────────────────────────────────────

    def _build(self):
        pad_x = {"padx": 5}

        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=5, pady=(5, 10))
        self.header = ttk.Label(header_frame, text="Selecciona una ficha", font=("", 12, "bold"))
        self.header.pack(side="left")
        self._dirty_label = tk.Label(header_frame, text="(sin guardar)",
                                     fg="red", font=("", 9))
        self._dirty_label.pack(side="left", padx=(4, 0))
        self._dirty_label.pack_forget()
        self._apply_btn = _icon_btn(header_frame, "💾", self._apply, "Aplicar cambios")
        self._revert_btn = _icon_btn(header_frame, "↩️", self._revert, "Revertir cambios")

        # Scrollable container for all fields
        self._canvas = tk.Canvas(self, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        scrollable = ttk.Frame(self._canvas)

        scrollable.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas_win = self._canvas.create_window((4, 0), window=scrollable, anchor="nw")
        self._canvas.configure(yscrollcommand=scroll.set)

        def _resize_scrollable(event):
            self._canvas.itemconfig(self._canvas_win, width=event.width - 8)

        self._canvas.bind("<Configure>", _resize_scrollable)
        self._scroll = scroll

        self._canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # ── fields in scrollable area ──
        row = 0
        self._fields = {}

        def add_field(label, key, widget_type="entry", options=None, readonly=False):
            nonlocal row
            f = ttk.Frame(scrollable)
            f.grid(row=row, column=0, sticky="ew", **pad_x)
            ttk.Label(f, text=label, width=20, anchor="w").pack(side="left")

            if widget_type == "entry":
                w = ttk.Entry(f)
                if readonly:
                    w.configure(state="readonly")
                else:
                    w.bind("<KeyRelease>", self._mark_dirty, add="+")
                w.pack(side="left", fill="x", expand=True)
            elif widget_type == "combo":
                w = ttk.Combobox(f, values=options, state="readonly")
                w.bind("<<ComboboxSelected>>", self._mark_dirty, add="+")
                w.pack(side="left", fill="x", expand=True)
            elif widget_type == "check":
                w = ttk.Checkbutton(f)
                w.pack(side="left")
                var = tk.BooleanVar()
                w.configure(variable=var)
                setattr(self, f"_var_{key}", var)
                var.trace_add("write", lambda *_: self._mark_dirty())
            elif widget_type == "text":
                w = tk.Text(f, height=3, wrap="word")
                w.bind("<KeyRelease>", self._mark_dirty, add="+")
                w.pack(side="left", fill="x", expand=True)
            elif widget_type == "file_path":
                inner = ttk.Frame(f)
                inner.pack(side="left", fill="x", expand=True)
                w = ttk.Entry(inner)
                if readonly:
                    w.configure(state="readonly")
                w.pack(side="left", fill="x", expand=True)
                btn = ttk.Button(inner, text="...", width=3, command=self._pick_destino)
                btn.pack(side="right", padx=(2, 0))
                self._fields[key + "_btn"] = btn

            self._fields[key] = w
            scrollable.columnconfigure(0, weight=1)
            row += 1

        add_field("Nombre legible", "nombre_legible", "entry")
        add_field("Tipo", "tipo", "combo", ["manual", "suplemento", "campaña", "aventura", "revista", "documento", "info", "imagen", "mapa", "hoja_pj", "pantalla", "musica", "otro"])
        add_field("Edición", "edicion", "combo", ["1ª", "2ª", "3ª", "4ª", "indeterminada"])
        add_field("Confianza", "confianza", "combo", ["alta", "media", "baja"])
        add_field("Destino", "destino", "file_path", readonly=True)

        add_field("Descripción", "descripcion", "text")
        add_field("Justificación", "justificacion", "text")

        ttk.Separator(scrollable, orient="horizontal").grid(
            row=row, column=0, sticky="ew", pady=5, **pad_x
        )
        row += 1

        add_field("Archivo Hash", "archivo_hash", "entry", readonly=True)
        add_field("Peso", "peso", "entry")
        add_field("Escaneado", "escaneado", "check")
        # ── portada fields ──
        ttk.Separator(scrollable, orient="horizontal").grid(
            row=row, column=0, sticky="ew", pady=5, **pad_x
        )
        row += 1

        ttk.Label(scrollable, text="Portada", font=("", 10, "bold")).grid(
            row=row, column=0, sticky="w", **pad_x
        )
        row += 1

        # Path row
        path_frame = ttk.Frame(scrollable)
        path_frame.grid(row=row, column=0, sticky="ew", **pad_x)
        ttk.Label(path_frame, text="Ruta portada", width=20, anchor="w").pack(side="left")
        self.portada_path = ttk.Entry(path_frame, state="readonly")
        self.portada_path.pack(side="left", fill="x", expand=True)
        row += 1

        # Buttons row
        btn_frame = ttk.Frame(scrollable)
        btn_frame.grid(row=row, column=0, sticky="w", **pad_x, pady=(2, 5))
        ttk.Button(btn_frame, text="Extraer portada...",
                   command=self._extract_portada).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Subir portada...",
                   command=self._upload_portada).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Abrir Directorio",
                   command=self._open_portada_dir).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Limpiar",
                   command=self._clear_portada).pack(side="left", padx=2)
        row += 1

        # Preview
        preview_frame = ttk.LabelFrame(scrollable, text="Vista previa")
        preview_frame.grid(row=row, column=0, sticky="nsew", **pad_x, pady=(0, 5))

        self.portada_label = ttk.Label(
            preview_frame, text="No Preview", anchor="center",
            background="#ddd",
        )
        self.portada_label.pack(padx=5, pady=5, fill="both", expand=True)

        scrollable.rowconfigure(row - 1, weight=1)

    # ── batch editing ───────────────────────────────────────

    def _build_batch(self):
        self._batch_frame = ttk.LabelFrame(self, text="Edición múltiple", padding=4)
        self._batch_widgets = {}

        row = 0
        for key, label, wtype, options in _BATCH_FIELDS:
            f = ttk.Frame(self._batch_frame)
            f.pack(fill="x", pady=2)
            ttk.Label(f, text=label, width=20, anchor="w").pack(side="left")

            if wtype == "combo":
                w = ttk.Combobox(f, values=options, state="readonly", width=18)
                w.pack(side="left", padx=(0, 4))
            elif wtype == "check":
                var = tk.BooleanVar()
                w = ttk.Checkbutton(f, variable=var)
                w.pack(side="left", padx=(0, 4))
                setattr(self, f"_batch_var_{key}", var)

            btn = ttk.Button(f, text="Aplicar", width=8,
                             command=lambda k=key, wt=wtype, wg=w: self._batch_apply(k, wt, wg))
            btn.pack(side="left")
            self._batch_widgets[key] = w

    # ── directory editing ───────────────────────────────────

    def _build_directory(self):
        self._dir_frame = ttk.LabelFrame(self, text="Directorio", padding=4)

        row = ttk.Frame(self._dir_frame)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Nombre", width=20, anchor="w").pack(side="left")
        self._dir_name_entry = ttk.Entry(row)
        self._dir_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(row, text="Renombrar", command=self._apply_dir_rename).pack(side="right")

        row2 = ttk.Frame(self._dir_frame)
        row2.pack(fill="x", pady=2)
        self._dir_visible_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="Mostrar en el árbol",
                        variable=self._dir_visible_var).pack(side="left")
        ttk.Button(row2, text="Eliminar directorio",
                   command=self._delete_dir).pack(side="right")

    def load_directory(self, dir_name: str, visible: bool,
                       on_rename: Callable[[str, str], None] = None,
                       on_delete: Callable[[str], None] = None):
        self._dir_name = dir_name
        self._on_dir_rename = on_rename
        self._on_dir_delete = on_delete

        self._canvas.pack_forget()
        self._scroll.pack_forget()
        self._batch_frame.pack_forget()
        self._apply_btn.pack(side="right", padx=2)
        self._revert_btn.pack(side="right", padx=2)

        self._dir_name_entry.delete(0, "end")
        self._dir_name_entry.insert(0, dir_name)
        self._dir_visible_var.set(visible)
        self.header.config(text=f"📁 {dir_name}")

        self._dir_frame.pack(fill="x", padx=5, pady=(5, 0))

    def _hide_directory(self):
        self._dir_frame.pack_forget()
        self._dir_name = None

    def _apply_dir_rename(self):
        new_name = self._dir_name_entry.get().strip()
        if not new_name:
            messagebox.showwarning("Renombrar", "El nombre no puede estar vacío.")
            return
        if new_name == self._dir_name:
            return
        if self._on_dir_rename:
            self._on_dir_rename(self._dir_name, new_name)

    def _delete_dir(self):
        if not self._dir_name:
            return
        if not messagebox.askyesno(
            "Eliminar directorio",
            f"¿Eliminar el directorio '{self._dir_name}'?\n\n"
            "Los items que contiene se moverán a la raíz.\n"
            "El directorio físico también se eliminará."
        ):
            return
        if self._on_dir_delete:
            self._on_dir_delete(self._dir_name)

    def _batch_apply(self, key: str, wtype: str, widget):
        for item in self._batch_items:
            if wtype == "combo":
                val = widget.get().strip()
                if val:
                    setattr(item, key, val)
            elif wtype == "check":
                var_name = f"_batch_var_{key}"
                if hasattr(self, var_name):
                    setattr(item, key, getattr(self, var_name).get())
            if self.on_item_changed:
                self.on_item_changed(item)
        self._mark_dirty()

    def _show_batch(self):
        self._canvas.pack_forget()
        self._scroll.pack_forget()
        self._batch_frame.pack(fill="x", padx=5, pady=(5, 0))
        self._apply_btn.pack_forget()
        self._revert_btn.pack_forget()

    def _hide_batch(self):
        self._batch_frame.pack_forget()
        self._apply_btn.pack(side="right", padx=2)
        self._revert_btn.pack(side="right", padx=2)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scroll.pack(side="right", fill="y")

    def load_items(self, items: List[Item]) -> bool:
        if len(items) == 0:
            self._item = None
            self._batch_items = []
            self.header.config(text="Selecciona una ficha")
            self._clear_fields()
            self._hide_batch()
            self._hide_directory()
            return True
        self._hide_directory()
        if len(items) == 1:
            self._batch_items = []
            self._hide_batch()
            return self.load_item(items[0])
        if self._item and self._dirty:
            if not messagebox.askyesno(
                "Cambios sin guardar",
                "Hay cambios sin aplicar en la ficha actual. ¿Descartarlos?"
            ):
                return False
        self._item = None
        self._batch_items = list(items)
        self.header.config(text=f"Editando: {len(items)} items")
        self._clear_fields()
        self._show_batch()
        return True

    # ── dirty tracking ────────────────────────────────────

    def _mark_dirty(self, event=None):
        if getattr(self, "_loading", False):
            return
        if self._item and not self._dirty:
            self._dirty = True
            self._dirty_label.pack(side="left", padx=(4, 0))

    def _pick_destino(self):
        initial = self._library_root or os.getcwd()
        path = filedialog.askdirectory(
            title="Seleccionar carpeta de destino",
            initialdir=initial,
        )
        if not path:
            return
        if self._library_root:
            rel = os.path.relpath(path, self._library_root)
        else:
            rel = path
        dest_entry = self._fields.get("destino")
        if dest_entry:
            dest_entry.configure(state="normal")
            dest_entry.delete(0, "end")
            dest_entry.insert(0, rel + "/")
            dest_entry.configure(state="readonly")
        self._mark_dirty()

    # ── load item ──────────────────────────────────────────

    def load_item(self, item: Optional[Item]) -> bool:
        if self._item and self._dirty and item is not None and item is not self._item:
            if not messagebox.askyesno(
                "Cambios sin guardar",
                "Hay cambios sin aplicar en la ficha actual. ¿Descartarlos?"
            ):
                return False
        self._item = item
        self._batch_items = []
        self._hide_batch()
        self._hide_directory()

        if item is None:
            self.header.config(text="Selecciona una ficha")
            self._clear_fields()
            return True

        self.header.config(text=item.display_name())
        self._dirty_label.pack_forget()
        self._loading = True
        self._fields_to_ui(item)
        self._loading = False
        self._dirty = False
        return True

    def _clear_fields(self):
        for key, widget in self._fields.items():
            if isinstance(widget, ttk.Entry):
                widget.configure(state="normal")
                widget.delete(0, "end")
                widget.configure(state="readonly")
            elif isinstance(widget, tk.Text):
                widget.delete("1.0", "end")
            elif isinstance(widget, ttk.Combobox):
                widget.set("")

        if hasattr(self, "_var_escaneado"):
            self._var_escaneado.set(False)
        self.portada_label.config(text="No Preview", image="", background="#ddd")
        self.portada_path.configure(state="normal")
        self.portada_path.delete(0, "end")
        self.portada_path.configure(state="readonly")

    def _fields_to_ui(self, item: Item):
        def set_entry(key, val):
            w = self._fields.get(key)
            if w:
                w.configure(state="normal")
                w.delete(0, "end")
                w.insert(0, str(val) if val else "")
                w.configure(state="readonly" if key in ("archivo_hash", "destino") else "normal")

        def set_combo(key, val):
            w = self._fields.get(key)
            if w:
                if val in w["values"]:
                    w.set(val)
                else:
                    w.set("")

        def set_text(key, val):
            w = self._fields.get(key)
            if w:
                w.delete("1.0", "end")
                w.insert("1.0", str(val) if val else "")

        def set_check(key, val):
            var_name = f"_var_{key}"
            if hasattr(self, var_name):
                getattr(self, var_name).set(bool(val))

        set_entry("nombre_legible", item.nombre_legible)
        set_combo("tipo", item.tipo)
        set_combo("edicion", item.edicion)
        set_combo("confianza", item.confianza)
        set_entry("destino", item.destino)
        set_text("descripcion", item.descripcion)
        set_text("justificacion", item.justificacion)
        set_entry("archivo_hash", item.archivo_hash)
        set_entry("peso", item.peso)
        set_check("escaneado", item.escaneado)

        self._update_portada_preview(item)

    # ── portada preview ────────────────────────────────────

    def _update_portada_preview(self, item: Optional[Item] = None):
        item = item or self._item

        self.portada_path.configure(state="normal")
        self.portada_path.delete(0, "end")

        if not item or not item.portada:
            self.portada_path.configure(state="readonly")
            self.portada_label.config(text="No Preview", image="", background="#ddd")
            return

        self.portada_path.insert(0, item.portada)
        self.portada_path.configure(state="readonly")

        abs_path = self._resolve_portada_path(item.portada)
        if not abs_path or not Path(abs_path).exists():
            self.portada_label.config(
                text=f"Archivo no encontrado:\n{abs_path}" if abs_path else "Ruta no resoluble",
                image="", background="#fdd",
            )
            return

        self._show_image(abs_path)

    def _show_image(self, path: str):
        if _HAS_PIL:
            try:
                pil_img = Image.open(path)
                pil_img.thumbnail((250, 300), Image.LANCZOS)
                buf = BytesIO()
                pil_img.save(buf, format="PNG")
                tk_img = tk.PhotoImage(data=buf.getvalue())
                self.portada_label.config(text="", image=tk_img, background="")
                self.portada_label.image = tk_img
                return
            except Exception:
                pass

        try:
            img = tk.PhotoImage(file=path)
            self.portada_label.config(text="", image=img, background="")
            self.portada_label.image = img
        except Exception:
            self.portada_label.config(
                text=f"Preview no disponible", image="", background="#eee",
            )

    def _resolve_portada_path(self, portada_rel: str) -> Optional[str]:
        if not portada_rel:
            return None
        if portada_rel.startswith("/") or (len(portada_rel) > 1 and portada_rel[1] == ":"):
            return portada_rel
        if self._web_root:
            return str(Path(self._web_root) / portada_rel)
        return None

    # ── portada actions ────────────────────────────────────

    def _upload_portada(self):
        if not self._item:
            return

        path = filedialog.askopenfilename(
            title="Seleccionar imagen de portada",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.webp *.gif")],
        )
        if not path:
            return

        if not self._portadas_root:
            messagebox.showwarning(
                "Sin ruta de portadas",
                "Configura la 'Ruta portadas' en la pestaña Configuración primero.",
            )
            return

        try:
            upload_portada(self._item, path, self._portadas_root, self._web_root)
            self._update_portada_preview()
            self._mark_dirty()
            if self.on_item_changed:
                self.on_item_changed(self._item)
        except Exception as e:
            messagebox.showerror("Error al subir portada", str(e))

    def _clear_portada(self):
        if not self._item:
            return
        self._item.portada = ""
        self._update_portada_preview()
        self._mark_dirty()
        if self.on_item_changed:
            self.on_item_changed(self._item)

    def _extract_portada(self):
        if not self._item:
            return
        if not self._library_root or not self._portadas_root:
            messagebox.showwarning(
                "Rutas sin configurar",
                "Configura 'Ruta biblioteca' y 'Ruta portadas' en la pestaña "
                "Configuración primero.",
            )
            return
        if not self._item.destino:
            messagebox.showwarning(
                "Sin destino",
                "Esta ficha no tiene un archivo de destino asignado.",
            )
            return

        def on_extracted(item, portada_rel):
            item.portada = portada_rel
            self._update_portada_preview()
            self._mark_dirty()
            if self.on_item_changed:
                self.on_item_changed(item)

        SinglePortadaExtractDialog(
            self,
            item=self._item,
            library_root=self._library_root,
            portadas_root=self._portadas_root,
            web_root=self._web_root,
            on_done=on_extracted,
        )

    def _open_portada_dir(self):
        if not self._item:
            return
        if not self._item.portada:
            messagebox.showinfo(
                "Sin portada",
                "Esta ficha no tiene portada asignada.",
            )
            return
        abs_path = self._resolve_portada_path(self._item.portada)
        if not abs_path:
            messagebox.showwarning(
                "Ruta no resoluble",
                "No se pudo resolver la ruta de la portada.",
            )
            return
        target = str(Path(abs_path).parent)
        if not Path(target).exists():
            # Try via portadas_root
            if self._portadas_root:
                target = str(Path(self._portadas_root) / self._item.destino)
            if not Path(target).exists():
                messagebox.showwarning(
                    "Directorio no encontrado",
                    f"No existe:\n{target}",
                )
                return
        try:
            if sys.platform == "win32":
                os.startfile(target)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el directorio:\n{e}")

    # ── apply / revert ─────────────────────────────────────

    def _ui_to_fields(self, item: Item) -> Item:
        def get_entry(key):
            w = self._fields.get(key)
            return w.get().strip() if w else ""

        def get_combo(key):
            w = self._fields.get(key)
            return w.get().strip() if w else ""

        def get_text(key):
            w = self._fields.get(key)
            return w.get("1.0", "end-1c").strip() if w else ""

        def get_check(key):
            var_name = f"_var_{key}"
            if hasattr(self, var_name):
                return getattr(self, var_name).get()
            return False

        item.nombre_legible = get_entry("nombre_legible")
        item.tipo = get_combo("tipo") or "otro"
        item.edicion = get_combo("edicion") or "indeterminada"
        item.confianza = get_combo("confianza") or "media"
        item.destino = get_entry("destino")
        item.descripcion = get_text("descripcion")
        item.justificacion = get_text("justificacion")
        item.archivo_hash = get_entry("archivo_hash")
        item.peso = get_entry("peso")
        item.escaneado = get_check("escaneado")

        return item

    def _apply(self):
        if not self._item:
            return
        self._ui_to_fields(self._item)
        self._dirty_label.pack_forget()
        self._dirty = False
        if self.on_item_changed:
            self.on_item_changed(self._item)

    def _revert(self):
        if not self._item:
            return
        if self._dirty:
            if not messagebox.askyesno("Revertir", "¿Descartar cambios no aplicados?"):
                return
        self._fields_to_ui(self._item)
        self._dirty_label.pack_forget()
        self._dirty = False

    def get_item(self) -> Optional[Item]:
        return self._item

    def get_dir_name(self) -> Optional[str]:
        return self._dir_name

    def is_dirty(self) -> bool:
        return self._dirty
