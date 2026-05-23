import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Dict, List, Optional, Set

from .models import Item
from .portada_mgr import make_web_path


class PortadaSearchDialog(tk.Toplevel):
    def __init__(self, parent, results: Dict[str, list], portadas_root: str, web_root: str = ""):
        super().__init__(parent)
        self.results = results
        self.portadas_root = portadas_root
        self.web_root = web_root
        self.result: Optional[str] = None

        self._checked: Set[int] = set()

        self.title("Buscar portadas — Resultados")
        self.geometry("950x600")
        self.minsize(750, 400)
        self.transient(parent)
        self.grab_set()

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
        ttk.Entry(top, textvariable=self.search_var).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )

        ttk.Button(top, text="☐ Sel. todos", command=self._select_all).pack(
            side="left", padx=2
        )
        ttk.Button(top, text="☐ Ninguno", command=self._select_none).pack(
            side="left", padx=2
        )

        # ── tree frame ───────────────────────────────────────

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=8)

        columns = ["☐", "Item", "Destino", "Estado", "Portada encontrada"]
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)

        self.tree.heading("☐", text="☐")
        self.tree.column("☐", width=30, minwidth=24, anchor="center", stretch=False)
        self.tree.heading("Item", text="Item", command=lambda: self._sort_tree("Item"))
        self.tree.column("Item", width=200, minwidth=120)
        self.tree.heading("Destino", text="Destino", command=lambda: self._sort_tree("Destino"))
        self.tree.column("Destino", width=150, minwidth=100)
        self.tree.heading("Estado", text="Estado", command=lambda: self._sort_tree("Estado"))
        self.tree.column("Estado", width=140, minwidth=100, anchor="center")
        self.tree.heading("Portada encontrada", text="Portada encontrada",
                          command=lambda: self._sort_tree("Portada encontrada"))
        self.tree.column("Portada encontrada", width=320, minwidth=180)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)

        # ── bottom bar ───────────────────────────────────────

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=8, pady=(0, 8))

        self.summary_var = tk.StringVar()
        ttk.Label(bottom, textvariable=self.summary_var, font=("", 10, "bold")).pack(
            side="left", padx=4
        )

        ttk.Button(bottom, text="Aplicar correcciones",
                   command=self._on_apply, width=20).pack(side="right", padx=2)
        ttk.Button(bottom, text="Cancelar",
                   command=self._on_cancel, width=12).pack(side="right", padx=2)

    # ── populate ────────────────────────────────────────────

    def _populate(self):
        self._flat: List[dict] = []
        self._checked.clear()

        for item, abs_path, rel_dir in self.results.get("exact", []):
            filename = Path(abs_path).name
            display = f"{rel_dir}/{filename}" if rel_dir else filename
            row = {
                "item": item,
                "status": "exact",
                "display_path": display,
                "abs_path": abs_path,
                "rel_dir": rel_dir,
            }
            idx = len(self._flat)
            self._flat.append(row)
            self._checked.add(idx)

        for item, abs_path, rel_dir, orig in self.results.get("fuzzy", []):
            filename = Path(abs_path).name
            display = f"{rel_dir}/{filename}" if rel_dir else filename
            display += f"  (era: {orig})"
            row = {
                "item": item,
                "status": "fuzzy",
                "display_path": display,
                "abs_path": abs_path,
                "rel_dir": rel_dir,
            }
            idx = len(self._flat)
            self._flat.append(row)
            self._checked.add(idx)

        for item in self.results.get("not_found", []):
            row = {
                "item": item,
                "status": "not_found",
                "display_path": "—",
                "abs_path": None,
                "rel_dir": None,
            }
            idx = len(self._flat)
            self._flat.append(row)

        self._rebuild_tree()

    def _rebuild_tree(self):
        self.tree.delete(*self.tree.get_children())
        for idx, row in enumerate(self._flat):
            item = row["item"]
            status = row["status"]
            estado = {
                "exact": "🔍 Exacta",
                "fuzzy": "🔎 Aproximada",
                "not_found": "✖ No encontrada",
            }[status]
            chk = "☑" if idx in self._checked else "☐"
            self.tree.insert("", "end", iid=str(idx), values=(
                chk, item.nombre_legible, item.destino, estado, row["display_path"],
            ))

    # ── checkbox toggle ─────────────────────────────────────

    def _on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        if col != "#1":
            return
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        idx = int(iid)
        row = self._flat[idx]
        if row["status"] == "not_found":
            return
        if idx in self._checked:
            self._checked.discard(idx)
        else:
            self._checked.add(idx)
        self._rebuild_tree()
        self._update_summary()

    # ── select all / none ───────────────────────────────────

    def _select_all(self):
        for idx, row in enumerate(self._flat):
            if row["status"] != "not_found":
                self._checked.add(idx)
        self._rebuild_tree()
        self._update_summary()

    def _select_none(self):
        self._checked.clear()
        self._rebuild_tree()
        self._update_summary()

    # ── summary ─────────────────────────────────────────────

    def _update_summary(self):
        ok_count = len(self.results.get("ok", []))
        exact_count = len(self.results.get("exact", []))
        fuzzy_count = len(self.results.get("fuzzy", []))
        nf_count = len(self.results.get("not_found", []))
        checked = len(self._checked)

        self.summary_var.set(
            f"📊 {ok_count} correctas  |  "
            f"{exact_count} exactas  |  "
            f"{fuzzy_count} aproximadas  |  "
            f"{nf_count} sin portada  —  "
            f"Aplicar: {checked}"
        )

    # ── filter ──────────────────────────────────────────────

    def _filter(self):
        query = self.search_var.get().lower()
        for child in self.tree.get_children():
            vals = self.tree.item(child, "values")
            text = " ".join(str(v) for v in vals).lower()
            if not query or query in text:
                self.tree.reattach(child, "", "end")
            else:
                self.tree.detach(child)

    # ── sort ────────────────────────────────────────────────

    def _sort_tree(self, col: str):
        cols = self.tree["columns"]
        col_idx = cols.index(col) if col in cols else 0
        items = [(self.tree.item(iid, "values"), iid) for iid in self.tree.get_children("")]
        items.sort(key=lambda x: str(x[0][col_idx]).lower() if col_idx < len(x[0]) else "")
        for pos, (_, iid) in enumerate(items):
            self.tree.move(iid, "", pos)

    # ── apply / cancel ──────────────────────────────────────

    def _on_apply(self):
        self.result = "apply"
        self.destroy()

    def _on_cancel(self):
        if self._checked:
            from tkinter import messagebox
            resp = messagebox.askyesno(
                "Descartar correcciones",
                "Hay correcciones seleccionadas. ¿Descartarlas?",
                parent=self,
            )
            if not resp:
                return
        self.result = None
        self.destroy()

    # ── public accessor for app.py ──────────────────────────

    def get_selected_corrections(self) -> List[tuple]:
        corrections = []
        for idx in self._checked:
            row = self._flat[idx]
            item = row["item"]
            if row["abs_path"]:
                portada = make_web_path(row["rel_dir"], Path(row["abs_path"]).name, self.portadas_root, self.web_root)
                corrections.append((item, portada))
        return corrections
