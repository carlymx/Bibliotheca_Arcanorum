import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional, Set

from pathlib import Path

from .models import (
    DuplicateGroup,
    Item,
    ModifiedResult,
    RenameResult,
    ScanReport,
)
from .portada_mgr import resolve_portada_file


class ScanReviewDialog(tk.Toplevel):
    def __init__(self, parent, report: ScanReport, portadas_root: str = ""):
        super().__init__(parent)
        self.report = report
        self.portadas_root = portadas_root
        self.result: Optional[str] = None

        self._iid_map: Dict[str, Any] = {}
        self._checked: Set[str] = set()
        self._header_vars: List[tk.StringVar] = []
        self._auto_portadas = tk.BooleanVar(value=True)

        self.title("Revisar cambios — Escaneo completado")
        self.geometry("1000x650")
        self.minsize(800, 500)
        self.transient(parent)
        self.grab_set()

        self._column_weights = {
            "new": [6, 32, 22, 16, 20],
            "missing": [6, 40, 30, 24],
            "mod": [6, 34, 24, 36],
            "ren": [6, 34, 24, 36],
            "exc": [6, 40, 30, 24],
            "dup": [30, 18, 52],
        }

        self._build_ui()
        self._populate()
        self._update_summary()

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    # ── build ──────────────────────────────────────────────

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=(8, 0))

        ttk.Label(top, text="🔍", font=("", 12)).pack(side="left", padx=(0, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter())
        search_entry = ttk.Entry(top, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ttk.Button(top, text="☐ Sel. todos", command=self._select_all).pack(side="left", padx=2)
        ttk.Button(top, text="☐ Ninguno", command=self._select_none).pack(side="left", padx=2)

        # ── collapsible sections ─────────────────────────────

        self._canvas_frame = ttk.Frame(self)
        self._canvas_frame.pack(fill="both", expand=True, padx=6, pady=6)

        canvas = tk.Canvas(self._canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._canvas_frame, orient="vertical", command=canvas.yview)
        self._scrollable = ttk.Frame(canvas)

        self._scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._canvas_win_id = canvas.create_window((0, 0), window=self._scrollable, anchor="nw")
        canvas.bind("<Configure>", lambda e: self._on_canvas_resize(e, canvas))

        self._bind_mousewheel(canvas)

        # ── sections ───
        self._sections: List[dict] = []

        self._build_section("🆕 Nuevos", "new", ["Nombre", "Destino", "Tamaño", "Portada"],
                            lambda r: [(i.nombre_legible, i.destino, i.peso, self._portada_status(i))
                                       for i in r.new_items],
                            len(self.report.new_items) > 0)

        self._build_section("❌ Faltantes", "missing", ["Nombre", "Destino", ""],
                            lambda r: [(i.nombre_legible, i.destino, "Archivo no encontrado") for i in r.missing_items],
                            len(self.report.missing_items) > 0)

        self._build_section("🔄 Modificados", "mod", ["Nombre", "Destino", "Hash"],
                            lambda r: [(i.item.nombre_legible, i.item.destino,
                                        self._format_hash(i.old_hash, i.new_hash))
                                       for i in r.modified_items],
                            len(self.report.modified_items) > 0)

        self._build_section("🔀 Renombrados", "ren", ["Nombre orig.", "Destino orig.", "Nuevo nombre"],
                            lambda r: [(i.item.nombre_legible, i.item.destino,
                                        f"→ {i.new_name}  ({i.new_destino})")
                                       for i in r.renamed_items],
                            len(self.report.renamed_items) > 0)

        self._build_section("⚠️ Excluidos en catálogo", "exc", ["Nombre", "Destino", ""],
                            lambda r: [(i.nombre_legible, i.destino,
                                        "El archivo coincide con scan_exclude")
                                       for i in r.excluded_in_catalog],
                            len(self.report.excluded_in_catalog) > 0)

        dup_data: List[tuple] = []
        for dg in self.report.duplicates:
            first = dg.paths[0].name if dg.paths else ""
            rest = ", ".join(str(p) for p in dg.paths[1:])
            dup_data.append((first, f"{len(dg.paths)} copias", rest))
        self._build_section("📋 Duplicados", "dup", ["Archivo", "Copias", "Rutas"],
                            lambda r: dup_data,
                            len(self.report.duplicates) > 0,
                            show_checkbox=False)

        # matched & excluded_on_disk → plain info rows
        info_parts = []
        if self.report.matched_items:
            info_parts.append(f"✅ {len(self.report.matched_items)} archivos ya catalogados")
        if self.report.excluded_on_disk:
            info_parts.append(f"🚫 {self.report.excluded_on_disk} archivos ignorados (scan_exclude)")
        if info_parts:
            info_frame = ttk.LabelFrame(self._scrollable, text="Resumen general", padding=4)
            info_frame.pack(fill="x", pady=(4, 0))
            for line in info_parts:
                ttk.Label(info_frame, text=line).pack(anchor="w", padx=6, pady=1)

        # ── bottom bar ──────────────────────────────────────

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=8, pady=(0, 8))

        ttk.Checkbutton(bottom, text="🖼 Autocompletar portadas",
                        variable=self._auto_portadas).pack(side="left", padx=4)

        self.summary_var = tk.StringVar()
        ttk.Label(bottom, textvariable=self.summary_var, font=("", 10, "bold")).pack(side="left", padx=4)

        ttk.Button(bottom, text="Aplicar cambios", command=self._on_apply, width=18).pack(side="right", padx=2)
        ttk.Button(bottom, text="Cancelar", command=self._on_cancel, width=12).pack(side="right", padx=2)

    def _build_section(self, title: str, prefix: str, columns: List[str],
                       data_fn, has_data: bool, show_checkbox: bool = True):
        if not has_data:
            return

        header_var = tk.StringVar(value=f"▼ {title}")
        section = {"prefix": prefix, "data_fn": data_fn, "header_var": header_var,
                   "visible": True, "show_checkbox": show_checkbox,
                   "columns": columns, "frame": None, "tree": None}

        hdr_frame = ttk.Frame(self._scrollable)
        hdr_frame.pack(fill="x", pady=(6, 0), padx=2)

        hdr = ttk.Label(hdr_frame, textvariable=header_var,
                        font=("", 10, "bold"), cursor="hand2")
        hdr.pack(side="left")
        hdr.bind("<Button-1>", lambda e, s=section: self._toggle_section(s))

        if show_checkbox:
            ttk.Button(hdr_frame, text="Sel", width=3,
                       command=lambda p=prefix: self._select_section(p)).pack(side="right", padx=1)
            ttk.Button(hdr_frame, text="No", width=3,
                       command=lambda p=prefix: self._deselect_section(p)).pack(side="right", padx=1)

        frame = ttk.Frame(self._scrollable)
        frame.pack(fill="x", pady=(0, 2), padx=4)
        section["frame"] = frame

        tree = ttk.Treeview(frame, columns=columns, show="headings", height=5)
        for col in columns:
            lbl = col if col else " "
            tree.heading(col, text=lbl, command=lambda c=col, t=tree: self._sort_tree(t, c))
            tree.column(col, width=100, minwidth=60)

        tree.pack(side="left", fill="x", expand=True)

        tree.bind("<ButtonRelease-1>", lambda e, t=tree: self._on_tree_click(e, t, section))

        section["tree"] = tree
        self._sections.append(section)

    # ── populate ────────────────────────────────────────────

    def _populate(self):
        self._iid_map.clear()
        self._checked.clear()

        for section in self._sections:
            tree: ttk.Treeview = section["tree"]
            prefix = section["prefix"]
            rows = section["data_fn"](self.report)

            for idx, row in enumerate(rows):
                iid = f"{prefix}_{idx}"
                if section["show_checkbox"]:
                    checked = "☑" if prefix in ("new", "missing", "mod", "exc") else "☐"
                    values = [checked] + list(row)
                    tree["columns"] = ["☐"] + section["columns"]
                    tree.heading("☐", text="☐")
                    tree.column("☐", width=30, minwidth=24, anchor="center")
                else:
                    values = list(row)
                tree.insert("", "end", iid=iid, values=values)
                if section["show_checkbox"]:
                    self._iid_map[iid] = (prefix, idx, row)
                    if prefix in ("new", "missing", "mod", "exc"):
                        self._checked.add(iid)

            tree.configure(height=min(len(rows), 8))

        self.update_idletasks()
        self._stretch_all_trees()

    # ── toggle section visibility ──────────────────────────

    def _toggle_section(self, section: dict):
        section["visible"] = not section["visible"]
        section["header_var"].set(
            f"▼ {section['header_var'].get()[2:]}" if section["visible"]
            else f"▶ {section['header_var'].get()[2:]}"
        )
        if section["visible"]:
            section["frame"].pack(fill="x", pady=(0, 2), padx=4)
        else:
            section["frame"].pack_forget()

    # ── checkbox toggle ─────────────────────────────────────

    def _on_tree_click(self, event, tree: ttk.Treeview, section: dict):
        if not section["show_checkbox"]:
            return
        region = tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = tree.identify_column(event.x)
        if col != "#1":
            return
        iid = tree.identify_row(event.y)
        if not iid:
            return
        values = list(tree.item(iid, "values"))
        if values[0] == "☑":
            values[0] = "☐"
            self._checked.discard(iid)
        else:
            values[0] = "☑"
            self._checked.add(iid)
        tree.item(iid, values=values)
        self._update_summary()

    # ── select all / none ───────────────────────────────────

    def _select_all(self):
        for iid in self._iid_map:
            self._checked.add(iid)
        self._refresh_checkboxes()
        self._update_summary()

    def _select_none(self):
        self._checked.clear()
        self._refresh_checkboxes()
        self._update_summary()

    def _select_section(self, prefix: str):
        for iid in list(self._iid_map.keys()):
            if iid.startswith(prefix + "_"):
                self._checked.add(iid)
        self._refresh_checkboxes()
        self._update_summary()

    def _deselect_section(self, prefix: str):
        for iid in list(self._iid_map.keys()):
            if iid.startswith(prefix + "_"):
                self._checked.discard(iid)
        self._refresh_checkboxes()
        self._update_summary()

    def _refresh_checkboxes(self):
        for section in self._sections:
            tree = section["tree"]
            if not section["show_checkbox"]:
                continue
            for iid in tree.get_children():
                values = list(tree.item(iid, "values"))
                values[0] = "☑" if iid in self._checked else "☐"
                tree.item(iid, values=values)

    # ── summary ─────────────────────────────────────────────

    def _update_summary(self):
        counts = {"new": 0, "missing": 0, "mod": 0, "ren": 0, "exc": 0}
        for iid in self._checked:
            prefix = iid.rsplit("_", 1)[0]
            if prefix in counts:
                counts[prefix] += 1
        parts = []
        if counts["new"]:
            parts.append(f"+{counts['new']} añadir")
        if counts["missing"]:
            parts.append(f"-{counts['missing']} eliminar")
        if counts["mod"]:
            parts.append(f"~{counts['mod']} actualizar")
        if counts["ren"]:
            parts.append(f"~{counts['ren']} renombrar")
        if counts["exc"]:
            parts.append(f"⚠{counts['exc']} eliminar (excluidos)")

        text = " │ ".join(parts) if parts else "Ningún cambio seleccionado"
        self.summary_var.set(f"📊 {text}")

    # ── apply / cancel ──────────────────────────────────────

    def _on_apply(self):
        self.result = "apply"
        self.destroy()

    def _on_cancel(self):
        if self._checked:
            from tkinter import messagebox
            resp = messagebox.askyesno(
                "Descartar cambios",
                "Hay cambios seleccionados. ¿Descartarlos?",
                parent=self,
            )
            if not resp:
                return
        self.result = None
        self.destroy()

    # ── helpers ─────────────────────────────────────────────

    def _filter(self):
        query = self.search_var.get().lower()
        for section in self._sections:
            tree = section["tree"]
            for iid in tree.get_children():
                vals = tree.item(iid, "values")
                text = " ".join(str(v) for v in vals).lower()
                if not query or query in text:
                    tree.reattach(iid, "", "end")
                else:
                    tree.detach(iid)

    def _sort_tree(self, tree: ttk.Treeview, col: str):
        items = [(tree.item(iid, "values"), iid) for iid in tree.get_children("")]
        col_idx = tree["columns"].index(col) if col in tree["columns"] else 0
        items.sort(key=lambda x: str(x[0][col_idx]).lower() if col_idx < len(x[0]) else "")

        for idx, (_, iid) in enumerate(items):
            tree.move(iid, "", idx)

    def _on_canvas_resize(self, event, canvas: tk.Canvas):
        if event.width > 50:
            canvas.itemconfig(self._canvas_win_id, width=event.width)
        self._stretch_all_trees()

    def _stretch_tree(self, tree: ttk.Treeview, prefix: str):
        cols = tree["columns"]
        if len(cols) < 2:
            return
        weights = self._column_weights.get(prefix)
        if not weights or len(weights) != len(cols):
            return
        tree.update_idletasks()
        total_w = tree.winfo_width()
        if total_w < 50:
            return
        margins = 5
        for col, w in zip(cols, weights):
            w = max(int((total_w - margins) * w / 100), 60)
            tree.column(col, width=w)

    def _stretch_all_trees(self):
        for section in self._sections:
            tree = section["tree"]
            prefix = section["prefix"]
            self._stretch_tree(tree, prefix)

    @staticmethod
    def _bind_mousewheel(canvas: tk.Canvas):
        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.focus_set()

    # ── helpers ───────────────────────────────────────────────

    @staticmethod
    def _format_hash(old_hash: str, new_hash: str) -> str:
        return f"{old_hash[:16]}… → {new_hash[:16]}…"

    # ── portada helpers ───────────────────────────────────────

    def _portada_status(self, item: Item) -> str:
        if not self.portadas_root:
            return "—"
        found = resolve_portada_file(
            self.portadas_root, item.destino,
            Path(item.nombre_legible).stem)
        if found:
            return f"🖼 {found.name}"
        return "—"

    @property
    def autocomplete_portadas(self) -> bool:
        return self._auto_portadas.get()

    # ── public accessors for app.py ─────────────────────────

    def get_selected_additions(self) -> List[Item]:
        return self._get_selected("new")

    def get_selected_removals(self) -> List[Item]:
        result = self._get_selected("missing")
        result.extend(self._get_selected("exc"))
        return result

    def get_selected_modified(self) -> List[ModifiedResult]:
        return self._get_selected("mod")

    def get_selected_renamed(self) -> List[RenameResult]:
        return self._get_selected("ren")

    def _get_selected(self, prefix: str) -> list:
        items = []
        for iid in self._checked:
            if iid.startswith(prefix + "_"):
                _, idx_str = iid.split("_", 1)
                idx = int(idx_str)
                if prefix == "new":
                    items.append(self.report.new_items[idx])
                elif prefix == "missing":
                    items.append(self.report.missing_items[idx])
                elif prefix == "mod":
                    items.append(self.report.modified_items[idx])
                elif prefix == "ren":
                    items.append(self.report.renamed_items[idx])
                elif prefix == "exc":
                    items.append(self.report.excluded_in_catalog[idx])
        return items
