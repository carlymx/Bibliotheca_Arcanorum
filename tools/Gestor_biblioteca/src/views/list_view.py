import fnmatch
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Set

from ..models import Item


class ListView(ttk.Frame):
    def __init__(
        self,
        parent,
        on_item_select: Callable[[List[Item]], None] = None,
        on_dir_select: Callable[[Optional[str]], None] = None,
        on_item_dropped: Callable[[List[Item], str], None] = None,
        on_visibility_changed: Callable[[], None] = None,
        on_export_request: Callable[[List[Item]], None] = None,
    ):
        super().__init__(parent)
        self.on_item_select = on_item_select
        self.on_dir_select = on_dir_select
        self.on_item_dropped = on_item_dropped
        self.on_visibility_changed = on_visibility_changed
        self.on_export_request = on_export_request

        self.items: List[Item] = []
        self.dir_visible: Dict[str, bool] = {}
        self._directorios: Set[str] = set()
        self._item_idx: Dict[str, int] = {}
        self._ignore_select = False
        self._drag_pending = False
        self._drag_active = False
        self._drag_item_iids: List[str] = []
        self._last_hover_node: Optional[str] = None
        self._click_node = None
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_changed)

        self._build_ui()

    # ── build ──────────────────────────────────────────────

    def _build_ui(self):
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", pady=(0, 4))

        ttk.Label(search_frame, text="🔍", font=("", 10)).pack(side="left", padx=(0, 4))
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(search_frame, text="✕", width=3, command=self._clear_search).pack(
            side="right", padx=(4, 0)
        )

        columns = ("portada", "mostrar")
        self.tree = ttk.Treeview(
            self, columns=columns, show="tree headings",
            selectmode="extended",
        )
        self.tree.heading("#0", text="Nombre")
        self.tree.heading("portada", text="Portada")
        self.tree.heading("mostrar", text="Mostrar")

        self.tree.column("#0", width=280, minwidth=150)
        self.tree.column("portada", width=60, minwidth=50, anchor="center", stretch=False)
        self.tree.column("mostrar", width=60, minwidth=50, anchor="center", stretch=False)

        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-1>", self._on_click, add="+")
        self.tree.bind("<B1-Motion>", self._on_motion, add="+")
        self.tree.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.tree.bind("<Leave>", self._on_leave, add="+")
        self.tree.bind("<Button-3>", self._on_context_menu, add="+")

        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(
            label="Exportar fichas seleccionadas",
            command=self._export_selected,
        )
        self._context_menu.add_command(
            label="Exportar directorio",
            command=self._export_dir,
        )
        self.tree.bind("<Button-1>", self._close_context_menu, add="+")

    # ── helpers ────────────────────────────────────────────

    def _item_iid(self, idx: int) -> str:
        return f"item_{idx}"

    def _get_item(self, iid: str) -> Optional[Item]:
        idx = self._item_idx.get(iid)
        if idx is not None and 0 <= idx < len(self.items):
            return self.items[idx]
        # Fallback: parse item_N
        if iid.startswith("item_"):
            try:
                idx = int(iid[5:])
                if 0 <= idx < len(self.items):
                    return self.items[idx]
            except ValueError:
                pass
        return None

    def _is_dir_node(self, node_id: str) -> bool:
        if node_id == "__root__":
            return True
        tags = self.tree.item(node_id, "tags")
        return "_dir" in tags

    def _is_item_node(self, node_id: str) -> bool:
        return node_id.startswith("item_")

    def _update_root_count(self):
        total = len(self.items)
        self.tree.item("__root__", text=f"📁 Raiz ({total})")

    # ── rebuild tree ───────────────────────────────────────

    def set_items(self, items: List[Item], dir_visible: dict = None,
                  directorios: set = None):
        self.items = items
        if dir_visible is not None:
            self.dir_visible = dir_visible
        if directorios is not None:
            self._directorios = directorios
        self.search_var.set("")
        self._rebuild_tree()

    def refresh(self):
        sel_iids = set(self.tree.selection())
        self._rebuild_tree()
        self._ignore_select = True
        new_sel = [iid for iid in sel_iids if self.tree.exists(iid)]
        if new_sel:
            self.tree.selection_set(new_sel)
            self.tree.focus(new_sel[0])
            self.tree.see(new_sel[0])
        self._ignore_select = False

    def _rebuild_tree(self, search_query: str = ""):
        self.tree.delete(*self.tree.get_children())
        self._item_idx.clear()

        total = len(self.items)
        self.tree.insert("", "end", iid="__root__",
                         text=f"📁 Raiz ({total})",
                         values=("", ""), tags=("_root",))
        self.tree.item("__root__", open=True)

        all_dirs: Set[str] = set()
        for item in self.items:
            if item.destino:
                parts = item.destino.rstrip("/").split("/")
                for i in range(len(parts)):
                    p = "/".join(parts[:i + 1])
                    all_dirs.add(p)
        all_dirs |= self._directorios

        if not all_dirs and not self.items:
            return

        dir_counts: Dict[str, int] = {}
        for item in self.items:
            if item.destino:
                parts = item.destino.rstrip("/").split("/")
                for i in range(len(parts)):
                    p = "/".join(parts[:i + 1])
                    dir_counts[p] = dir_counts.get(p, 0) + 1

        by_dir: Dict[str, List[int]] = {}
        for idx, item in enumerate(self.items):
            d = item.destino.rstrip("/") if item.destino else ""
            by_dir.setdefault(d, []).append(idx)

        tree_map: Dict[str, str] = {}

        if search_query:
            matching_dirs = self._dirs_with_matches(search_query)
            match_count = sum(1 for it in self.items if self._item_matches(it, search_query))
            self.tree.item("__root__", text=f"📁 Raiz ({match_count} coincidencias)")
            dirs_to_build = matching_dirs
        else:
            dirs_to_build = all_dirs

        for dir_path in sorted(dirs_to_build):
            if not dir_path:
                continue
            self._ensure_dir_nodes(dir_path, dir_counts, tree_map, all_dirs)

        for dir_path in sorted(dirs_to_build):
            if not dir_path:
                continue
            parent_id = tree_map.get(dir_path, "__root__")

            for idx in by_dir.get(dir_path, []):
                item = self.items[idx]
                portada_icon = "✅" if item.has_portada() else "⬜"
                oculto_icon = "⬜" if item.oculto else "✅"
                iid = self._item_iid(idx)
                self._item_idx[iid] = idx

                if search_query:
                    if not self._item_matches(item, search_query):
                        continue

                self.tree.insert(
                    parent_id, "end", iid=iid,
                    text=f"📄 {item.display_name()}",
                    values=(portada_icon, oculto_icon),
                    tags=("_item",),
                )

        # Render root-level items (sin destino)
        for idx in by_dir.get("", []):
            item = self.items[idx]
            portada_icon = "✅" if item.has_portada() else "⬜"
            oculto_icon = "⬜" if item.oculto else "✅"
            iid = self._item_iid(idx)
            self._item_idx[iid] = idx

            if search_query and not self._item_matches(item, search_query):
                continue

            self.tree.insert(
                "__root__", "end", iid=iid,
                text=f"📄 {item.display_name()}",
                values=(portada_icon, oculto_icon),
                tags=("_item",),
            )

        if search_query:
            for dir_path in matching_dirs:
                if dir_path and self.tree.exists(dir_path):
                    self.tree.item(dir_path, open=True)

    def _ensure_dir_nodes(self, dir_path: str, dir_counts: Dict[str, int],
                          tree_map: Dict[str, str],
                          all_dirs: Set[str] = None) -> str:
        parts = dir_path.split("/")
        parent_id = "__root__"
        for i, part in enumerate(parts):
            path = "/".join(parts[:i + 1])
            if path not in tree_map:
                visible = self.dir_visible.get(path, True)
                mostrar_icon = "✅" if visible else "⬜"
                n = dir_counts.get(path, 0)
                node_id = self.tree.insert(
                    parent_id, "end", iid=path,
                    text=f"{part} ({n})",
                    values=("", mostrar_icon),
                    tags=("_dir",),
                )
                tree_map[path] = node_id
            parent_id = tree_map[path]
        return parent_id

    def _item_matches(self, item: Item, query: str) -> bool:
        q = query.lower()
        if "*" in q or "?" in q:
            return (fnmatch.fnmatch(item.nombre_legible.lower(), q) or
                    fnmatch.fnmatch(item.tipo.lower(), q) or
                    fnmatch.fnmatch((item.destino or "").lower(), q))
        pat = f"*{q}*"
        return (fnmatch.fnmatch(item.nombre_legible.lower(), pat) or
                fnmatch.fnmatch(item.tipo.lower(), pat) or
                fnmatch.fnmatch((item.destino or "").lower(), pat))

    def _dirs_with_matches(self, query: str) -> Set[str]:
        dirs: Set[str] = set()
        for item in self.items:
            if self._item_matches(item, query) and item.destino:
                parts = item.destino.rstrip("/").split("/")
                for i in range(len(parts)):
                    dirs.add("/".join(parts[:i + 1]))
        return dirs

    # ── search ─────────────────────────────────────────────

    def _on_search_changed(self, *_):
        self._rebuild_tree(self.search_var.get().strip())

    def _clear_search(self):
        self.search_var.set("")

    # ── mostrar toggle ─────────────────────────────────────

    def _toggle_mostrar(self, node_id: str):
        tags = self.tree.item(node_id, "tags")
        if "_dir" in tags:
            current = self.dir_visible.get(node_id, True)
            self.dir_visible[node_id] = not current
            icon = "✅" if self.dir_visible[node_id] else "⬜"
            vals = list(self.tree.item(node_id, "values"))
            vals[1] = icon
            self.tree.item(node_id, values=vals)
        elif "_item" in tags:
            item = self._get_item(node_id)
            if item:
                item.oculto = not item.oculto
                icon = "⬜" if item.oculto else "✅"
                vals = list(self.tree.item(node_id, "values"))
                vals[1] = icon
                self.tree.item(node_id, values=vals)
        if self.on_visibility_changed:
            self.on_visibility_changed()

    # ── selection ──────────────────────────────────────────

    def _on_tree_select(self, event):
        if self._ignore_select:
            return
        selected_items = []
        selected_dirs = []
        for iid in self.tree.selection():
            if self._is_dir_node(iid) and iid != "__root__":
                selected_dirs.append(iid)
            item = self._get_item(iid)
            if item:
                selected_items.append(item)

        if selected_dirs and selected_items:
            # mixed selection not allowed — clear the newer selection
            self.tree.selection_remove([iid for iid in self.tree.selection()
                                        if iid.startswith("item_")])
            selected_items = []
            if self.on_dir_select:
                self.on_dir_select(selected_dirs[0] if len(selected_dirs) == 1 else None)
            return

        if selected_dirs and not selected_items:
            if self.on_dir_select:
                self.on_dir_select(selected_dirs[0] if len(selected_dirs) == 1 else None)
        else:
            if self.on_item_select:
                self.on_item_select(selected_items)

    def select_item(self, item: Item):
        for idx, it in enumerate(self.items):
            if it is item:
                iid = self._item_iid(idx)
                if self.tree.exists(iid):
                    self._ignore_select = True
                    self.tree.selection_set(iid)
                    self.tree.focus(iid)
                    self.tree.see(iid)
                    self._ignore_select = False
                break

    def get_selected_items(self) -> List[Item]:
        result = []
        for iid in self.tree.selection():
            item = self._get_item(iid)
            if item:
                result.append(item)
        return result

    def get_selected_dirs(self) -> List[str]:
        result = []
        for iid in self.tree.selection():
            if self._is_dir_node(iid) and iid != "__root__":
                result.append(iid)
        return result

    # ── drag & drop ────────────────────────────────────────

    def _on_click(self, event):
        col = self.tree.identify_column(event.x)
        node = self.tree.identify_row(event.y)

        if col == "#2" and node:
            self._toggle_mostrar(node)
            self._ignore_select = True
            self.tree.selection_remove(node)
            self._ignore_select = False
            return "break"

        if node and node.startswith("item_"):
            self._drag_pending = True
            self._drag_start_y = event.y
            self._click_node = node
            sel = self.tree.selection()
            ctrl_or_shift = event.state & (0x0001 | 0x0004)
            if len(sel) >= 2 and node in sel and not ctrl_or_shift:
                return "break"

    def _on_motion(self, event):
        if self._drag_pending:
            if abs(event.y - self._drag_start_y) > 6:
                sel = self.tree.selection()
                self._drag_item_iids = [
                    iid for iid in sel if iid.startswith("item_")
                ]
                if not self._drag_item_iids:
                    self._drag_pending = False
                    return
                self._drag_active = True
                self._drag_pending = False
                self.tree.configure(cursor="fleur")

        if self._drag_active:
            node = self.tree.identify_row(event.y)
            if node != self._last_hover_node:
                self._clear_drag_hover()
                if node and node != "__root__" and self._is_dir_node(node):
                    self.tree.tag_configure("_drag_hover", background="#d0e4f5")
                    tags = list(self.tree.item(node, "tags"))
                    if "_drag_hover" not in tags:
                        tags.append("_drag_hover")
                    self.tree.item(node, tags=tags)
                    self._last_hover_node = node

    def _on_release(self, event):
        if self._drag_active:
            self.tree.configure(cursor="")
            self._clear_drag_hover()
            node = self.tree.identify_row(event.y)
            if node and node != "__root__" and self._is_dir_node(node):
                new_destino = node.rstrip("/") + "/"
                items = [self._get_item(iid) for iid in self._drag_item_iids]
                items = [i for i in items if i is not None]
                if items and self.on_item_dropped:
                    self.on_item_dropped(items, new_destino)
            self._drag_active = False
            self._drag_pending = False
            self._drag_item_iids = []
            return

        self._drag_pending = False

        if event.state & (0x0001 | 0x0004):
            return

        node = self._click_node
        if node and node.startswith("item_"):
            sel = self.tree.selection()
            if len(sel) >= 2 and node in sel:
                self.tree.selection_set(node)
                self.tree.focus(node)

    def _on_leave(self, event):
        if self._drag_active:
            self._clear_drag_hover()

    def _clear_drag_hover(self):
        if self._last_hover_node:
            try:
                tags = list(self.tree.item(self._last_hover_node, "tags"))
                if "_drag_hover" in tags:
                    tags.remove("_drag_hover")
                self.tree.item(self._last_hover_node, tags=tags)
            except tk.TclError:
                pass
            self._last_hover_node = None

    # ── context menu ─────────────────────────────────────

    def _close_context_menu(self, event=None):
        try:
            self._context_menu.unpost()
        except tk.TclError:
            pass

    def _on_context_menu(self, event):
        node = self.tree.identify_row(event.y)
        if not node:
            return
        self._context_node = node
        self._context_items = []
        self._context_dir = None

        if self._is_item_node(node):
            self._context_items = self.get_selected_items()
            self._context_menu.entryconfigure("Exportar directorio", state="disabled")
            state = "normal" if self._context_items else "disabled"
            self._context_menu.entryconfigure("Exportar fichas seleccionadas", state=state)
        elif self._is_dir_node(node) and node != "__root__":
            self._context_dir = node
            sel_dirs = [n for n in self.tree.selection()
                        if self._is_dir_node(n) and n != "__root__"]
            if node not in sel_dirs:
                sel_dirs = [node]
            dir_items = []
            for nd in sel_dirs:
                nd_stripped = nd.rstrip("/")
                for it in self.items:
                    if not it.destino:
                        continue
                    d = it.destino.rstrip("/")
                    if d == nd_stripped or d.startswith(nd_stripped + "/"):
                        if it not in dir_items:
                            dir_items.append(it)
            self._context_items = dir_items
            state = "normal" if dir_items else "disabled"
            self._context_menu.entryconfigure("Exportar directorio", state=state)
            self._context_menu.entryconfigure("Exportar fichas seleccionadas", state="disabled")
        else:
            self._context_menu.entryconfigure("Exportar directorio", state="disabled")
            self._context_menu.entryconfigure("Exportar fichas seleccionadas", state="disabled")

        self._context_menu.post(event.x_root, event.y_root)

    def _export_selected(self):
        if self.on_export_request and self._context_items:
            self.on_export_request(self._context_items)

    def _export_dir(self):
        if self.on_export_request and self._context_items:
            self.on_export_request(self._context_items)
