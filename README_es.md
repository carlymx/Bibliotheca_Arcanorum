<p align="center">
  <img src="src/imgs/img_web_002.png" alt="Bibliotheca Arcanorum" width="800">
  <br>
  <em>Collectio Manuscriptorum</em>
</p>

<h1 align="center">Bibliotheca Arcanorum</h1>

<p align="center">
  <strong>Gestor de bibliotecas de juegos de rol de código abierto</strong><br>
  Catálogo web SPA + aplicación de escritorio multiplataforma para crear y gestionar colecciones de documentos de juego.
</p>

<p align="center">
  <a href="#características">Características</a> •
  <a href="#arquitectura">Arquitectura</a> •
  <a href="#primeros-pasos">Primeros pasos</a> •
  <a href="#personalizar-para-cualquier-rpg">Personalización</a> •
  <a href="#compilar-la-app-de-escritorio">Compilar</a> •
  <a href="#licencia">Licencia</a>
</p>

<p align="center">
  🌐 <a href="README.md">Read in English</a>
</p>

---

## Descripción

**Bibliotheca Arcanorum** es un sistema completo para organizar, catalogar y explorar colecciones de documentos de juegos de rol. Combina un catálogo web estático y ligero con una potente aplicación de escritorio para la gestión.

El proyecto está diseñado para ser **independiente del juego**: aunque incluye una temática dedicada al juego de rol [Aquelarre](https://es.wikipedia.org/wiki/Aquelarre_(juego_de_rol)), la versión genérica puede personalizarse para cualquier sistema — D&D, El Anillo Único, La Llamada de Cthulhu, o tu propia ambientación.

### Componentes

| Componente | Descripción |
|---|---|
| 🌐 **Catálogo web genérico** (`webs/web_BibliothecaArcanorum/`) | SPA en JavaScript puro — sin frameworks, sin backend, sin build. Funciona en cualquier servidor HTTP estático. |
| 🎭 **Catálogo web temático** (`webs/web_Aquelarre/`) | El mismo motor, tematizado para Aquelarre con marca personalizada, portada y créditos comunitarios. |
| 🖥️ **Gestor de escritorio** (`tools/Gestor_biblioteca/`) | App Python/Tkinter para crear, editar y mantener catálogos. Escanea directorios de PDFs, extrae portadas, gestiona metadatos. |

---

## Características

### Catálogo Web (SPA)

- **100% estático** — HTML/CSS/JS puro, sin servidor, sin base de datos. Funciona en cualquier servidor de archivos estático o localmente.
- **Árbol de directorios** — Navega los documentos por estructura de carpetas con expandir/colapsar.
- **Vista cuadrícula / lista** — Alterna entre tarjetas con portada y lista compacta.
- **Búsqueda y filtros** — Búsqueda de texto completo con filtros por tipo, edición y confianza.
- **Panel de detalle** — Previsualización de portada, metadatos, notas personales, valoraciones, estado de lectura.
- **Favoritos** — Marca documentos para acceso rápido.
- **Estadísticas de lectura** — Registra páginas leídas, marca libros como terminados.
- **Tema oscuro / claro** — Preferencia persistente con detección del tema del sistema.
- **Exportación/importación de ajustes** — Respaldar o transferir favoritos, valoraciones y notas.
- **Sin conexión** — Todos los datos se almacenan en LocalStorage.
- **Multilenguaje** — Los datos del catálogo soportan cualquier idioma.

### Gestor de Escritorio (Gestor_biblioteca)

- **CRUD completo** — Añade, edita, elimina fichas del catálogo con un formulario enriquecido.
- **Escáner de PDFs** — Escanea un árbol de directorios, detecta archivos nuevos, movidos, renombrados o eliminados; revisa los cambios antes de aplicarlos.
- **Gestión de portadas** — Asocia portadas automáticamente, sube portadas personalizadas, extrae portadas de PDFs, archivos de audio (MP3, FLAC, OGG, M4A) e imágenes.
- **Búsqueda de portadas** — Indexa portadas existentes y las enlaza automáticamente a las fichas correspondientes.
- **Arrastrar y soltar** — Mueve fichas entre directorios visualmente en el árbol.
- **Exportación JSON** — Genera `catalogo.js` listo para la web.
- **Rotación de copias de seguridad** — Copias de seguridad rotativas automáticas del catálogo.
- **Compilación multiplataforma** — Windows (.exe), macOS (.dmg), Linux (.AppImage) vía PyInstaller + CI.

---

## Arquitectura

```
BibliothecaArcanorum/
├── webs/
│   ├── web_BibliothecaArcanorum/   ← Catálogo genérico (copia y personaliza)
│   │   ├── index.html              ← Shell SPA (edita texto, título, pestañas)
│   │   ├── css/style.css           ← Estilos compartidos
│   │   ├── js/
│   │   │   ├── app.js              ← Inicio y orquestación
│   │   │   ├── data.js             ← Modelo de datos y persistencia
│   │   │   ├── tree.js             ← Árbol de directorios
│   │   │   ├── card.js             ← Tarjetas (cuadrícula y lista)
│   │   │   ├── search.js           ← Búsqueda y filtros
│   │   │   ├── detail.js           ← Panel de detalle del item
│   │   │   └── settings.js         ← Preferencias de usuario y exportación
│   │   ├── data/catalogo.js        ← Generado por Gestor_biblioteca
│   │   └── assets/                 ← Logos, portada, placeholders
│   │
│   └── web_Aquelarre/              ← Variante temática de Aquelarre
│       └── (mismos JS/CSS, distinto index.html, logo, portada)
│
├── tools/
│   └── Gestor_biblioteca/          ← App de escritorio Python/Tkinter
│       ├── main.py                 ← Punto de entrada
│       ├── build.spec              ← Especificación PyInstaller
│       ├── requirements.txt
│       ├── src/
│       │   ├── app.py              ← Ventana principal y orquestación
│       │   ├── models.py           ← Dataclass Item
│       │   ├── catalog.py          ← Carga/guarda JSON
│       │   ├── scanner.py          ← Escáner del sistema de archivos
│       │   ├── portada_mgr.py      ← Gestión de imágenes de portada
│       │   ├── portadas_extract_dialog.py  ← Extracción portadas PDF/audio
│       │   ├── portada_search_dialog.py    ← Auto-enlace de portadas
│       │   ├── scan_dialog.py      ← Diálogo de revisión de escaneo
│       │   ├── path_setup_dialog.py
│       │   ├── settings_view.py
│       │   └── views/              ← list_view, detail_view, help_view
│       └── scripts/                ← Scripts de build (Win/Mac/Linux)
│
└── src/                            ← Recursos compartidos
    └── logo.svg
```

### Cómo se conecta todo

```
┌──────────────────┐    genera JSON     ┌──────────────────────┐
│  Gestor_biblioteca│ ──────────────────→  │  data/catalogo.js    │
│  (app escritorio) │   (exporta .js)   │                      │
└──────────────────┘                    └──────────┬───────────┘
                                                   │ lo carga
                                                   ▼
                                        ┌──────────────────────┐
                                        │  Catálogo Web (SPA)  │
                                        │  (cualquier servidor) │
                                        └──────────────────────┘
```

La app de escritorio genera un archivo `catalogo.js` que el catálogo web carga como script. Sin API, sin base de datos — solo un objeto JS estático.

---

## Primeros pasos

### Inicio rápido con el catálogo web

1. Clona este repositorio:
   ```bash
   git clone https://github.com/tu-usuario/BibliothecaArcanorum.git
   ```
2. Abre `webs/web_BibliothecaArcanorum/index.html` directamente en tu navegador — no necesita servidor.

> El catálogo web es una **SPA estática** (HTML/CSS/JS) que carga sus datos desde una etiqueta `<script>`. Funciona con el protocolo `file://` sin necesidad de configuración. Para crear tu propio catálogo, usa el gestor de escritorio.

### Usar el gestor de escritorio

**Opción A — Binarios precompilados (recomendado):**  
Descarga la última versión para tu plataforma desde la página de [Releases](https://github.com/carlymx/Bibliotheca_Arcanorum/releases) — no necesitas instalar Python.

**Opción B — Ejecutar desde el código fuente:**

Requiere **Python 3.8+**.

```bash
cd tools/Gestor_biblioteca

# (Opcional) Crear y activar un entorno virtual
python3 -m venv venv
source venv/bin/activate    # Linux/macOS
# venv\Scripts\activate     # Windows

pip install -r requirements.txt
python main.py
```

También se incluyen scripts auxiliares que automatizan la creación del entorno virtual:
- Linux/macOS: `run.sh`
- Windows: `run_win.bat`

La app te guiará por la configuración inicial de rutas (directorio raíz de PDFs, directorio de portadas, raíz web).

---

## Personalizar para cualquier RPG

El catálogo genérico (`web_BibliothecaArcanorum`) está diseñado como **plantilla**. Para adaptarlo a otro juego:

1. **Copia** `webs/web_BibliothecaArcanorum/` a un nuevo directorio.
2. **Reemplaza** `assets/icons/logo.svg` y `assets/portada_web.png` con tu propia marca.
3. **Edita** `index.html` para cambiar el título, texto de portada y etiquetas de pestañas.
4. **Genera** tu catálogo con Gestor_biblioteca, asignando el campo `juego` al nombre de tu juego.
5. **Sirve** la web personalizada desde cualquier servidor HTTP estático.

> **Ejemplos de variantes**: D&D, El Anillo Único, La Llamada de Cthulhu, Pathfinder, Warhammer Fantasy, Cyberpunk RED, o incluso colecciones de documentos no relacionados con juegos.

Solo `index.html` y la carpeta `assets/` necesitan cambios — los 7 módulos JavaScript son compartidos.

---

## Compilar la app de escritorio

Los binarios precompilados están disponibles en la página de [Releases](https://github.com/tu-usuario/BibliothecaArcanorum/releases). Para compilar desde el código fuente:

### Requisitos

- **Python 3.8+**
- **Poppler utils** (`pdftoppm`) — para extracción de portadas de PDF
  - Linux: `sudo apt install poppler-utils`
  - macOS: `brew install poppler`
  - Windows: se incluye automáticamente en el script de build

### Compilar con PyInstaller

```bash
cd tools/Gestor_biblioteca
pip install -r requirements.txt pyinstaller
pyinstaller build.spec
```

Esto produce:
- **Linux**: `dist/Gestor_biblioteca` (usa `scripts/build-linux.sh` para AppImage)
- **macOS**: `dist/Gestor_biblioteca.app` (usa `scripts/build-macos.sh` para .dmg)
- **Windows**: `dist/Gestor_biblioteca.exe` (usa `scripts/build-windows.ps1` para .exe)

### Compilación automatizada

El repositorio incluye un workflow de GitHub Actions (`.github/workflows/build.yml`) que compila las tres plataformas en cada push de una tag de versión.

---

## Tecnologías

| Capa | Tecnología |
|---|---|
| **Frontend web** | JavaScript Vanilla (ES6), CSS3, HTML5 |
| **App escritorio** | Python 3, Tkinter, Pillow, mutagen, sv-ttk |
| **Herramientas externas** | pdftoppm (poppler-utils), appimagetool, create-dmg |
| **CI/CD** | GitHub Actions |
| **Empaquetado** | PyInstaller |

La web tiene **cero dependencias** — ni npm, ni build step, ni frameworks, ni CDN. Todo es JS escrito a mano.

---

## Proyectos relacionados

- [Sun-Valley-ttk-theme](https://github.com/rdbende/Sun-Valley-ttk-theme) — Tema moderno para Tkinter usado por Gestor_biblioteca
- [poppler](https://poppler.freedesktop.org/) — Librería de renderizado PDF (pdftoppm)
- [mutagen](https://mutagen.readthedocs.io/) — Librería de metadatos de audio para extracción de portadas

---

## Licencia

Este proyecto está licenciado bajo la GNU General Public License v3.0 — consulta el archivo [LICENSE](LICENSE) para más detalles.

*Aquelarre es una marca registrada de Ricard Ibáñez. Este proyecto no está afiliado ni respaldado por el autor.*
