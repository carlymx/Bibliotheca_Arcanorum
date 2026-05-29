import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Callable, Optional

from .models import Item
from .io_pack import (
    detect_format,
    read_bibliotex_json,
    read_bibliotex_zip,
    BibliotexError,
)
from .import_handler import ImportOptions, ImportResult, import_file


class ImportDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        existing_items: list[Item],
        config: dict,
        on_import_done: Optional[Callable[[ImportResult], None]] = None,
        initial_path: str = "",
    ):
        super().__init__(parent)
        self.title("Importar fichas")
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)
        self.geometry("940x600")
        self.minsize(790, 450)

        self.existing_items = existing_items
        self.config = config
        self.on_import_done = on_import_done
        self._result: Optional[ImportResult] = None

        self._build()
        self._progress_bar["maximum"] = 100

        if initial_path:
            self._load_file(initial_path)

        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        wx = parent.winfo_rootx()
        wy = parent.winfo_rooty()
        dw = self.winfo_reqwidth()
        dh = self.winfo_reqheight()
        self.geometry(f"+{wx + (pw - dw) // 2}+{wy + (ph - dh) // 2}")

    def _build(self):
        pad = {"padx": 10, "pady": 5}

        # ── header / file selection ──
        header = ttk.Frame(self)
        header.pack(fill="x", **pad)

        ttk.Label(header, text="Importar fichas", font=("", 12, "bold")).pack(side="left")

        ttk.Button(header, text="Seleccionar archivo...", command=self._select_file).pack(
            side="right", padx=(5, 0)
        )

        self._file_label = ttk.Label(header, text="(ningún archivo seleccionado)", foreground="gray")
        self._file_label.pack(side="right", padx=(0, 5))

        ttk.Separator(self, orient="horizontal").pack(fill="x", **pad)

        # ── preview ──
        preview_frame = ttk.LabelFrame(self, text="Vista previa", padding=5)
        preview_frame.pack(fill="both", expand=True, **pad)

        select_bar = ttk.Frame(preview_frame)
        select_bar.pack(fill="x", pady=(0, 4))
        ttk.Button(select_bar, text="Seleccionar todo", command=self._select_all).pack(side="left", padx=(0, 4))
        ttk.Button(select_bar, text="Seleccionar nada", command=self._select_none).pack(side="left")

        tree_frame = ttk.Frame(preview_frame)
        tree_frame.pack(side="left", fill="both", expand=True)

        cols = ("nombre", "juego", "tipo", "destino", "estado")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 height=10)
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("juego", text="Juego")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("destino", text="Destino")
        self.tree.heading("estado", text="Estado")
        self.tree.column("nombre", width=180)
        self.tree.column("juego", width=100)
        self.tree.column("tipo", width=80)
        self.tree.column("destino", width=180)
        self.tree.column("estado", width=80)

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_preview_select)

        # ── portada preview ──
        portada_frame = ttk.Frame(preview_frame, width=180)
        portada_frame.pack(side="right", fill="y", padx=(5, 0))
        portada_frame.pack_propagate(False)

        ttk.Label(portada_frame, text="Portada", font=("", 9, "bold")).pack(anchor="n")
        self._portada_label = ttk.Label(portada_frame, text="")
        self._portada_label.pack(expand=True, fill="both")

        # ── options ──
        opts_frame = ttk.LabelFrame(self, text="Opciones de importación", padding=10)
        opts_frame.pack(fill="x", **pad)

        # destino
        dest_row = ttk.Frame(opts_frame)
        dest_row.pack(fill="x", pady=(0, 5))

        ttk.Label(dest_row, text="Destino:", width=12).pack(side="left")
        self._dest_modo_var = tk.StringVar(
            value=self.config.get("import_modo_destino_default", "estructura")
        )
        ttk.Radiobutton(
            dest_row,
            text="Estructura relativa",
            variable=self._dest_modo_var,
            value="estructura",
        ).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(
            dest_row,
            text="Carpeta específica:",
            variable=self._dest_modo_var,
            value="carpeta_fija",
        ).pack(side="left")

        self._carpeta_var = tk.StringVar(
            value=self.config.get("import_carpeta_default", "Importados")
        )
        self._carpeta_entry = ttk.Entry(dest_row, textvariable=self._carpeta_var, width=20)
        self._carpeta_entry.pack(side="left", padx=(5, 0))

        self._dest_modo_var.trace_add("write", lambda *a: self._on_dest_mode_change())
        self._on_dest_mode_change()

        # duplicados
        dup_row = ttk.Frame(opts_frame)
        dup_row.pack(fill="x")

        ttk.Label(dup_row, text="Duplicados:", width=12).pack(side="left")
        self._dup_var = tk.StringVar(
            value=self.config.get("import_comportamiento_default", "saltar")
        )
        ttk.Radiobutton(
            dup_row,
            text="Saltar",
            variable=self._dup_var,
            value="saltar",
        ).pack(side="left", padx=(0, 5))
        ttk.Radiobutton(
            dup_row,
            text="Sobrescribir",
            variable=self._dup_var,
            value="sobrescribir",
        ).pack(side="left", padx=(0, 5))
        ttk.Radiobutton(
            dup_row,
            text="Importar todos",
            variable=self._dup_var,
            value="importar_todos",
        ).pack(side="left")

        # ── progress ──
        self._progress_bar = ttk.Progressbar(self, mode="determinate")
        self._progress_label = ttk.Label(self, text="")
        self._progress_bar.pack(fill="x", **pad)
        self._progress_label.pack(**pad)

        # ── buttons ──
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)

        self._import_btn = ttk.Button(
            btn_frame, text="Importar", command=self._do_import, state="disabled"
        )
        self._import_btn.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side="left", padx=5)

    def _on_dest_mode_change(self):
        state = "normal" if self._dest_modo_var.get() == "carpeta_fija" else "disabled"
        self._carpeta_entry.configure(state=state)

    def _select_file(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de importación",
            filetypes=[
                ("Bibliotex", "*.bibliotex *.bibliotex.zip"),
                ("Bibliotex JSON", "*.bibliotex"),
                ("Bibliotex ZIP", "*.bibliotex.zip"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not path:
            return
        self._load_file(path)

    def _load_file(self, path: str):
        self._file_label.config(text=Path(path).name, foreground="black")
        self._current_path = path
        self._import_btn.configure(state="normal")
        self._preview_items = None
        self._portadas_data = {}

        try:
            fmt = detect_format(path)

            if fmt == "zip":
                items_dicts, meta, portadas, _ = read_bibliotex_zip(
                    path, load_portadas=True, load_pdfs=False
                )
                self._portadas_data = portadas
            else:
                items_dicts, meta = read_bibliotex_json(path)

            self._preview_items = [Item.from_dict(d) for d in items_dicts]
            self._preview_metadata = meta
            self._populate_preview()
        except BibliotexError as e:
            messagebox.showerror("Error al leer archivo", str(e), parent=self)
            self._import_btn.configure(state="disabled")
            self._preview_items = None
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}", parent=self)
            self._import_btn.configure(state="disabled")
            self._preview_items = None

    def _populate_preview(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        if not self._preview_items:
            return

        existing_hashes = {i.archivo_hash for i in self.existing_items if i.archivo_hash}

        for idx, item in enumerate(self._preview_items):
            is_dup = item.archivo_hash and item.archivo_hash in existing_hashes
            estado = "🔁 duplicado" if is_dup else "🆕 nuevo"
            self.tree.insert(
                "", "end",
                iid=str(idx),
                values=(
                    item.nombre_legible or "(sin nombre)",
                    item.juego,
                    item.tipo,
                    item.destino or "",
                    estado,
                ),
                tags=("duplicado",) if is_dup else (),
            )

        self.tree.tag_configure("duplicado", foreground="orange")
        self.tree.selection_set(self.tree.get_children())

        if hasattr(self, "_source_label") and self._source_label:
            self._source_label.destroy()

        self._source_label = ttk.Label(self, font=("", 9), foreground="gray")
        self._source_label.pack(fill="x", padx=10)
        self._update_selection_info()

    def _select_all(self):
        self.tree.selection_set(self.tree.get_children())
        self._on_preview_select(None)

    def _select_none(self):
        self.tree.selection_remove(self.tree.selection())
        self._on_preview_select(None)

    def _update_selection_info(self):
        if not self._preview_items or not hasattr(self, "_source_label"):
            return
        sel = self.tree.selection()
        existing_hashes = {i.archivo_hash for i in self.existing_items if i.archivo_hash}
        total = len(self._preview_items)
        total_dups = sum(1 for item in self._preview_items
                         if item.archivo_hash and item.archivo_hash in existing_hashes)
        if sel:
            selected_indices = {self.tree.index(item) for item in sel}
            sel_count = len(selected_indices)
            sel_dups = sum(1 for idx in selected_indices
                           if idx < len(self._preview_items)
                           and self._preview_items[idx].archivo_hash
                           and self._preview_items[idx].archivo_hash in existing_hashes)
        else:
            sel_count = 0
            sel_dups = 0
        source = self._preview_metadata.get("biblioteca_origen", "Desconocida")
        self._source_label.config(
            text=f"Origen: {source}  |  {sel_count}/{total} seleccionados  |  {sel_dups} duplicados (de {total_dups} totales)"
        )

    def _on_preview_select(self, event):
        self._update_selection_info()
        sel = self.tree.selection()
        if not sel or not self._preview_items:
            self._portada_label.config(image="", text="")
            return

        focus = self.tree.focus()
        if not focus:
            focus = sel[-1]
        idx = self.tree.index(focus)
        if idx >= len(self._preview_items):
            return

        item = self._preview_items[idx]
        data = self._find_portada_for_item(item)
        if data:
            from PIL import Image, ImageTk
            img = Image.open(io.BytesIO(data))
            img.thumbnail((170, 200))
            tk_img = ImageTk.PhotoImage(img)
            self._portada_label.config(image=tk_img, text="")
            self._portada_label.image = tk_img
        else:
            self._portada_label.config(image="", text="(sin portada)")

    def _find_portada_for_item(self, item) -> Optional[bytes]:
        stem = Path(item.nombre_legible or "").stem
        if not stem:
            return None
        target = f"[portada]_{stem}"
        dest_parts = set((item.destino or "").rstrip("/").split("/"))
        for key, data in self._portadas_data.items():
            if target not in key:
                continue
            if not dest_parts:
                return data
            key_parts = set(Path(key).parts[:-1])
            if dest_parts & key_parts:
                return data
        return None

    def _progress(self, pct, msg):
        self._progress_bar.configure(value=pct)
        self._progress_label.configure(text=msg)
        self.update_idletasks()

    def _do_import(self):
        if not self._preview_items or not hasattr(self, "_current_path"):
            return

        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Importar", "No hay fichas seleccionadas.", parent=self)
            return
        selected_indices = {self.tree.index(item) for item in sel}
        selected_indices = {i for i in selected_indices if i < len(self._preview_items)}

        if not self.existing_items:
            if not messagebox.askyesno(
                "Confirmar importación",
                f"Se importarán {len(selected_indices)} fichas.\n"
                "No hay fichas en el catálogo actual.\n"
                "¿Continuar?",
                parent=self,
            ):
                return

        opciones = ImportOptions(
            comportamiento_duplicados=self._dup_var.get(),
            modo_destino=self._dest_modo_var.get(),
            carpeta_destino=self._carpeta_var.get().strip() or "Importados",
        )

        self._import_btn.configure(state="disabled")

        try:
            result = import_file(
                self._current_path,
                library_root=self.config.get("library_root", ""),
                portadas_root=self.config.get("portadas_root", ""),
                opciones=opciones,
                existing_items=self.existing_items,
                progress_callback=self._progress,
                selected_indices=selected_indices,
            )
            self._result = result
            self._show_result(result, callback=self.on_import_done)
        except BibliotexError as e:
            messagebox.showerror("Error de importación", str(e), parent=self)
            self._import_btn.configure(state="normal")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo importar:\n{e}", parent=self)
            self._import_btn.configure(state="normal")

    def _show_result(self, result: ImportResult, callback: Optional[Callable[[ImportResult], None]] = None):
        parts = []
        if result.importados:
            parts.append(f"{len(result.importados)} importados")
        if result.sobrescritos:
            parts.append(f"{len(result.sobrescritos)} sobrescritos")
        if result.saltados:
            parts.append(f"{len(result.saltados)} saltados")
        if result.errores:
            parts.append(f"{len(result.errores)} errores")
        if result.pdfs_faltantes:
            parts.append(f"{len(result.pdfs_faltantes)} PDFs faltantes")
        if result.portadas_extraidas:
            parts.append(f"{result.portadas_extraidas} portadas extraídas")

        msg = "\n".join(parts) if parts else "Sin cambios"
        messagebox.showinfo(
            "Importación completada",
            f"Resultado:\n\n{msg}",
            parent=self,
        )
        self.destroy()
        if callback:
            self.after(10, lambda: callback(result))

    def get_result(self) -> Optional[ImportResult]:
        return self._result
