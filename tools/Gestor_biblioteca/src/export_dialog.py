import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Callable, Optional

from .models import Item
from .export_handler import export_items


class ExportDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Widget,
        items: list[Item],
        config: dict,
        on_export_done: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent)
        self.title("Exportar fichas")
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)
        self.geometry("600x540")
        self.minsize(500, 440)

        self.items = items
        self.config = config
        self.on_export_done = on_export_done

        self._build()
        self._populate()

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

        # ── header ──
        ttk.Label(self, text="Exportar fichas", font=("", 12, "bold")).pack(
            anchor="w", **pad
        )

        ttk.Separator(self, orient="horizontal").pack(fill="x", **pad)

        # ── items preview ──
        preview_frame = ttk.LabelFrame(self, text=f"Fichas ({len(self.items)})", padding=5)
        preview_frame.pack(fill="both", expand=True, **pad)

        cols = ("nombre", "juego", "tipo", "tamaño")
        self.tree = ttk.Treeview(preview_frame, columns=cols, show="headings",
                                 height=8, selectmode="none")
        for col in cols:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=100)

        scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # ── options ──
        opts_frame = ttk.LabelFrame(self, text="Opciones de exportación", padding=10)
        opts_frame.pack(fill="x", **pad)

        self._formato_var = tk.StringVar(
            value=self.config.get("export_formato_default", "json")
        )
        ttk.Radiobutton(
            opts_frame,
            text="Solo metadatos (.bibliotex)",
            variable=self._formato_var,
            value="json",
            command=self._on_formato_change,
        ).pack(anchor="w")
        ttk.Radiobutton(
            opts_frame,
            text="Completo (.bibliotex.zip)",
            variable=self._formato_var,
            value="zip",
            command=self._on_formato_change,
        ).pack(anchor="w")

        self._incluir_portadas_var = tk.BooleanVar(
            value=self.config.get("export_incluir_portadas", False)
        )
        self._incluir_pdfs_var = tk.BooleanVar(
            value=self.config.get("export_incluir_pdfs", False)
        )

        incluir_frame = ttk.Frame(opts_frame)
        incluir_frame.pack(anchor="w", padx=(20, 0), pady=(5, 0))

        self._portadas_cb = ttk.Checkbutton(
            incluir_frame,
            text="Incluir portadas",
            variable=self._incluir_portadas_var,
        )
        self._portadas_cb.pack(side="left", padx=(0, 10))

        self._pdfs_cb = ttk.Checkbutton(
            incluir_frame,
            text="Incluir PDFs",
            variable=self._incluir_pdfs_var,
        )
        self._pdfs_cb.pack(side="left")

        ttk.Label(opts_frame, text="Comentario (opcional):").pack(anchor="w", pady=(5, 0))
        self._comentario_entry = ttk.Entry(opts_frame)
        self._comentario_entry.pack(fill="x", pady=(2, 0))

        # ── progress ──
        self._progress_bar = ttk.Progressbar(self, mode="determinate")
        self._progress_label = ttk.Label(self, text="")
        self._progress_bar.pack(fill="x", **pad)
        self._progress_label.pack(**pad)

        # ── buttons ──
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", **pad)

        self._export_btn = ttk.Button(btn_frame, text="Exportar", command=self._do_export)
        self._export_btn.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(
            side="left", padx=5
        )

        self._on_formato_change()

    def _populate(self):
        if not self.items:
            self._export_btn.configure(state="disabled")
        for item in self.items:
            self.tree.insert(
                "", "end",
                values=(
                    item.nombre_legible or "(sin nombre)",
                    item.juego,
                    item.tipo,
                    item.peso or "",
                ),
            )

    def _on_formato_change(self):
        state = "normal" if self._formato_var.get() == "zip" else "disabled"
        self._portadas_cb.configure(state=state)
        self._pdfs_cb.configure(state=state)

    def _progress(self, pct, msg):
        self._progress_bar.configure(value=pct)
        self._progress_label.configure(text=msg)
        self.update_idletasks()

    def _do_export(self):
        formato = self._formato_var.get()
        incluir_portadas = self._incluir_portadas_var.get() and formato == "zip"
        incluir_pdfs = self._incluir_pdfs_var.get() and formato == "zip"
        comentario = self._comentario_entry.get().strip()

        ext = ".bibliotex.zip" if formato == "zip" else ".bibliotex"
        initial = f"exportacion{ext}"

        destino = filedialog.asksaveasfilename(
            title="Guardar exportación como...",
            defaultextension=ext,
            initialfile=initial,
            filetypes=[
                ("Bibliotex JSON", "*.bibliotex"),
                ("Bibliotex ZIP", "*.bibliotex.zip"),
            ],
        )
        if not destino:
            return

        try:
            export_items(
                self.items,
                destino,
                formato,
                incluir_portadas=incluir_portadas,
                incluir_pdfs=incluir_pdfs,
                comentario=comentario,
                biblioteca_origen=self.config.get("nombre_biblioteca", ""),
                library_root=self.config.get("library_root", ""),
                portadas_root=self.config.get("portadas_root", ""),
                progress_callback=self._progress,
            )
            self._progress(100, "Exportación completada")
            messagebox.showinfo(
                "Exportación completada",
                f"Se han exportado {len(self.items)} fichas.\n\n{destino}",
                parent=self,
            )
            callback = self.on_export_done
            self.destroy()
            if callback:
                self.after(10, lambda: callback(destino))
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e), parent=self)
            self._progress(0, "Error")
