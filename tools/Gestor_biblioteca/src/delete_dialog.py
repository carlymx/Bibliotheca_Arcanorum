import tkinter as tk
from tkinter import ttk
from typing import List, Optional


class DeleteItemResult:
    def __init__(self, borrar_pdf=False, borrar_portada=False, guardar_default=False):
        self.borrar_pdf = borrar_pdf
        self.borrar_portada = borrar_portada
        self.guardar_default = guardar_default


class DeleteDirResult:
    def __init__(
        self,
        accion_fichas="subir",
        accion_pdfs="mover",
        accion_portadas="mover",
        accion_subdirectorios="heredar",
        accion_mantenidos="mover_a_raiz",
        guardar_default=False,
    ):
        self.accion_fichas = accion_fichas
        self.accion_pdfs = accion_pdfs
        self.accion_portadas = accion_portadas
        self.accion_subdirectorios = accion_subdirectorios
        self.accion_mantenidos = accion_mantenidos
        self.guardar_default = guardar_default


class DeleteItemDialog(tk.Toplevel):
    def __init__(self, parent, count: int, defaults: dict):
        super().__init__(parent)
        self.title(f"Eliminar {count} ficha{'s' if count != 1 else ''}")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.result: Optional[DeleteItemResult] = None

        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text=(
                f"Se van a eliminar {count} ficha{'s' if count != 1 else ''} del catálogo."
            ),
            wraplength=340,
        ).pack(anchor="w", pady=(0, 10))

        self._borrar_pdf_var = tk.BooleanVar(
            value=defaults.get("borrar_pdf", False)
        )
        self._borrar_portada_var = tk.BooleanVar(
            value=defaults.get("borrar_portada", False)
        )

        ttk.Checkbutton(
            frame,
            text="Borrar PDF del disco",
            variable=self._borrar_pdf_var,
        ).pack(anchor="w", pady=2)

        ttk.Checkbutton(
            frame,
            text="Borrar portada del disco",
            variable=self._borrar_portada_var,
        ).pack(anchor="w", pady=2)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10)

        self._guardar_default_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Guardar como predeterminado",
            variable=self._guardar_default_var,
        ).pack(anchor="w")

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(12, 0))

        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(
            side="right", padx=(4, 0)
        )
        ttk.Button(btn_frame, text="Eliminar", command=self._accept).pack(
            side="right"
        )

        self.wait_window()

    def _accept(self):
        self.result = DeleteItemResult(
            borrar_pdf=self._borrar_pdf_var.get(),
            borrar_portada=self._borrar_portada_var.get(),
            guardar_default=self._guardar_default_var.get(),
        )
        self.destroy()


class DeleteDirDialog(tk.Toplevel):
    def __init__(self, parent, dirs: List[str], defaults: dict):
        super().__init__(parent)
        n = len(dirs)
        self.title(f"Eliminar {n} directorio{'s' if n != 1 else ''}")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.result: Optional[DeleteDirResult] = None

        pad = {"padx": 14, "pady": 14}
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, **pad)

        dirs_text = "\n".join(f"  • {d}" for d in dirs[:5])
        if n > 5:
            dirs_text += f"\n  … y {n - 5} más"
        ttk.Label(
            frame,
            text=f"Directorios seleccionados:\n{dirs_text}",
            wraplength=380,
        ).pack(anchor="w", pady=(0, 10))

        # ── Fichas ──
        lb1 = ttk.LabelFrame(frame, text="Fichas del catálogo", padding=8)
        lb1.pack(fill="x", pady=4)
        self._fichas_var = tk.StringVar(value=defaults.get("accion_fichas", "subir"))
        ttk.Radiobutton(
            lb1, text="Subir un nivel (a raíz o directorio padre)",
            variable=self._fichas_var, value="subir",
        ).pack(anchor="w")
        ttk.Radiobutton(
            lb1, text="Eliminar del catálogo",
            variable=self._fichas_var, value="eliminar",
        ).pack(anchor="w")

        # ── PDFs ──
        lb2 = ttk.LabelFrame(frame, text="PDFs en disco", padding=8)
        lb2.pack(fill="x", pady=4)
        self._pdfs_var = tk.StringVar(value=defaults.get("accion_pdfs", "mover"))
        self._pdfs_mover_rb = ttk.Radiobutton(
            lb2, text="Mover con la ficha",
            variable=self._pdfs_var, value="mover",
        )
        self._pdfs_mover_rb.pack(anchor="w")
        ttk.Radiobutton(
            lb2, text="Borrar",
            variable=self._pdfs_var, value="borrar",
        ).pack(anchor="w")
        ttk.Radiobutton(
            lb2, text="Mantener",
            variable=self._pdfs_var, value="mantener",
        ).pack(anchor="w")

        # ── Portadas ──
        lb3 = ttk.LabelFrame(frame, text="Portadas en disco", padding=8)
        lb3.pack(fill="x", pady=4)
        self._portadas_var = tk.StringVar(value=defaults.get("accion_portadas", "mover"))
        self._portadas_mover_rb = ttk.Radiobutton(
            lb3, text="Mover con la ficha",
            variable=self._portadas_var, value="mover",
        )
        self._portadas_mover_rb.pack(anchor="w")
        ttk.Radiobutton(
            lb3, text="Borrar",
            variable=self._portadas_var, value="borrar",
        ).pack(anchor="w")
        ttk.Radiobutton(
            lb3, text="Mantener",
            variable=self._portadas_var, value="mantener",
        ).pack(anchor="w")

        # ── Subdirectorios ──
        lb4 = ttk.LabelFrame(frame, text="Subdirectorios", padding=8)
        lb4.pack(fill="x", pady=4)
        self._subdirs_var = tk.StringVar(
            value=defaults.get("accion_subdirectorios", "heredar")
        )
        ttk.Radiobutton(
            lb4, text="Heredar estas opciones",
            variable=self._subdirs_var, value="heredar",
        ).pack(anchor="w")
        ttk.Radiobutton(
            lb4, text="Eliminar todo (purga total)",
            variable=self._subdirs_var, value="eliminar_todo",
        ).pack(anchor="w")
        ttk.Radiobutton(
            lb4, text="Solo limpiar catálogo (dejar archivos)",
            variable=self._subdirs_var, value="solo_limpiar",
        ).pack(anchor="w")
        ttk.Radiobutton(
            lb4, text="Mantener intactos",
            variable=self._subdirs_var, value="mantener_intactos",
        ).pack(anchor="w")

        # ── Archivos mantenidos ──
        self._mant_frame = ttk.LabelFrame(
            frame, text="Archivos mantenidos", padding=8
        )
        self._mant_var = tk.StringVar(
            value=defaults.get("accion_mantenidos", "mover_a_raiz")
        )
        ttk.Radiobutton(
            self._mant_frame, text="No borrar el directorio físico",
            variable=self._mant_var, value="no_borrar",
        ).pack(anchor="w")
        ttk.Radiobutton(
            self._mant_frame, text="Mover archivos a la raíz y borrar el directorio",
            variable=self._mant_var, value="mover_a_raiz",
        ).pack(anchor="w")

        # ── Guardar default ──
        self._sep = ttk.Separator(frame, orient="horizontal")
        self._sep.pack(fill="x", pady=8)

        self._guardar_default_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame,
            text="Guardar como predeterminado",
            variable=self._guardar_default_var,
        ).pack(anchor="w")

        # ── Botones ──
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(
            side="right", padx=(4, 0)
        )
        ttk.Button(btn_frame, text="Aceptar", command=self._accept).pack(
            side="right"
        )

        # ── Enlaces ──
        self._fichas_var.trace_add("write", self._on_fichas_changed)
        self._pdfs_var.trace_add("write", self._on_pdfs_changed)
        self._portadas_var.trace_add("write", self._on_portadas_changed)

        self._update_mover_state()
        self._update_mant_frame()

        self.wait_window()

    def _on_fichas_changed(self, *_):
        self._update_mover_state()

    def _on_pdfs_changed(self, *_):
        self._update_mant_frame()

    def _on_portadas_changed(self, *_):
        self._update_mant_frame()

    def _update_mover_state(self):
        fichas = self._fichas_var.get()
        state = "disabled" if fichas == "eliminar" else "normal"
        self._pdfs_mover_rb.configure(state=state)
        self._portadas_mover_rb.configure(state=state)
        if fichas == "eliminar":
            if self._pdfs_var.get() == "mover":
                self._pdfs_var.set("borrar")
            if self._portadas_var.get() == "mover":
                self._portadas_var.set("borrar")

    def _update_mant_frame(self):
        pdfs = self._pdfs_var.get()
        portadas = self._portadas_var.get()
        if pdfs == "mantener" or portadas == "mantener":
            self._mant_frame.pack(fill="x", pady=4, before=self._sep)
        else:
            self._mant_frame.pack_forget()

    def _accept(self):
        self.result = DeleteDirResult(
            accion_fichas=self._fichas_var.get(),
            accion_pdfs=self._pdfs_var.get(),
            accion_portadas=self._portadas_var.get(),
            accion_subdirectorios=self._subdirs_var.get(),
            accion_mantenidos=self._mant_var.get(),
            guardar_default=self._guardar_default_var.get(),
        )
        self.destroy()
