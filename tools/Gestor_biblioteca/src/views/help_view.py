import tkinter as tk
from tkinter import ttk


def _build_item(frame, title, desc, wraplength=680):
    ttk.Label(frame, text=title, font=("", 11, "bold")).pack(anchor="w")
    ttk.Label(frame, text=desc, font=("", 10), wraplength=wraplength).pack(
        anchor="w", pady=(2, 8)
    )


class HelpView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._build()

    def _build(self):
        pad_x = {"padx": 20}

        canvas = tk.Canvas(self, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable = ttk.Frame(canvas)

        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._canvas_window = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self._canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # ── Barra de herramientas ──
        tb_frame = ttk.LabelFrame(scrollable, text="Barra de herramientas", padding=12)
        tb_frame.pack(fill="x", padx=20, pady=(0, 10))

        ttk.Label(
            tb_frame,
            text="La barra de herramientas usa iconos en vez de texto. "
                 "Al pasar el cursor por encima aparece un tooltip con la descripción.",
            font=("", 10),
            wraplength=700,
        ).pack(anchor="w", pady=(0, 6))

        toolbar_help = [
            ("🗂️  Nuevo catálogo (Ctrl+Shift+N)",
             "Crea un catálogo desde cero escaneando la biblioteca."),
            ("📂  Abrir JSON (Ctrl+O)",
             "Abre un archivo JSON del catálogo existente."),
            ("💾  Guardar catálogo (Ctrl+S)",
             "Guarda el catálogo actual en el JSON y exporta catalogo.js."),
            ("➕  Añadir ficha (Ctrl+N)",
             "Crea una ficha vacía en el catálogo."),
            ("🗑️  Eliminar ficha",
             "Elimina la ficha seleccionada del catálogo. Muestra un diálogo para elegir "
             "si se borran también el PDF y la portada del disco."),
            ("📁  Nuevo directorio",
             "Crea un nuevo directorio en la biblioteca y en portadas."),
            ("🚫  Eliminar directorio",
             "Elimina un directorio del catálogo y del disco. Muestra un diálogo con "
             "opciones avanzadas: subir o eliminar fichas, mover/borrar/mantener PDFs "
             "y portadas, y cómo tratar subdirectorios."),
        ]

        for title, desc in toolbar_help:
            _build_item(tb_frame, title, desc)

        ttk.Separator(scrollable, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # ── Menú ──
        menu_frame = ttk.LabelFrame(scrollable, text="Menú Archivo y Herramientas", padding=12)
        menu_frame.pack(fill="x", padx=20, pady=(0, 10))

        menu_help = [
            ("Buscar cambios (Ctrl+B)",
             "Escanea el directorio de la biblioteca (PDFs) en busca de archivos "
             "nuevos que aún no estén en el catálogo. Los detecta por su hash SHA-256 "
             "y los añade como fichas nuevas.\n\n"
             "Puedes personalizar las exclusiones en Configuración → 'Ignorar en las búsquedas'."),
            ("Portadas → Buscar portadas",
             "Busca portadas faltantes o mal asignadas. Compara las rutas de portada "
             "de cada ficha contra los archivos existentes en el directorio de portadas.\n\n"
             "Sugiere correcciones automáticas (coincidencias exactas y aproximadas)."),
             ("Portadas → Extraer portadas",
              "Abre una ventana para extraer portadas en lote desde archivos PDF, "
              "imágenes (JPG, PNG, TIFF, BMP, WEBP, GIF), archivos de audio con "
              "carátula incrustada (MP3, M4A/AAC, OGG, FLAC), y libros digitales "
              "(EPUB, MOBI, AZW3, CBZ, CBR, DOCX).\n\n"
              "Los checkboxes de formatos están agrupados en tres categorías: "
              "Documentos (PDF, EPUB, CBZ, CBR, MOBI/AZW3, DOCX), "
              "Imagenes/Mapas (JPG, PNG, TIFF, BMP, WEBP, GIF), "
              "y Audio/Musica (MP3, M4A/AAC, OGG, FLAC).\n\n"
              "Configura directorio origen y destino, formato de salida, resolución, "
              "y sobrescritura. Usa procesamiento paralelo y muestra progreso en tiempo real."),
             ("   Página",
              "Número de página (1-based) que se usará como portada. "
              "El comportamiento varía según el formato:\n\n"
              "• PDF/CBZ/CBR/DOCX: el número indica la página o imagen "
              "a extraer. Si supera el total disponible, se usa la última "
              "automáticamente. Truco: pon 9999 para obtener la contraportada "
              "de todos los archivos.\n\n"
              "• EPUB/MOBI/AZW3: ignoran este parámetro. Siempre extraen "
              "la portada declarada en los metadatos del libro.\n\n"
              "Por defecto es 1 (primera página o portada)."),
            ("   Trabajos en paralelo",
             "Número de procesos simultáneos que se lanzan para extraer portadas. "
             "Por defecto se usan 4, pero puedes ajustarlo del 1 al máximo de hilos "
             "de tu procesador (se muestra entre paréntesis al lado del control).\n\n"
             "Con valores altos se acelera la extracción masiva en máquinas multinúcleo. "
             "Reduce el número si notas el sistema lento o si trabajas con archivos muy grandes."),
            ("Directorios → Añadir directorio",
             "Crea un nuevo directorio tanto en el sistema de archivos como en el "
             "catálogo. Pide el nombre y crea la carpeta en library_root y portadas_root."),
            ("Directorios → Eliminar directorio",
             "Elimina un directorio del catálogo y del disco. Abre un diálogo con "
             "opciones para fichas (subir/eliminar), PDFs (mover/borrar/mantener), "
             "portadas (mover/borrar/mantener) y subdirectorios (heredar/eliminar_todo/"
             "solo_limpiar/mantener_intactos).\n\n"
             "Si se seleccionan varios directorios, el diálogo se omite y se aplican "
             "los defaults configurados."),
            ("Fichas → Añadir ficha (Ctrl+N)",
             "Añade una ficha vacía con valores por defecto."),
            ("Fichas → Eliminar ficha",
             "Elimina la ficha seleccionada del catálogo. Muestra un diálogo para decidir "
             "si se borra también el PDF y/o la portada del disco."),
            ("Exportar fichas... (Ctrl+Shift+E)",
             "Empaqueta fichas seleccionadas o todo el catálogo en un archivo "
             "`.bibliotex` (JSON) o `.bibliotex.zip` (incluye portadas y PDFs). "
             "Permite elegir formato, incluir portadas/PDFs, y cifrar con contraseña."),
            ("Importar fichas... (Ctrl+Shift+I)",
             "Importa fichas desde un archivo `.bibliotex` o `.bibliotex.zip`. "
             "Detecta duplicados por hash y permite sobrescribir, saltar o añadir. "
             "Extrae PDFs y portadas a los directorios correspondientes."),
        ]

        for title, desc in menu_help:
            _build_item(menu_frame, title, desc)

        ttk.Separator(scrollable, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # ── Formulario detalle ──
        form_frame = ttk.LabelFrame(scrollable, text="Formulario de ficha", padding=12)
        form_frame.pack(fill="x", padx=20, pady=(0, 10))

        form_help = [
            ("💾 Aplicar cambios",
             "Guarda en memoria los cambios del formulario de la ficha actual. "
             "Los cambios no se persisten en disco hasta que pulses 'Guardar' en la barra."),
            ("↩️ Revertir cambios",
             "Descarta las modificaciones no aplicadas del formulario y restaura "
             "los valores originales de la ficha."),
            ("Nombre legible",
             "Nombre público con el que se mostrará la ficha en el catálogo. "
             "No tiene por qué coincidir con el nombre del archivo PDF.\n\n"
             "Ej: «Aquelarre - Manual básico 3ª edición»"),
            ("Tipo",
             "Clasifica la ficha para organizar y filtrar el catálogo. Los valores disponibles son:\n\n"
             "manual = Para guías y manuales principales, normalmente oficiales.\n"
             "suplemento = Normalmente expansiones de las reglas o el mundo, oficiales o no.\n"
             "campaña = Conjunto de misiones que pertenecen a una misma aventura. Pueden agregar "
             "o no suplementos y expansiones del mundo que sirven a la aventura.\n"
             "aventura = Módulo o aventura individual. Suelen ser pocas páginas.\n"
             "revista = Revistas del mundo del juego de rol.\n"
             "documento = Comodín para enmarcar todo documento que no quepa en las anteriores.\n"
             "info = Comodín genérico.\n"
             "imagen = Toda imagen que no es un mapa.\n"
             "mapa = Mapas de localizaciones ficticias o reales.\n"
             "hoja_pj = Fichas de hojas de personajes jugadores o no jugadores.\n"
             "pantalla = Pantalla de cartón que separa a los jugadores del Director de juego.\n"
             "musica = Bandas sonoras o música ambiental para partidas.\n"
             "otro = Cualquier otra cosa que no encaje en todas las anteriores."),
            ("Edición",
             "Indica la edición del material. Puede ser 1ª a 20ª, o indeterminada. "
             "Ayuda a filtrar y ordenar el catálogo por versiones."),
            ("Confianza",
             "Nivel de fiabilidad de los metadatos de la ficha:\n\n"
             "alta = Información contrastada y completa.\n"
             "media = Información parcial o pendiente de verificar.\n"
             "baja = Ficha recién creada o con datos provisionales."),
            ("Ubicación Documento",
             "Ruta relativa (desde la raíz de la biblioteca) donde se encuentra el archivo físico. "
             "Se usa para agrupar fichas en directorios dentro del catálogo.\n\n"
             "Pulsa el botón '...' para elegir una carpeta del sistema."),
            ("Descripción",
             "Texto descriptivo del contenido de la ficha. Acepta texto libre con el formato que "
             "prefieras. Se muestra en la web como resumen del material."),
            ("Justificación",
             "Explica por qué esta ficha está en el catálogo o por qué tiene ciertos valores. "
             "Normalmente de uso interno para documentar decisiones del catalogador."),
            ("Archivo Hash",
             "Almacena el hash SHA-256 del archivo. Se asigna automáticamente al escanear y "
             "sirve para detectar cambios o duplicados. Campo de solo lectura."),
            ("Peso",
             "Peso de la portada en bytes. Se completa automáticamente al asignar una portada."),
            ("Escaneado",
             "Marca si el archivo ha sido escaneado manualmente (no es una descarga digital). "
             "Sirve para identificar materiales físicos digitalizados."),
            ("Mostrar en web",
             "Cuando está desmarcado, la ficha se oculta en la web pero permanece en el catálogo. "
             "El icono en el árbol cambia de ✅ a ⬜."),
        ]

        for title, desc in form_help:
            _build_item(form_frame, title, desc)

        # Portada (sub-sección dentro del mismo LabelFrame)
        ttk.Label(form_frame, text="Portada", font=("", 11, "bold", "underline")).pack(
            anchor="w", pady=(8, 2)
        )

        portada_help = [
            ("Subir portada...",
             "Abre un selector de archivos para elegir una imagen de portada. "
             "La imagen se copiará al directorio de portadas con el formato:\n"
             "  [portada]_{nombre_legible}.jpg.\n"
             "Formatos admitidos: JPG, PNG, WEBP, GIF."),
            ("Limpiar portada",
             "Elimina la referencia a la portada de la ficha actual. "
             "NO borra el archivo de imagen del disco."),
            ("Abrir Directorio",
             "Abre la carpeta donde se almacenan las portadas para la ficha actual "
             "en el gestor de archivos del sistema."),
            ("Vista previa",
             "Muestra una previsualización de la portada asignada. Si no se encuentra "
             "el archivo o no se puede mostrar, se indica con un mensaje."),
        ]

        for title, desc in portada_help:
            _build_item(form_frame, title, desc, wraplength=660)

        # Documento (sub-sección dentro del mismo LabelFrame)
        ttk.Label(form_frame, text="Documento", font=("", 11, "bold", "underline")).pack(
            anchor="w", pady=(8, 2)
        )

        doc_help = [
            ("Subir Documento...",
             "Abre un selector de archivos para copiar o mover un documento "
             "al directorio de destino de la ficha. El nombre legible se "
             "asigna automáticamente sin extensión.\n\n"
             "Si el archivo ya existe, pregunta si sobrescribir.\n"
             "El comportamiento (copiar/mover) se configura en Configuración."),
            ("Abrir Directorio",
             "Abre en el gestor de archivos la carpeta donde está (o debería "
             "estar) el documento de la ficha actual."),
            ("Limpiar",
             "Elimina la referencia al documento de la ficha actual. "
             "NO borra el archivo físico del disco."),
        ]

        for title, desc in doc_help:
            _build_item(form_frame, title, desc, wraplength=660)

        ttk.Separator(scrollable, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # ── Configuración ──
        cfg_frame = ttk.LabelFrame(scrollable, text="Configuración", padding=12)
        cfg_frame.pack(fill="x", padx=20, pady=(0, 10))

        config_help = [
            ("Ruta biblioteca (PDFs)",
             "Directorio raíz donde están los archivos PDF y demás documentos "
             "del catálogo. Es la ruta que se escanea al usar 'Buscar cambios'."),
            ("Ruta portadas (imágenes)",
             "Directorio donde se almacenan las imágenes de portada asociadas "
             "a cada ficha. Las portadas se copian aquí con el formato:\n"
             "  [portada]_{nombre}.jpg"),
            ("Ruta web (index.html)",
             "Directorio raíz del sitio web."),
            ("Ruta catalogo.js",
             "Ruta donde se exporta catalogo.js para la web.\n"
             "Se configura y se guarda desde la pestaña Configuración."),
            ("Ignorar en las búsquedas",
             "Lista de archivos y directorios que se saltará 'Buscar cambios'.\n"
             "Un patrón por línea. Usa * como comodín."),
            ("Copias de seguridad",
             "Al abrir un archivo JSON se crea una copia de seguridad rotatoria.\n"
             "Pon 0 para deshabilitar."),
            ("Defaults de borrado",
             "Configura los valores por defecto del diálogo de eliminación.\n\n"
             "Al eliminar una ficha: elegir si borrar PDF y portada por defecto.\n\n"
             "Al eliminar un directorio:\n"
             "  • Fichas: subir a raíz o eliminar del catálogo.\n"
             "  • PDFs: mover a raíz, borrar o mantener.\n"
             "  • Portadas: mover a raíz, borrar o mantener.\n"
             "  • Subdirectorios: heredar acción principal, eliminar todo,\n"
             "    solo limpiar (borrar fichas pero dejar PDFs/portadas),\n"
             "    o mantener intactos (mover subdirectorios a raíz).\n"
             "  • Mantenidos: mover archivos a raíz o no borrar el directorio."),
            ("Comportamiento upload",
             "Configura si al subir portadas y documentos se copian o se mueven:\n\n"
             "  • Portada: al subir una imagen, se copia (por defecto) al directorio "
             "de portadas. Si eliges 'mover', se traslada y se elimina del origen.\n\n"
             "  • Documento: al subir un archivo PDF (u otro formato), se copia al "
             "directorio de destino de la ficha. Con 'mover', se traslada."),
        ]

        for title, desc in config_help:
            _build_item(cfg_frame, title, desc)

        ttk.Separator(scrollable, orient="horizontal").pack(fill="x", padx=20, pady=10)

        # ── Atajos de teclado ──
        shortcut_frame = ttk.LabelFrame(scrollable, text="Atajos de teclado", padding=12)
        shortcut_frame.pack(fill="x", padx=20, pady=(0, 10))

        shortcuts = [
            ("Ctrl+O", "Abrir JSON"),
            ("Ctrl+S", "Guardar catálogo"),
            ("Ctrl+B", "Buscar cambios"),
            ("Ctrl+N", "Añadir ficha vacía"),
            ("Ctrl+Shift+N", "Nuevo catálogo"),
            ("Ctrl+Shift+E", "Exportar fichas"),
            ("Ctrl+Shift+I", "Importar fichas"),
        ]

        grid = ttk.Frame(shortcut_frame)
        grid.pack(fill="x")
        for i, (key, action) in enumerate(shortcuts):
            ttk.Label(grid, text=key, font=("", 10, "bold"), width=18, anchor="w").grid(
                row=i, column=0, sticky="w", pady=1
            )
            ttk.Label(grid, text=action, font=("", 10), anchor="w").grid(
                row=i, column=1, sticky="w", pady=1, padx=(10, 0)
            )

        _bind_mousewheel(canvas, scrollable)


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
