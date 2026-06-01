import os
import json
import shutil
import urllib.request
import tkinter as tk
from tkinter import simpledialog, ttk, filedialog, messagebox
from pathlib import Path
from typing import List, Optional
import threading

import sv_ttk

from .models import Item, ModifiedResult, RenameResult
from .catalog import load, save, save_catalogo_js
from .scanner import Scanner
from .scan_dialog import ScanReviewDialog
from .portada_search_dialog import PortadaSearchDialog
from .portada_mgr import (build_portada_index, find_missing_portadas,
                           resolve_portada_file, move_item, move_portada)
from .utils.tooltip import ToolTip, make_btn, refresh_icons
from .portadas_extract_dialog import PortadasExtractDialog
from .path_setup_dialog import PathSetupDialog
from .export_dialog import ExportDialog
from .import_dialog import ImportDialog
from .io_pack import BibliotexError
from .settings_view import DEFAULT_CONFIG, SettingsView, load_config, save_config
from .views.list_view import ListView
from .views.detail_view import DetailView
from .views.help_view import HelpView
from .delete_dialog import DeleteItemDialog, DeleteDirDialog, DeleteDirResult
from .update_dialog import UpdateCheckerDialog, urlopen_with_fallback, parse_version


VERSION = "0.9.7"


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"Gestor de Bibliotecas v{VERSION}")
        self.root.geometry("1400x910")
        self.root.minsize(1000, 600)

        self.style = ttk.Style(self.root)
        self.items: List[Item] = []
        self.dir_visible: dict = {}
        self.directorios: set = set()
        self.json_path: Optional[str] = None
        self.nombre_biblioteca: str = ""
        self.url_base: str = ""
        self.config = load_config()

        self._clean_library_paths_from_config()
        save_config(self.config)

        self.root.tk.eval('catch {set ::tk::dialog::file::initWidth 70}')
        self.root.tk.eval('catch {set ::tk::dialog::file::initHeight 30}')

        self._apply_theme(self.config.get("theme", "default"))
        self._dirty: bool = False

        self._scan_progress: Optional[tk.Toplevel] = None
        self._scan_cancel_event = threading.Event()

        self._build_menu()
        self._build_body()

        self.root.bind("<Control-o>", lambda e: self.open_json())
        self.root.bind("<Control-s>", lambda e: self.save())
        self.root.bind("<Control-n>", lambda e: self.add_item())
        self.root.bind("<Control-Shift-n>", lambda e: self.nuevo_catalogo())
        self.root.bind("<Control-b>", lambda e: self.buscar_cambios())
        self.root.bind("<Control-Shift-e>", lambda e: self._export_items())
        self.root.bind("<Control-Shift-i>", lambda e: self._import_items())

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._update_status()
        self.root.after(1500, lambda: self._check_for_updates(silent=True))

    # ── build ──────────────────────────────────────────────

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Nuevo catálogo", command=self.nuevo_catalogo, accelerator="Ctrl+Shift+N")
        file_menu.add_command(label="Abrir biblioteca...", command=self.open_json, accelerator="Ctrl+O")
        self._recent_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_cascade(label="Bibliotecas recientes", menu=self._recent_menu)
        file_menu.add_separator()
        file_menu.add_command(label="Guardar", command=self.save, accelerator="Ctrl+S")
        file_menu.add_command(label="Guardar como...", command=self.save_as)
        file_menu.add_command(label="Cerrar catálogo", command=self.cerrar_catalogo)
        file_menu.add_separator()
        file_menu.add_command(label="Exportar fichas...", command=self._export_items, accelerator="Ctrl+Shift+E")
        file_menu.add_command(label="Importar fichas...", command=self._import_items, accelerator="Ctrl+Shift+I")
        file_menu.add_separator()
        file_menu.add_command(label="Exportar para la web", command=self._export_for_web)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="Archivo", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Buscar cambios", command=self.buscar_cambios, accelerator="Ctrl+B")

        portadas_menu = tk.Menu(tools_menu, tearoff=0)
        portadas_menu.add_command(label="Buscar portadas", command=self.buscar_portadas)
        portadas_menu.add_command(label="Extraer portadas", command=self._extraer_portadas)
        tools_menu.add_cascade(label="Portadas", menu=portadas_menu)

        directorios_menu = tk.Menu(tools_menu, tearoff=0)
        directorios_menu.add_command(label="Añadir directorio", command=self._nuevo_directorio)
        directorios_menu.add_command(label="Eliminar directorio", command=self._delete_dir_menu)
        tools_menu.add_cascade(label="Directorios", menu=directorios_menu)

        fichas_menu = tk.Menu(tools_menu, tearoff=0)
        fichas_menu.add_command(label="Añadir ficha", command=self.add_item, accelerator="Ctrl+N")
        fichas_menu.add_command(label="Eliminar ficha", command=self.delete_item)
        tools_menu.add_cascade(label="Fichas", menu=fichas_menu)

        menubar.add_cascade(label="Herramientas", menu=tools_menu)

        self._about_menu = tk.Menu(menubar, tearoff=0)
        self._about_menu.add_command(label="Acerca de...", command=self._about)
        self._about_menu.add_separator()
        self._about_menu.add_command(label="Buscar actualizaciones...", command=lambda: self._check_for_updates(silent=False))
        menubar.add_cascade(label="?", menu=self._about_menu)

        self._update_recent_libraries_menu()

    def _build_body(self):
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_rowconfigure(2, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

        # ── toolbar ──
        self.toolbar = ttk.Frame(self.root)
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=2, pady=2)

        make_btn(self.toolbar, "📝", self.nuevo_catalogo, "Nuevo catálogo (Ctrl+Shift+N)")
        make_btn(self.toolbar, "📂", self.open_json, "Abrir biblioteca (Ctrl+O)")
        make_btn(self.toolbar, "💾", self.save, "Guardar catálogo (Ctrl+S)")
        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", fill="y", padx=4)
        make_btn(self.toolbar, "➕", self.add_item, "Añadir ficha (Ctrl+N)")
        make_btn(self.toolbar, "🗑️", self.delete_item, "Eliminar ficha seleccionada")
        ttk.Separator(self.toolbar, orient="vertical").pack(side="left", fill="y", padx=4)
        make_btn(self.toolbar, "📁", self._nuevo_directorio, "Nuevo directorio")
        make_btn(self.toolbar, "🚫", self._delete_dir_menu, "Eliminar directorio")

        # ── spacer + update label (right side) ──
        spacer = ttk.Frame(self.toolbar)
        spacer.pack(side="left", fill="x", expand=True)
        self._update_url = ""
        self._update_label = ttk.Label(self.toolbar, foreground="green", cursor="hand2")
        self._update_label.pack(side="left", padx=(0, 8))
        self._update_label.bind("<Button-1>", lambda e: self._open_update_url())

        # ── notebook ──
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))

        library_frame = ttk.Frame(self.notebook)
        self.notebook.add(library_frame, text="Biblioteca")

        paned = ttk.PanedWindow(library_frame, orient="horizontal")
        paned.pack(fill="both", expand=True)

        self.list_view = ListView(
            paned,
            on_item_select=self._on_item_selected,
            on_dir_select=self._on_dir_selected,
            on_item_dropped=self._on_item_dropped,
            on_dir_dropped=self._on_dir_dropped,
            on_visibility_changed=self._mark_dirty,
            on_export_request=self._export_items,
        )
        paned.add(self.list_view, weight=1)

        self.detail_view = DetailView(paned, on_item_changed=self._on_item_changed)
        paned.add(self.detail_view, weight=1)
        self.detail_view.set_library_root(self.config.get("library_root", ""))

        self.settings_view = SettingsView(
            self.notebook,
            on_config_saved=self._on_config_saved,
        )
        self.notebook.add(self.settings_view, text="Configuración")

        self.help_view = HelpView(self.notebook)
        self.notebook.add(self.help_view, text="Ayuda")

        # ── status bar ──
        self.status_frame = ttk.Frame(self.root, relief="sunken")
        self.status_frame.grid(row=2, column=0, sticky="ew")

        self.status_msg = ttk.Label(self.status_frame, text="Listo", anchor="w")
        self.status_msg.pack(side="left", fill="x", expand=True, padx=4)

        self._dirty_indicator = tk.Label(self.status_frame, text="", font=("", 9))
        self._dirty_indicator.pack(side="right", padx=(0, 6))

        self.status_counts = ttk.Label(self.status_frame, text="", anchor="e", font=("", 9))
        self.status_counts.pack(side="right", padx=4)

    # ── backup ─────────────────────────────────────────────

    def _create_backup(self, filepath: str):
        count = self.config.get("backup_count", 2)
        if count <= 0:
            return

        src = Path(filepath)
        if not src.exists():
            return

        stem = src.stem
        ext = src.suffix
        parent = src.parent

        oldest = parent / f"{stem}_bak{count}{ext}"
        oldest.unlink(missing_ok=True)

        for i in range(count - 1, 1, -1):
            old_file = parent / f"{stem}_bak{i}{ext}"
            new_file = parent / f"{stem}_bak{i + 1}{ext}"
            if old_file.exists():
                old_file.rename(new_file)

        if count >= 2:
            first_bak = parent / f"{stem}_bak{ext}"
            second_bak = parent / f"{stem}_bak2{ext}"
            if first_bak.exists():
                first_bak.rename(second_bak)

        shutil.copy2(str(src), str(parent / f"{stem}_bak{ext}"))

    @staticmethod
    def _lib_path_keys():
        return ("library_root", "portadas_root", "web_root", "catalogo_js_path",
                "nombre_biblioteca", "url_base")

    def _clean_library_paths_from_config(self):
        for key in self._lib_path_keys():
            self.config.pop(key, None)

    def _apply_metadata_to_config(self, metadata: dict):
        for key in ("library_root", "portadas_root", "web_root", "catalogo_js_path",
                     "nombre_biblioteca", "url_base"):
            val = metadata.get(key, "")
            if val:
                self.config[key] = val

    def _ensure_paths(self, required=("library_root",)) -> bool:
        missing = [k for k in required if not self.config.get(k)]
        if not missing:
            return True

        dlg = PathSetupDialog(self.root, required=required)
        if dlg.result is None:
            return False

        self.config.update(dlg.result)
        save_config(self.config)
        self.settings_view.set_fields_from_config(self.config)
        self.detail_view.set_web_root(self.config.get("web_root", ""))
        self.detail_view.set_portadas_root(self.config.get("portadas_root", ""))
        self.detail_view.set_library_root(self.config.get("library_root", ""))
        return True

    # ── actions ────────────────────────────────────────────

    def open_json(self, path: Optional[str] = None):
        if not path:
            initial = self.config.get("last_json", "")
            path = filedialog.askopenfilename(
                title="Abrir JSON del catálogo",
                initialdir=str(Path(initial).parent) if initial else "",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            )
            if not path:
                return

        self._create_backup(path)

        try:
            self.items, self.dir_visible, self.directorios, metadata = load(path)
            self.json_path = path
            self.nombre_biblioteca = metadata.get("nombre_biblioteca", "Biblioteca sin nombre")
            self.url_base = metadata.get("url_base", "")
            self._apply_metadata_to_config(metadata)
            self.config["last_json"] = path
            recents = self.config.get("recent_libraries", [])
            if path in recents:
                recents.remove(path)
            recents.insert(0, path)
            self.config["recent_libraries"] = recents[:10]
            save_config(self.config)
            self._update_recent_libraries_menu()
            self._clear_dirty()
            self.list_view.set_items(self.items, self.dir_visible, self.directorios)
            self.detail_view.set_web_root(self.config.get("web_root", ""))
            self.detail_view.set_portadas_root(self.config.get("portadas_root", ""))
            self.detail_view.set_library_root(self.config.get("library_root", ""))
            self.settings_view.set_fields_from_config(self.config)
            self._update_status()
            self.status_msg.config(text=f"Cargados {len(self.items)} items de {path}")
        except Exception as e:
            messagebox.showerror("Error al cargar", str(e))

    def save(self):
        if not self.items:
            messagebox.showinfo("Sin datos", "No hay items para guardar.")
            return
        if not self.json_path:
            self.save_as()
            return

        self._collect_directorios()
        try:
            nb = self.nombre_biblioteca or self.config.get("nombre_biblioteca", "")
            save(self.items, self.json_path, self.dir_visible, self.directorios,
                 nombre_biblioteca=nb, url_base=self.url_base,
                 library_root=self.config.get("library_root", ""),
                 portadas_root=self.config.get("portadas_root", ""),
                 web_root=self.config.get("web_root", ""),
                 catalogo_js_path=self.config.get("catalogo_js_path", ""))
            self._clear_dirty()
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))

    def _export_for_web(self):
        cfg = self.settings_view.get_config()
        js_path = cfg.get("catalogo_js_path", "") or self.config.get("catalogo_js_path", "")
        if not js_path:
            js_path = filedialog.asksaveasfilename(
                title="Guardar catalogo.js como...",
                defaultextension=".js",
                filetypes=[("JavaScript files", "*.js")],
            )
            if not js_path:
                return

        library_root = self.config.get("library_root", "")
        web_root = self.config.get("web_root", "")
        url_base = ""
        if library_root and web_root:
            try:
                url_base = os.path.relpath(library_root, web_root)
            except ValueError:
                url_base = ""

        nb = self.nombre_biblioteca or self.config.get("nombre_biblioteca", "")
        self._save_for_web(js_path, nombre_biblioteca=nb, url_base=url_base)

    def _save_for_web(self, js_path: str, nombre_biblioteca: str = "",
                      url_base: str = ""):
        if not self.items:
            messagebox.showinfo("Sin datos", "No hay items para guardar.")
            return
        try:
            save_catalogo_js(self.items, js_path, self.dir_visible,
                             nombre_biblioteca=nombre_biblioteca, url_base=url_base)
            messagebox.showinfo("Éxito", f"Catálogo guardado para la web en:\n{js_path}")
            self.status_msg.config(text="Guardado catalogo.js para la web", foreground="green")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")

    def _export_items(self, items: Optional[list[Item]] = None):
        if items is None:
            items = self.items
        if not items:
            messagebox.showinfo("Exportar", "No hay fichas para exportar.")
            return

        ExportDialog(
            self.root,
            items=items,
            config=self.config,
            on_export_done=lambda path: self.status_msg.config(
                text=f"Exportadas {len(items)} fichas a {path}"
            ),
        )

    def _import_items(self, filepath: str = ""):
        ImportDialog(
            self.root,
            existing_items=self.items,
            config=self.config,
            on_import_done=self._on_import_complete,
            initial_path=filepath,
        )

    def _on_import_complete(self, result):
        parts = []
        if result.importados:
            self.items.extend(result.importados)
            parts.append(f"+{len(result.importados)} importados")
        if result.sobrescritos:
            parts.append(f"~{len(result.sobrescritos)} sobrescritos")
        if result.saltados:
            parts.append(f"-{len(result.saltados)} saltados")
        if result.pdfs_faltantes:
            parts.append(f"⚠ {len(result.pdfs_faltantes)} PDFs faltantes")
        self.list_view.set_items(self.items, self.dir_visible, self.directorios)
        self._mark_dirty()
        self._update_status()
        self.status_msg.config(text="Importación: " + (", ".join(parts) if parts else "Sin cambios"))

    def save_as(self):
        path = filedialog.asksaveasfilename(
            title="Guardar JSON como...",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        self.json_path = path
        self.config["last_json"] = path
        save_config(self.config)
        self.save()

    def add_item(self):
        item = Item()
        item.nombre_legible = "Ficha Nueva"
        selected_dirs = self.list_view.get_selected_dirs()
        if selected_dirs:
            item.destino = selected_dirs[0].rstrip("/") + "/"
        self.items.append(item)
        self.list_view.set_items(self.items, self.dir_visible, self.directorios)
        self.list_view.select_item(item)
        self._on_item_selected([item])
        self._mark_dirty()
        self._update_status()
        self.status_msg.config(text=f"Añadida ficha vacía. Total: {len(self.items)} items")

    def delete_item(self):
        selected = self.list_view.get_selected_items()
        if not selected:
            messagebox.showinfo("Eliminar", "Selecciona una o varias fichas primero.")
            return

        item_defaults = self.config.get("delete_defaults", {}).get("item", {})
        dialog = DeleteItemDialog(self.root, len(selected), item_defaults)
        result = dialog.result
        if result is None:
            return

        library_root = self.config.get("library_root", "")
        portadas_root = self.config.get("portadas_root", "")

        for item in selected:
            if result.borrar_pdf and item.nombre_legible and library_root and item.destino:
                pdf_path = Path(library_root) / item.destino.rstrip("/") / item.nombre_legible
                if pdf_path.exists():
                    pdf_path.unlink()

            if result.borrar_portada and portadas_root and item.nombre_legible:
                portada_path = resolve_portada_file(
                    portadas_root, item.destino, Path(item.nombre_legible).stem)
                if portada_path and portada_path.exists():
                    portada_path.unlink()
                    item.portada = ""

            if item in self.items:
                self.items.remove(item)

        if result.guardar_default:
            self.config.setdefault("delete_defaults", {})
            self.config["delete_defaults"]["item"] = {
                "borrar_pdf": result.borrar_pdf,
                "borrar_portada": result.borrar_portada,
            }
            save_config(self.config)

        self.list_view.set_items(self.items, self.dir_visible, self.directorios)
        self.detail_view.load_items([])
        self._mark_dirty()
        self._update_status()
        self.status_msg.config(
            text=f"{len(selected)} ficha(s) eliminada(s). Total: {len(self.items)} items"
        )

    def _run_scan(self, library_root, existing_items, on_complete_cb):
        self._scan_cancel_event.clear()
        win = tk.Toplevel(self.root)
        self._scan_progress = win
        win.title("Buscando cambios...")
        win.geometry("400x170")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        ttk.Label(win, text="Escaneando biblioteca...", font=("", 11)).pack(pady=10)
        self._scan_progress_label = ttk.Label(win, text="Iniciando...")
        self._scan_progress_label.pack()
        self._scan_progress_bar = ttk.Progressbar(win, mode="indeterminate")
        self._scan_progress_bar.pack(fill="x", padx=20, pady=10)
        self._scan_progress_bar.start()

        cancel_btn = ttk.Button(win, text="Cancelar",
                                command=self._cancel_scan)
        cancel_btn.pack(pady=(0, 6))

        def progress_cb(msg):
            self.root.after(0, lambda: self._scan_progress_label.config(text=msg))

        def scan_thread():
            try:
                exclude = self.config.get("scan_exclude") or DEFAULT_CONFIG.get("scan_exclude", [])
                scanner = Scanner(library_root, existing_items, scan_exclude=exclude,
                                  cancel_event=self._scan_cancel_event)
                report = scanner.scan(progress_callback=progress_cb)
                if report is None:
                    self.root.after(0, self._scan_cleanup)
                else:
                    self.root.after(0, lambda: on_complete_cb(report))
            except Exception as e:
                self.root.after(0, lambda: self._scan_error(str(e)))

        win.protocol("WM_DELETE_WINDOW", self._cancel_scan)
        threading.Thread(target=scan_thread, daemon=True).start()

    def _cancel_scan(self):
        self._scan_cancel_event.set()
        self._scan_cleanup()
        self.status_msg.config(text="Escaneo: cancelado")

    def _scan_cleanup(self):
        if self._scan_progress:
            self._scan_progress.destroy()
            self._scan_progress = None

    def buscar_cambios(self):
        if not self._ensure_paths(("library_root",)):
            return
        library_root = self.config["library_root"]
        if not Path(library_root).exists():
            messagebox.showerror("Error", f"La ruta de biblioteca no existe:\n{library_root}")
            return
        if not self.items:
            messagebox.showinfo("Sin datos", "Abre un JSON del catálogo antes de buscar cambios.")
            return

        self._run_scan(library_root, self.items, self._scan_complete)

    def _scan_complete(self, report):
        self._scan_cleanup()

        if report.total_changes == 0:
            messagebox.showinfo("Escaneo completo",
                                "El catálogo está al día. No hay cambios.")
            self.status_msg.config(text="Escaneo: sin cambios")
            return

        portadas_root = self.config.get("portadas_root", "")
        dialog = ScanReviewDialog(self.root, report, portadas_root=portadas_root)
        dialog.wait_window()

        if dialog.result != "apply":
            self.status_msg.config(text="Escaneo: cambios descartados")
            return

        added = dialog.get_selected_additions()
        removed = dialog.get_selected_removals()
        modified = dialog.get_selected_modified()

        if added:
            if dialog.autocomplete_portadas and portadas_root:
                web_root = self.config.get("web_root", "")
                if web_root:
                    for item in added:
                        found = resolve_portada_file(
                            portadas_root, item.destino,
                            Path(item.nombre_legible).stem)
                        if found:
                            item.portada = os.path.relpath(str(found), web_root)
            self.items.extend(added)

        if removed:
            for item in removed:
                if item in self.items:
                    self.items.remove(item)

        if modified:
            for mod in modified:
                mod.item.archivo_hash = mod.new_hash
                mod.item.peso = mod.new_size

        renamed = dialog.get_selected_renamed()
        for ren in renamed:
            ren.item.nombre_legible = ren.new_name
            ren.item.destino = ren.new_destino
            ren.item.archivo_hash = ren.new_hash
            ren.item.peso = ren.new_size

        self.list_view.set_items(self.items, self.dir_visible, self.directorios)
        self.detail_view.load_items([])
        self._mark_dirty()
        self._update_status()

        parts = []
        if added:
            parts.append(f"+{len(added)} añadidos")
        if removed:
            parts.append(f"-{len(removed)} eliminados")
        if modified:
            parts.append(f"~{len(modified)} actualizados")
        if renamed:
            parts.append(f"~{len(renamed)} renombrados")
        self.status_msg.config(text="Escaneo: " + ", ".join(parts))

    def _scan_error(self, error_msg):
        self._scan_cleanup()
        messagebox.showerror("Error de escaneo", error_msg)

    # ── nuevo catálogo desde cero ────────────────────────────

    def nuevo_catalogo(self):
        if self._dirty or self.detail_view.is_dirty():
            resp = messagebox.askyesno(
                "Cambios sin guardar",
                "Hay cambios sin guardar. ¿Descartarlos y empezar un nuevo catálogo?",
            )
            if not resp:
                return

        if not self._ensure_paths(("library_root", "portadas_root", "web_root",
                                    "nombre_biblioteca")):
            return

        self.nombre_biblioteca = self.config.get("nombre_biblioteca", "")
        library_root = self.config["library_root"]
        if not Path(library_root).exists():
            messagebox.showerror("Error", f"La ruta de biblioteca no existe:\n{library_root}")
            return

        self._run_scan(library_root, [], self._scan_complete_new_catalog)

    def _scan_complete_new_catalog(self, report):
        self._scan_cleanup()

        if report.total_changes == 0:
            messagebox.showinfo(
                "Nuevo catálogo",
                "La biblioteca está vacía. No hay archivos que añadir.",
            )
            self.status_msg.config(text="Nuevo catálogo: biblioteca vacía")
            return

        portadas_root = self.config.get("portadas_root", "")
        dialog = ScanReviewDialog(self.root, report, portadas_root=portadas_root)
        dialog.wait_window()

        if dialog.result != "apply":
            self.status_msg.config(text="Nuevo catálogo: cancelado")
            return

        added = dialog.get_selected_additions()
        if not added:
            messagebox.showinfo("Nuevo catálogo", "No se seleccionaron archivos.")
            return

        self.items = []
        self.dir_visible = {}
        self.directorios = set()
        self.json_path = None

        if dialog.autocomplete_portadas and portadas_root:
            web_root = self.config.get("web_root", "")
            if web_root:
                for item in added:
                    found = resolve_portada_file(
                        portadas_root, item.destino,
                        Path(item.nombre_legible).stem)
                    if found:
                        item.portada = os.path.relpath(str(found), web_root)

        self.items.extend(added)
        self.list_view.set_items(self.items, self.dir_visible, self.directorios)
        self.detail_view.load_items([])
        self._mark_dirty()
        self._update_status()

        self.status_msg.config(
            text=f"Nuevo catálogo: {len(self.items)} fichas creadas. Guarda el archivo."
        )

        self.save_as()

    # ── cerrar catálogo ─────────────────────────────────────

    def cerrar_catalogo(self):
        if not self.items and not self.json_path:
            messagebox.showinfo(
                "Cerrar catálogo",
                "No hay ningún catálogo abierto.",
            )
            return

        if self._dirty or self.detail_view.is_dirty():
            resp = messagebox.askyesnocancel(
                "Cambios sin guardar",
                "Hay cambios sin guardar. ¿Guardar antes de cerrar?",
            )
            if resp is None:
                return
            if resp:
                if self.json_path:
                    self.save()
                else:
                    self.save_as()
                if self._dirty:
                    return

        self.items = []
        self.dir_visible = {}
        self.directorios = set()
        self.json_path = None
        self.nombre_biblioteca = ""
        self.url_base = ""
        self._clean_library_paths_from_config()
        self.settings_view.set_fields_from_config(self.config)
        self._clear_dirty()
        self.list_view.set_items(self.items, self.dir_visible, self.directorios)
        self.detail_view.load_items([])
        self._update_status()
        self.status_msg.config(text="Catálogo cerrado")

    # ── buscar portadas ─────────────────────────────────────

    def _extraer_portadas(self):
        PortadasExtractDialog(self.root)

    def buscar_portadas(self):
        if not self._ensure_paths(("portadas_root",)):
            return
        portadas_root = self.config["portadas_root"]
        if not Path(portadas_root).exists():
            messagebox.showerror("Error", f"La ruta de portadas no existe:\n{portadas_root}")
            return
        if not self.items:
            messagebox.showinfo("Sin datos", "Abre un JSON del catálogo antes de buscar portadas.")
            return

        self.status_msg.config(text="Indexando portadas...")
        self.root.update_idletasks()

        try:
            index = build_portada_index(portadas_root)
            results = find_missing_portadas(self.items, portadas_root, index)
        except Exception as e:
            messagebox.showerror("Error", f"Error al buscar portadas:\n{e}")
            self.status_msg.config(text="Error al buscar portadas")
            return

        web_root = self.config.get("web_root", "")

        # Procesar items "ok": tienen archivo en disco pero item.portada vacío
        ok_linked = 0
        for item, abs_path in results["ok"]:
            if not item.portada:
                item.portada = os.path.relpath(abs_path, web_root) if web_root else Path(abs_path).name
                ok_linked += 1

        total_problem = len(results["exact"]) + len(results["fuzzy"]) + len(results["not_found"])
        if total_problem == 0:
            msg = f"Todas las {len(results['ok'])} portadas están correctas."
            if ok_linked:
                msg += f"\n{ok_linked} portadas enlazadas automáticamente."
            messagebox.showinfo("Buscar portadas", msg)
            if ok_linked:
                self.list_view.refresh()
                cur = self.detail_view.get_item()
                if cur:
                    self.detail_view.load_items([cur])
                self._mark_dirty()
                self._update_status()
            self.status_msg.config(text="Portadas: todas correctas")
            return

        dialog = PortadaSearchDialog(self.root, results, portadas_root, web_root)
        dialog.wait_window()

        if dialog.result != "apply":
            self.status_msg.config(text="Búsqueda de portadas: descartada")
            return

        corrections = dialog.get_selected_corrections()
        for item, portada in corrections:
            item.portada = portada

        self.list_view.refresh()
        cur = self.detail_view.get_item()
        if cur:
            self.detail_view.load_items([cur])
        self._mark_dirty()
        self._update_status()

        self.status_msg.config(
            text=f"Portadas: {len(corrections)} corregidas  |  "
                 f"{len(results['not_found'])} sin encontrar"
        )

    # ── callbacks ──────────────────────────────────────────

    def _on_item_selected(self, items: List[Item]):
        if not self.detail_view.load_items(items):
            old = self.detail_view.get_item()
            if old:
                self.list_view.select_item(old)

    def _on_dir_selected(self, dir_name: Optional[str]):
        if not dir_name:
            self.detail_view.load_items([])
            return
        visible = self.dir_visible.get(dir_name, True)
        self.detail_view.load_directory(
            dir_name, visible,
            on_rename=self._on_dir_rename,
            on_delete=self._on_dir_delete,
        )

    def _on_dir_rename(self, old_name: str, new_name: str):
        library_root = self.config.get("library_root", "")
        new_name = new_name.rstrip("/")
        old_name = old_name.rstrip("/")

        if old_name in self.directorios:
            self.directorios.discard(old_name)
            self.directorios.add(new_name)

        if old_name in self.dir_visible:
            self.dir_visible[new_name] = self.dir_visible.pop(old_name)

        for item in self.items:
            if item.destino and item.destino.rstrip("/") == old_name:
                item.destino = new_name + "/"
            elif item.destino and item.destino.startswith(old_name + "/"):
                item.destino = new_name + "/" + item.destino[len(old_name) + 1:]

        if library_root:
            old_path = Path(library_root) / old_name
            new_path = Path(library_root) / new_name
            if old_path.exists():
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old_path), str(new_path))

        portadas_root = self.config.get("portadas_root", "")
        if portadas_root:
            old_portada_dir = Path(portadas_root) / old_name
            new_portada_dir = Path(portadas_root) / new_name
            if old_portada_dir.exists():
                new_portada_dir.mkdir(parents=True, exist_ok=True)
                for f in old_portada_dir.iterdir():
                    shutil.move(str(f), str(new_portada_dir / f.name))
                try:
                    old_portada_dir.rmdir()
                except OSError:
                    pass

            web_root = self.config.get("web_root", "")
            for item in self.items:
                if item.has_portada():
                    found = resolve_portada_file(
                        portadas_root, item.destino,
                        Path(item.nombre_legible).stem)
                    if found:
                        item.portada = os.path.relpath(str(found), web_root) if web_root else found.name

        self.list_view.set_items(self.items, self.dir_visible, self.directorios)
        self._mark_dirty()
        self._update_status()
        self.status_msg.config(text=f"Directorio renombrado: '{old_name}' → '{new_name}'")

    def _on_dir_delete(self, dir_name: str):
        dir_defaults = self.config.get("delete_defaults", {}).get("dir", {})
        dialog = DeleteDirDialog(self.root, [dir_name], dir_defaults)
        opts = dialog.result
        if opts is None:
            return

        self._apply_dir_delete([dir_name], opts)
        self.status_msg.config(text=f"Directorio eliminado: '{dir_name}'")

    def _apply_dir_delete(self, dirs: list, opts: DeleteDirResult):
        for d in dirs:
            self._delete_single_dir(d, opts)

        self.list_view.set_items(self.items, self.dir_visible, self.directorios)
        self.detail_view.load_items([])

        if opts.guardar_default:
            self.config.setdefault("delete_defaults", {})
            self.config["delete_defaults"]["dir"] = {
                "accion_fichas": opts.accion_fichas,
                "accion_pdfs": opts.accion_pdfs,
                "accion_portadas": opts.accion_portadas,
                "accion_subdirectorios": opts.accion_subdirectorios,
                "accion_mantenidos": opts.accion_mantenidos,
            }
            save_config(self.config)

        self._mark_dirty()
        self._update_status()

    def _delete_single_dir(self, dir_name: str, opts: DeleteDirResult):
        dir_name = dir_name.rstrip("/")
        library_root = self.config.get("library_root", "")
        portadas_root = self.config.get("portadas_root", "")
        web_root = self.config.get("web_root", "")

        # Recolectar items según alcance
        is_mantener_intactos = opts.accion_subdirectorios == "mantener_intactos"
        scope_items = []
        for it in self.items:
            if not it.destino:
                continue
            d = it.destino.rstrip("/")
            if d == dir_name:
                scope_items.append(it)
            elif not is_mantener_intactos and d.startswith(dir_name + "/"):
                scope_items.append(it)

        items_to_remove = []

        for item in scope_items:
            old_destino = item.destino.rstrip("/") if item.destino else ""
            is_direct = old_destino == dir_name
            in_subdir = (not is_direct) and old_destino.startswith(dir_name + "/")

            # Acciones efectivas según origen del item
            if in_subdir:
                sd_opt = opts.accion_subdirectorios
                if sd_opt == "eliminar_todo":
                    eff_fichas, eff_pdfs, eff_portadas = "eliminar", "borrar", "borrar"
                elif sd_opt == "solo_limpiar":
                    eff_fichas, eff_pdfs, eff_portadas = "eliminar", "mantener", "mantener"
                else:  # heredar
                    eff_fichas, eff_pdfs, eff_portadas = (
                        opts.accion_fichas, opts.accion_pdfs, opts.accion_portadas)
            else:
                eff_fichas = opts.accion_fichas
                eff_pdfs = opts.accion_pdfs
                eff_portadas = opts.accion_portadas

            # Nuevo destino tras subir un nivel
            if eff_fichas == "subir":
                if is_direct:
                    new_destino = ""
                else:
                    new_destino = item.destino[len(dir_name) + 1:]
            else:
                new_destino = None

            # Gestionar archivos
            self._delete_item_files(
                item, old_destino, new_destino,
                eff_pdfs, eff_portadas,
                library_root, portadas_root, web_root,
            )

            # Catálogo
            if eff_fichas == "eliminar":
                items_to_remove.append(item)
            else:
                item.destino = new_destino

        for item in items_to_remove:
            if item in self.items:
                self.items.remove(item)

        # Subdirectorios «mantener intactos» — ajustar destinos y mover físicamente
        if opts.accion_subdirectorios == "mantener_intactos":
            for it in self.items:
                if it.destino and it.destino.startswith(dir_name + "/"):
                    it.destino = it.destino[len(dir_name) + 1:]
            if library_root:
                dpath = Path(library_root) / dir_name
                if dpath.exists():
                    for child in list(dpath.iterdir()):
                        if child.is_dir():
                            target = Path(library_root) / child.name
                            if not target.exists():
                                shutil.move(str(child), str(target))
            if portadas_root:
                pdir = Path(portadas_root) / dir_name
                if pdir.exists():
                    for child in list(pdir.iterdir()):
                        if child.is_dir():
                            target = Path(portadas_root) / child.name
                            if not target.exists():
                                shutil.move(str(child), str(target))

        # Limpieza física
        has_mantener = (opts.accion_pdfs == "mantener" or opts.accion_portadas == "mantener")

        if has_mantener and opts.accion_mantenidos == "mover_a_raiz":
            self._move_files_to_root(dir_name, library_root, portadas_root)
            if library_root:
                dpath = Path(library_root) / dir_name
                if dpath.exists():
                    shutil.rmtree(str(dpath), ignore_errors=True)
            if portadas_root:
                pdir = Path(portadas_root) / dir_name
                if pdir.exists():
                    shutil.rmtree(str(pdir), ignore_errors=True)
        elif not (has_mantener and opts.accion_mantenidos == "no_borrar"):
            if library_root:
                dpath = Path(library_root) / dir_name
                if dpath.exists():
                    shutil.rmtree(str(dpath), ignore_errors=True)
            if portadas_root:
                pdir = Path(portadas_root) / dir_name
                if pdir.exists():
                    shutil.rmtree(str(pdir), ignore_errors=True)

        self.directorios.discard(dir_name)
        self.dir_visible.pop(dir_name, None)

    def _move_files_to_root(self, dir_name, library_root, portadas_root):
        if library_root:
            dpath = Path(library_root) / dir_name
            if dpath.exists():
                for f in list(dpath.iterdir()):
                    if f.is_file():
                        target = Path(library_root) / f.name
                        counter = 1
                        while target.exists():
                            target = Path(library_root) / f"{f.stem}_{counter}{f.suffix}"
                            counter += 1
                        shutil.move(str(f), str(target))
                try:
                    dpath.rmdir()
                except OSError:
                    pass
        if portadas_root:
            pdir = Path(portadas_root) / dir_name
            if pdir.exists():
                for f in list(pdir.iterdir()):
                    if f.is_file():
                        target = Path(portadas_root) / f.name
                        counter = 1
                        while target.exists():
                            target = Path(portadas_root) / f"{f.stem}_{counter}{f.suffix}"
                            counter += 1
                        shutil.move(str(f), str(target))
                try:
                    pdir.rmdir()
                except OSError:
                    pass

    def _delete_item_files(self, item, old_destino, new_destino,
                           accion_pdf, accion_portada,
                           library_root, portadas_root, web_root):
        if not old_destino:
            return
        # PDF
        if item.nombre_legible and library_root:
            src = Path(library_root) / old_destino / item.nombre_legible
            if src.exists():
                if accion_pdf == "borrar":
                    src.unlink()
                elif accion_pdf == "mover" and new_destino is not None:
                    dst = Path(library_root) / new_destino / item.nombre_legible
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if dst.exists():
                        dst.unlink()
                    shutil.move(str(src), str(dst))
        # Portada
        if item.nombre_legible and portadas_root:
            portada_path = resolve_portada_file(
                portadas_root, old_destino, Path(item.nombre_legible).stem)
            if portada_path and portada_path.exists():
                if accion_portada == "borrar":
                    portada_path.unlink()
                    item.portada = ""
                elif accion_portada == "mover" and new_destino is not None:
                    new_dir = Path(portadas_root) / new_destino
                    new_dir.mkdir(parents=True, exist_ok=True)
                    new_file = new_dir / portada_path.name
                    if new_file.exists():
                        new_file.unlink()
                    shutil.move(str(portada_path), str(new_file))
                    item.portada = (
                        os.path.relpath(str(new_file), web_root)
                        if web_root else new_file.name
                    )

    def _nuevo_directorio(self):
        dirs = self.list_view.get_selected_dirs()
        items = self.list_view.get_selected_items()

        parent = ""
        if dirs:
            parent = dirs[0].rstrip("/")
        elif items:
            parent = items[0].destino.rstrip("/")

        name = simpledialog.askstring(
            "Nuevo directorio",
            f"Nombre del nuevo directorio{f' en \"{parent}\"' if parent else ''}:",
            parent=self.root,
        )
        if not name:
            return
        name = name.strip().rstrip("/")
        if not name:
            return

        full_name = f"{parent}/{name}" if parent else name

        library_root = self.config.get("library_root", "")
        if library_root:
            dir_path = Path(library_root) / full_name
            dir_path.mkdir(parents=True, exist_ok=True)

        self.directorios.add(full_name)

        portadas_root = self.config.get("portadas_root", "")
        if portadas_root:
            (Path(portadas_root) / full_name).mkdir(parents=True, exist_ok=True)

        self.list_view.set_items(self.items, self.dir_visible, self.directorios)
        self._mark_dirty()
        self.status_msg.config(text=f"Directorio creado: '{full_name}'")

    def _delete_dir_menu(self):
        dirs = self.list_view.get_selected_dirs()
        if not dirs:
            if not self.directorios:
                messagebox.showinfo("Eliminar directorio", "No hay directorios en el catálogo.")
                return
            chosen = self._pick_directory_dialog()
            if chosen is None:
                return
            dirs = [chosen]

        dir_defaults = self.config.get("delete_defaults", {}).get("dir", {})
        dialog = DeleteDirDialog(self.root, dirs, dir_defaults)
        opts = dialog.result
        if opts is None:
            return

        self._apply_dir_delete(dirs, opts)

        label = ", ".join(dirs[:3])
        if len(dirs) > 3:
            label += f" (+{len(dirs) - 3} más)"
        self.status_msg.config(text=f"Directorio(s) eliminado(s): {label}")

    def _pick_directory_dialog(self) -> Optional[str]:
        dirs = sorted(self.directorios)
        win = tk.Toplevel(self.root)
        win.title("Seleccionar directorio")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)

        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Selecciona el directorio a eliminar:",
        ).pack(anchor="w", pady=(0, 8))

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        lb = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            selectmode="single",
            font=("TkFixedFont", 10),
            exportselection=False,
            height=min(len(dirs), 15),
            width=50,
        )
        scrollbar.configure(command=lb.yview)
        scrollbar.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True)

        for d in dirs:
            lb.insert("end", d)
        if dirs:
            lb.selection_set(0)
        lb.focus_set()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(8, 0))

        result = {"dir_name": None}

        def on_accept():
            sel = lb.curselection()
            if not sel:
                return
            result["dir_name"] = dirs[sel[0]]
            win.destroy()

        ttk.Button(btn_frame, text="Cancelar", command=win.destroy).pack(
            side="right", padx=(4, 0)
        )
        ttk.Button(btn_frame, text="Seleccionar", command=on_accept).pack(
            side="right"
        )

        win.wait_window()
        return result["dir_name"]

    def _collect_directorios(self):
        for item in self.items:
            if item.destino:
                parts = item.destino.rstrip("/").split("/")
                for i in range(len(parts)):
                    p = "/".join(parts[:i + 1])
                    self.directorios.add(p)
        for d in list(self.dir_visible.keys()):
            self.directorios.add(d.rstrip("/"))

    def _on_item_changed(self, item: Item):
        self.list_view.refresh()
        self._mark_dirty()
        self._update_status()

    def _on_item_dropped(self, items: List[Item], new_destino: str):
        portadas_root = self.config.get("portadas_root", "")
        library_root = self.config.get("library_root", "")
        mover = self.config.get("mover_items_fisicamente", True)

        for item in items:
            old_destino = item.destino
            if mover:
                if library_root and old_destino and item.nombre_legible:
                    try:
                        move_item(item, old_destino, new_destino, library_root)
                    except Exception as e:
                        messagebox.showwarning(
                            "Error al mover",
                            f"No se pudo mover el archivo:\n{item.nombre_legible}\n{e}",
                        )
                        continue
                if item.has_portada() and portadas_root:
                    try:
                        web_root = self.config.get("web_root", "")
                        move_portada(item, old_destino, new_destino, portadas_root, web_root)
                    except Exception as e:
                        messagebox.showwarning(
                            "Error al mover portada",
                            f"No se pudo mover la portada de:\n{item.nombre_legible}\n{e}",
                        )
            item.destino = new_destino
        self._collect_directorios()
        self.list_view.refresh()
        self.detail_view.load_items(self.list_view.get_selected_items())
        self._update_status()
        count = len(items)
        self.status_msg.config(text=f"Movidas {count} ficha(s) a {new_destino}")

    def _on_dir_dropped(self, dirs: List[str], new_parent: str):
        mover = self.config.get("mover_items_fisicamente", True)
        library_root = self.config.get("library_root", "")
        portadas_root = self.config.get("portadas_root", "")
        modified = False

        for old_dir in dirs:
            dir_name = old_dir.rsplit("/", 1)[-1]
            new_dir = f"{new_parent}/{dir_name}" if new_parent else dir_name

            if new_dir == old_dir:
                continue

            if mover:
                if library_root and Path(library_root, new_dir).exists():
                    messagebox.showwarning(
                        "Directorio existente",
                        f"'{new_dir}' ya existe en el disco. Se omite '{old_dir}'.",
                    )
                    continue
                if portadas_root and Path(portadas_root, new_dir).exists():
                    messagebox.showwarning(
                        "Directorio existente",
                        f"La carpeta de portadas '{new_dir}' ya existe. Se omite.",
                    )
                    continue

            if mover:
                if library_root:
                    old_path = Path(library_root) / old_dir
                    if old_path.exists():
                        new_path = Path(library_root) / new_dir
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(old_path), str(new_path))
                if portadas_root:
                    old_port = Path(portadas_root) / old_dir
                    if old_port.exists():
                        new_port = Path(portadas_root) / new_dir
                        new_port.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(old_port), str(new_port))

            old_prefix = old_dir + "/"
            for item in self.items:
                if item.destino and (
                    item.destino.rstrip("/") == old_dir
                    or item.destino.startswith(old_prefix)
                ):
                    suffix = item.destino[len(old_dir):]
                    item.destino = f"{new_dir}{suffix}"

            for d in list(self.dir_visible.keys()):
                if d == old_dir or d.startswith(old_prefix):
                    suffix = d[len(old_dir):]
                    self.dir_visible[f"{new_dir}{suffix}"] = self.dir_visible.pop(d)

            stale = [p for p in self.directorios
                     if p == old_dir or p.startswith(old_prefix)]
            for p in stale:
                self.directorios.discard(p)

            modified = True

        if not modified:
            return

        self._collect_directorios()
        self.list_view.refresh()
        self._mark_dirty()
        self._update_status()
        count = len(dirs)
        self.status_msg.config(text=f"Movido(s) {count} directorio(s) con su contenido.")

    def _on_config_saved(self, config: dict):
        self.config.update(config)
        self.nombre_biblioteca = config.get("nombre_biblioteca", self.nombre_biblioteca)
        self.detail_view.set_web_root(config.get("web_root", ""))
        self.detail_view.set_portadas_root(config.get("portadas_root", ""))
        self.detail_view.set_library_root(config.get("library_root", ""))
        self._apply_theme(config.get("theme", "default"))
        refresh_icons(self.toolbar)
        self._update_status()

    def _apply_theme(self, name: str):
        if name in ("sv-light", "sv-dark"):
            sv_ttk.set_theme("light" if name == "sv-light" else "dark", root=self.root)
        else:
            self.style.theme_use(name)

    def _update_recent_libraries_menu(self):
        self._recent_menu.delete(0, "end")
        recents = self.config.get("recent_libraries", [])
        if not recents:
            self._recent_menu.add_command(label="(ninguna)", state="disabled")
        else:
            for path in recents:
                label = Path(path).stem
                self._recent_menu.add_command(label=label, command=lambda p=path: self.open_json(p))

    def _open_update_url(self):
        if self._update_url:
            from .update_dialog import open_url
            open_url(self._update_url)

    def _show_silent_update(self, tag: str, url: str):
        self._update_url = url
        self._update_label.config(text=f"Existe una nueva versión {tag}  →")

    def _check_for_updates(self, silent: bool = False):
        if not silent:
            dlg = UpdateCheckerDialog(self.root, VERSION)
            self.root.wait_window(dlg.dialog)
            if dlg.tag and dlg.url:
                self._update_label.config(text=f"Existe una nueva versión {dlg.tag}  →")
                self._update_url = dlg.url
            else:
                self._update_label.config(text="")
                self._update_url = ""
        else:
            def _do_check():
                try:
                    req = urllib.request.Request(
                        "https://api.github.com/repos/CaRLymx/Bibliotheca_Arcanorum/releases/latest",
                        headers={"Accept": "application/vnd.github.v3+json",
                                 "User-Agent": "GestorBiblioteca/1.0"},
                    )
                    resp = urlopen_with_fallback(req)
                    data = json.loads(resp.read().decode())
                    latest_tag = data.get("tag_name", "").lstrip("vV")
                    if not latest_tag:
                        return
                    current_v = parse_version(VERSION)
                    latest_v = parse_version(latest_tag)
                    if latest_v > current_v:
                        tag = data.get("tag_name", "")
                        url = data.get("html_url", "")
                        self.root.after(0, lambda t=tag, u=url: self._show_silent_update(t, u))
                except Exception:
                    pass
            threading.Thread(target=_do_check, daemon=True).start()

    def _about(self):
        import webbrowser as _wb

        win = tk.Toplevel(self.root)
        win.title("Acerca de")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, False)

        frame = ttk.Frame(win, padding=20)
        frame.pack()

        ttk.Label(frame, text="Gestor de Bibliotecas", font=("", 16, "bold")).pack()

        ttk.Label(frame, text=f"v{VERSION}  (Mayo 2026)", font=("", 11)).pack(pady=(4, 0))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=12)

        ttk.Label(
            frame,
            text="Herramienta para gestionar el catálogo de la Biblioteca Web.\n"
                 "Edita, organiza y mantiene fichas con portadas para su publicación.",
            wraplength=360,
            justify="center",
        ).pack()

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=12)

        ttk.Label(frame, text="Creado por CaRLyMx (Mayo 2026)", font=("", 10)).pack()

        link = ttk.Label(
            frame,
            text="github.com/carlymx/Bibliotheca_Arcanorum",
            font=("", 10, "underline"),
            foreground="blue",
            cursor="hand2",
        )
        link.pack()
        link.bind("<Button-1>", lambda e: _wb.open("https://github.com/carlymx/Bibliotheca_Arcanorum"))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=12)

        lic_frame = ttk.Frame(frame)
        lic_frame.pack()
        ttk.Label(lic_frame, text="Licencia:  ", font=("", 9)).pack(side="left")
        lic_link = ttk.Label(
            lic_frame,
            text="GNU General Public License v3.0",
            font=("", 9, "underline"),
            foreground="blue",
            cursor="hand2",
        )
        lic_link.pack(side="left")
        lic_link.bind(
            "<Button-1>",
            lambda e: _wb.open("https://www.gnu.org/licenses/gpl-3.0.html"),
        )

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=12)

        ttk.Label(frame, text="Hecho con Tkinter + Python 3", font=("", 9), foreground="gray").pack()

        ttk.Button(frame, text="Cerrar", command=win.destroy).pack(pady=(10, 0))

        win.update_idletasks()
        pw = self.root.winfo_width()
        ph = self.root.winfo_height()
        wx = self.root.winfo_x()
        wy = self.root.winfo_rooty()
        dw = win.winfo_reqwidth()
        dh = win.winfo_reqheight()
        win.geometry(f"+{wx + (pw - dw) // 2}+{wy + (ph - dh) // 2}")

    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True
            self.root.title(self.root.title() + " *")
            self._dirty_indicator.config(text="⚠ Sin guardar", fg="red")

    def _clear_dirty(self):
        if self._dirty:
            self._dirty = False
            self._dirty_indicator.config(text="✔ Guardado", fg="green")
            self.root.after(2000, lambda: self._dirty_indicator.config(text=""))
            self._update_status()

    def _on_close(self):
        if self._dirty or self.detail_view.is_dirty():
            if not messagebox.askyesno(
                "Cambios sin guardar",
                "Hay cambios sin guardar. ¿Salir sin guardar?"
            ):
                return
        self._clean_library_paths_from_config()
        save_config(self.config)
        self.root.destroy()

    def _update_status(self):
        count = len(self.items)
        with_portada = sum(1 for i in self.items if i.has_portada())
        without_portada = count - with_portada
        hidden = sum(1 for i in self.items if i.oculto)
        name = self.nombre_biblioteca or "Gestor de Bibliotecas"
        title = f"{name} — v{VERSION}"
        if count:
            title += f" ({count} items)"
        self.root.title(title)
        self.status_counts.config(
            text=f"📄 {count} fichas  |  🖼 {with_portada} portadas  |  ⬜ {without_portada} sin portada  |  🔒 {hidden} ocultas"
        )

    def run(self):
        self.root.mainloop()
