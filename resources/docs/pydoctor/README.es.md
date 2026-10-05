# Orionis · tema para Pydoctor

Tema reutilizable para la referencia API de Orionis. Extiende el tema `base`
mediante `--template-dir`; no modifica los HTML después de generarlos ni los
archivos instalados de Pydoctor. Verificado con Pydoctor **25.10.1**.

## Generar la documentación

Desde la raíz del repositorio, con `uv` instalado:

```powershell
.\DOCS.ps1
```

El resultado queda en `docs/index.html`. El script instala las dependencias del
grupo `docs` mediante `uv`, lee la versión de `pyproject.toml` y vincula el código
fuente a la revisión Git actual. Puede invocarse desde otro directorio y restaura
la ubicación original al terminar.

La generación se prepara desde cero en `.docs-build-<id>/site`. Antes de
reemplazar el resultado anterior se validan los índices, la búsqueda y el
inventario. **Todo el contenido anterior de `docs` se reemplaza**, incluido
cualquier archivo o carpeta ajeno a la documentación generada. Si falla la
publicación, el script intenta restaurar el resultado anterior. Una generación
fallida conserva su carpeta temporal para diagnóstico.

- Código `0`: documentación generada correctamente.
- Código `2`: Pydoctor terminó con errores de parsing de docstrings o del AST.
  Si existen todos los artefactos principales se publica el resultado, se muestra
  una advertencia y se conserva el código `2` para CI. Revisa el log: algunos
  textos u objetos pueden estar incompletos.
- Código `1`: fallo de generación, validación o publicación.

Para usar la búsqueda, sirve la documentación por HTTP; los navegadores restringen
la carga de sus índices al abrir un archivo mediante `file://`:

```powershell
uv run python -m http.server 8000 --bind 127.0.0.1 --directory docs
```

Abre <http://127.0.0.1:8000/>. `Ctrl+C` detiene el servidor. El sitio usa recursos
locales; no necesita Google Fonts, CDN ni un proceso de compilación de frontend.

## Estructura

```text
resources/docs/pydoctor/
├── README.md
└── templates/
    ├── extra.css           # Tokens, diseño, responsive e impresión
    ├── head.html           # Fuentes de estilos, scripts, favicon y viewport
    ├── header.html         # Marca y controles globales
    ├── subheader.html      # Ruta de navegación y portada
    ├── footer.html         # Metadatos y scripts originales de búsqueda
    ├── orionis-theme.js    # Preferencia de color aplicada antes del CSS
    ├── orionis-ui.js       # Navegación, atajos y copia de ejemplos
    ├── orionis-icon.svg
    └── orionis-fonts/      # Titillium Web, Fira Code y licencias OFL
```

## Personalización y reuso

Los tokens de `extra.css` siguen la identidad de Orionis: azul `#206bc4`,
marino `#082b52`, cian `#66d5f4`, dorado `#f5ca37` y tipografía Titillium Web.
Fira Code se utiliza para firmas y ejemplos. Ajusta `:root` y
`html[data-theme='dark']` para variar colores, superficies, bordes y fuentes sin
tocar las plantillas.

El modo inicial sigue al sistema y el botón guarda la elección en
`localStorage` bajo `orionis-api-theme`. La navegación móvil aparece hasta
760 px; si cambias ese límite, actualiza tanto el CSS como `orionis-ui.js`.
Los atajos `/`, `Ctrl+K` y `Cmd+K` enfocan la búsqueda fuera de campos de edición;
`Escape` cierra los resultados o la navegación móvil. Los ejemplos ofrecen copia
de código con una alternativa de selección manual si el navegador no la permite.

La configuración principal reside en `[tool.pydoctor]` de `pyproject.toml`.
Para reutilizar el tema en otro repositorio, copia esta carpeta y configura:

```toml
[tool.pydoctor]
project-name = "Mi proyecto"
add-package = ["mi_paquete"]
html-output = "docs/api"
theme = "base"
template-dir = ["resources/docs/pydoctor/templates"]
docformat = "numpy"
sidebar-expand-depth = 2
sidebar-toc-depth = 3
use-hardlinks = true
```

Después ejecuta `uv run --group docs pydoctor`. Adapta la marca, los enlaces y el
texto de `header.html`, `subheader.html` y `footer.html`. La portada se activa
para `index.html`, `orionis.html` o una URL de directorio; ajusta la detección en
`orionis-theme.js` si tu raíz usa otro nombre. El formato de docstrings y la
política de visibilidad deben corresponder al proyecto de destino. Orionis
conserva `PUBLIC:**`, como su script anterior.

## Mantenimiento

Las plantillas `head.html` y `footer.html` declaran la versión **3** de sus
equivalentes en Pydoctor 25.10.1. `header.html` y `subheader.html` son puntos de
extensión sin versión. Al actualizar Pydoctor, comprueba los avisos de plantillas
y revisa portada, clase con firmas largas, índices, búsqueda, móvil y ambos modos
de color. Se mantienen la navegación, los renderers y el motor de búsqueda de
Pydoctor.

El icono procede de `orionis/metadata/icon.svg`; Titillium Web procede de
`storage/app/public/fonts/titillium-web`, y Fira Code de
`orionis/http/default/assets/fonts`. Las copias dentro del tema permiten moverlo
sin depender de esas rutas. Conserva las licencias OFL al redistribuir las fuentes.

Referencias: [personalización oficial](https://pydoctor.readthedocs.io/en/latest/customize.html)
y [configuración de Pydoctor](https://pydoctor.readthedocs.io/en/latest/help.html).