# Prompt: Clasificación de juegos de rol

Eres un experto en juegos de rol. Clasifica estos archivos por su nombre, tamaño y hash.

> Puedes usar los MCPs disponibles (websearch, brave-search, etc.) para buscar información adicional si el nombre del archivo no es suficiente para identificar el juego, tipo o idioma.

## Instrucciones

1. Lee la tabla `descargas` de la base de datos SQLite (`tgfilecenter.db`) filtrando por `estado = 'pendiente'`.
2. Para cada archivo, identifica a qué **juego de rol** pertenece, qué **tipo** de documento es, y en qué **idioma** está.
3. Escribe los resultados en la tabla `clasificaciones` con los siguientes campos:
   - `archivo_hash`: el hash SHA256 del archivo (calculado a partir del contenido real)
   - `juego`: nombre del juego de rol (ej: "Vampiro - La Mascarada 5e", "Dungeons & Dragons 5e", "Aquelarre")
   - `tipo`: uno de: `manual_basico`, `suplemento`, `aventura`, `mapa`, `otro`
   - `idioma`: `es`, `en`, `fr`, `de`, `it`, `pt`, u `otro`
   - `nombre_legible`: nombre limpio y legible para el archivo
   - `confianza`: `alta`, `media` o `baja`
4. Actualiza la tabla `descargas` poniendo `estado = 'clasificado'` para los archivos procesados.

## Estructura de salida

Los archivos clasificados deben organizarse en una estructura de directorios:

```
Clasificados/
├── [Nombre del Juego]/
│   ├── 01 - Manuales (Basicos)/
│   │   ├── 1ª Edición
│   │   ├── 2ª Edición
│   │   └── (...)
│   ├── 02 - Manuales (Expansiones Oficiales)
│   │   ├── 1ª Edición
│   │   ├── 2ª Edición
│   │   └── (...)
│   ├── 03 - Modulos (aventuras Oficiales)
│   │   ├── 1ª Edición
│   │   ├── 2ª Edición
│   │   └── (...)
│   ├── 04 - Modulos (aventuras NoOficiales)
│   │   ├── 1ª Edición
│   │   ├── 2ª Edición
│   │   └── (...)
│   ├── 05 - Suplementos (Oficiales)
│   │   ├── 1ª Edición
│   │   ├── 2ª Edición
│   │   └── (...)
│   ├── 06 - Suplementos (NoOficiales)
│   │   ├── 1ª Edición
│   │   ├── 2ª Edición
│   │   └── (...)
│   ├── 80 - Mapas
│   ├── 90 - Documentación NoOficial
│   ├── 95 - Otros
│   └── 99 - No Clasificados
└── clasificacion.json
```

Donde:
- Cada tipo de documento va en su subdirectorio correspondiente
- Los nombres de archivos deben ser limpios y legibles (sin hashes en el nombre)
- Si hay conflictos de nombres (mismo nombre legible para archivos distintos), añade un sufijo numérico: `Nombre_1.pdf`, `Nombre_2.pdf`

## Archivo de metadatos

Crea un archivo `clasificacion.json` con la siguiente estructura:

```json
{
  "clasificaciones": [
    {
      "archivo_hash": "...",
      "juego": "...",
      "tipo": "...",
      "idioma": "...",
      "nombre_legible": "...",
      "escaneado": true,
      "confianza": "...",
      "edicion": "...",
      "destino": "...",
      "justificacion": "...",
      "descripcion": "...",
      "portada": "...",
      "peso": "..."
    }
  ]
}
```

### Campos

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| `archivo_hash` | ✅ | SHA256 del archivo |
| `juego` | ✅ | Nombre del juego de rol (ej: "Aquelarre") |
| `tipo` | ✅ | `manual_basico`, `suplemento`, `aventura`, `mapa`, `otro` |
| `idioma` | ✅ | `es`, `en`, `fr`, `de`, `it`, `pt`, `otro` |
| `nombre_legible` | ✅ | Nombre limpio y legible para el archivo |
| `escaneado` | ✅ | `true` si es versión escaneada, `false` si es digital nativa |
| `confianza` | ✅ | `alta`, `media` o `baja` |
| `edicion` | ✅ | Edición del juego (ej: `1ª`, `2ª`, `3ª`, `4ª`, `indeterminada`) |
| `destino` | ✅ | Ruta relativa del directorio de destino (ej: `"02 - Manuales (Expansiones Oficiales)/2ª Edición/"`) |
| `justificacion` | ✅ | Texto explicativo de la decisión de clasificación y búsquedas realizadas |
| `descripcion` | ✅ | Descripción del contenido del archivo |
| `portada` | ⬜ | Ruta de la imagen de portada (ej: `"../Aquelarre_pak/portadas/categoría/archivo.jpg"`). Se rellena manualmente después de la clasificación |
| `peso` | ⬜ | Tamaño del archivo en formato legible (ej: `"50.1 MB"`). Opcional |
| `contenido` | ⬜ | Estructura interna para aventuras multiparte con sub-aventuras. Opcional |

## Archivos comprimidos

- Los archivos `.zip`, `.rar`, `.7z` deben tratarse como contenedores
- Clasifica el archivo comprimido según su contenido principal
- Si contiene múltiples tipos, usa el tipo mayoritario o `suplemento` por defecto
- En el campo `nombre_legible`, indica que es un compendio/colección

## Reglas de clasificación

### Referencias:
- Se analizará y tomará como referencia la estructura de directorios del directorio raíz y todo su árbol del directorio que el usuario marque como destino.
- El directorio de destino original antes de la clasificación es muy posible que contenga archivos precargados que deberán tomarse como referencia y bajo ningún concepto ser renombrados, movidos, copiados o eliminados. Dado que los habrá puesto el usuario a mano.

### Cómo renombrar en términos generales:
- Una vez analizado el nombre, si es necesario se harán búsquedas por internet para hallar la siguiente información relevante si es posible:
 - Edición (1ª, 2ª, 3ª...)
 - Colección a la que pertenece, si se aplica (Grandes Ciudades, Cofradía Anatema...)
 - Nombre (El Libro Secreto de los Alquimistas, El País de Oc...)
 - Volumen, si procede (Vol. 1, Vol. 2...)
 - Año de edición
 - Oficial, no oficial, fanzine...

- Se renombrará cada archivo de la siguiente manera si la información existe o se ha podido encontrar:
 - `[Juego] [Edición] - [Colección] - [Nombre] [Volumen] [Año].[Formato]`

### No clasificables:
- Todo aquel documento que por el nombre o el hash y su búsqueda por internet no haya arrojado información suficiente para su correcta clasificación se moverá al directorio "99 - No Clasificados". En el JSON se creará una sección específica con estos documentos agregando una entrada explicando por qué no se ha podido clasificar.

### Tratamiento de duplicados:
- Es muy posible que se encuentren documentos duplicados:
 - Con el mismo nombre o fragmentos iguales. Comprobar si pesan lo mismo o si son dos volúmenes distintos, y actuar en consecuencia.
 - En caso de sospecha de un duplicado, el que prevalecerá por encima de todos es el que ya se encuentre en el directorio de destino. A menos que el archivo del directorio de destino tenga la etiqueta `[Scan]`. En ese caso, se comprobará intentando leer algún fragmento del PDF que se está clasificando en busca de texto u otros signos claros de que se está ante una versión digital (no escaneada). Si se confirma que el archivo nuevo es digital y el existente es escaneado, se moverá el archivo con etiqueta `[Scan]` a un subdirectorio dentro del mismo directorio llamado "Escaneados".
 - En el caso de los duplicados, se moverán a un subdirectorio llamado "Duplicados" en el directorio de origen.

### Archivos de otros juegos de rol:
- Durante la clasificación pueden aparecer archivos que **no pertenezcan al juego principal** que se está clasificando (ej: al clasificar material de Aquelarre, aparece un libro de D&D, una ficha de La Llamada de Cthulhu, etc.).
- Estos archivos **no deben mezclarse** con la estructura de directorios del juego principal ni dejarse en el directorio de origen.
- Se moverán al directorio de origen bajo la siguiente estructura:
  ```
  ./Otros juegos/[Nombre del Juego]/
  ```
  Donde `[Nombre del Juego]` es el nombre identificado del juego (ej: "Dungeons & Dragons 5e", "La Llamada de Cthulhu 7e").
- Si el juego no puede identificarse con suficiente confianza, se moverá a `./Otros juegos/No Identificado/`.
- En el JSON de clasificación se registrarán estos archivos en una sección independiente `otros_juegos` con los mismos campos que las clasificaciones principales, más el juego identificado.

### Reglas básicas de clasificación (mover a directorio):
- Los directorios ya han sido prediseñados y establecidos con anterioridad.
- No se pueden crear, mover, copiar o eliminar los directorios preexistentes.
- Siempre que se haya concluido que un archivo pertenece a una edición particular, se moverá dentro de su respectivo subdirectorio dentro del tipo.
- Si no se ha encontrado el número de la edición o se sospecha que puede pertenecer de forma genérica a cualquiera o a todas ellas (puede pasar con aventuras, fanzines y documentos no oficiales), se moverá al directorio raíz del tipo correspondiente.

### Por tipo:
- **manual_basico**: términos como "core", "players handbook", "manual", "edición", "anniversary", "basic", "essential"
- **mapas**: palabras como "mapa", "cartografía", "map", "battlemap", "dungeon map"
- **aventuras**: palabras como "aventura", "módulo", "campaña", "capítulo", "adventure", "module", "campaign", "one-shot"
- **suplementos**: complementan el manual (bestiarios, guías, escenarios, supplements)

### Por idioma:
- Detecta variantes: "spanish", "español", "esañol", "castellano" → `es`
- Detecta: "english", "inglés", "inglish" → `en`
- Si no hay pistas en el nombre, usa `otro` con confianza `baja`

### Por edición/versión:
- Busca patrones como "4e", "5e", "4ª", "5th", "anniversary", "edición", "edition"
- Si la edición no es clara, incluye solo el nombre del juego base

### Identificación de escaneados frente a digitales:
- Un archivo etiquetado como `[Scan]` es una versión escaneada (fotocopia digitalizada), NO un documento digital nativo.
- La etiqueta `[Scan]` es informativa y debe **preservarse en el nombre del archivo** durante el renombrado, nunca eliminarse.
- Existen variantes abreviadas de estas etiquetas: `[S]` para Scan y `[D]` para Digital. Sin embargo, **al clasificar y renombrar un archivo siempre se usará la versión completa** (`[Scan]` o `[Digital]`), nunca la abreviada.
- Sirve para identificar qué documentos podrían ser sustituidos en el futuro si se encuentra una versión digital nativa (OCR, texto seleccionable, menor tamaño, mayor calidad).
- Para los archivos que originalmente NO tenían la etiqueta `[Scan]`, se asume que son versiones digitales nativas.
- En el JSON de clasificación se registrará un campo `escaneado: true/false` para facilitar la consulta automatizada.

### Prioridad Digital sobre Scan:
- **Siempre que sea posible, se priorizará la versión digital frente a la escaneada.**
- Las versiones digitales no llevan ninguna etiqueta en el nombre (limpias). Los archivos originalmente etiquetados como `[Digital]` **pierden la etiqueta** al renombrarse. Los archivos `[Scan]` **mantienen la etiqueta** al renombrarse.
- Cuando se identifique manualmente que un archivo nuevo es una versión digital de otro que ya existe en el directorio de destino con etiqueta `[Scan]`:
  1. **No se trata como duplicado.** La versión digital sustituye a la escaneada.
  2. La versión digital se clasifica y renombra sin etiqueta en el directorio de destino correspondiente.
  3. La versión `[Scan]` existente se mueve a `./99 - No Clasificados/Scan/` para su retiro manual (no se elimina por si hay que recuperarla).
  4. En el JSON se actualiza la entrada: se sustituye el hash del scan por el de la versión digital, y `escaneado` pasa a `false`.

### Por confianza:
- **alta**: nombre del archivo contiene información clara y verificable
- **media**: información ambigua pero razonable
- **baja**: no estás seguro del juego, tipo o idioma

## Manejo de errores

- Si un archivo no puede clasificarse, regístralo en la sección `errores` del JSON
- Usa confianza `baja` cuando tengas dudas razonables
- NO inventes información no verificable

## Logging

Para cada clasificación, registra:
- Hash del archivo original
- Decisión tomada y justificación breve
- Cualquier búsqueda web realizada (si aplica)
