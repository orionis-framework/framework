# Instalación y primer proyecto

Orionis requiere Python 3.14 o posterior. Este checkout declara la versión `0.901.0` y el estado Alpha en `pyproject.toml`. Usa los manuales junto con la misma revisión del framework: las APIs y dependencias descritas pertenecen a este árbol de código.

## Preparar el entorno

Para trabajar con el checkout actual desde Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -c "from orionis.metadata import VERSION; print(VERSION)"
```

En macOS o Linux:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -c 'from orionis.metadata import VERSION; print(VERSION)'
```

Ejecuta estos comandos en la raíz del checkout. La instalación editable sirve para desarrollar contra este código; no crea la estructura de una aplicación. Este repositorio ya incluye `app/`, `bootstrap/`, `config/`, `routes/`, `resources/`, `database/`, `storage/` y el script `reactor`. Un proyecto que solo instala la distribución necesita proporcionar su propio bootstrap y archivos de aplicación; el entry point de consola no genera ese esqueleto.

El repositorio también mantiene `uv.lock`; si ya trabajas con uv, `uv sync` prepara las dependencias declaradas. No mezcles intérpretes: comprueba `python --version` dentro del entorno que ejecutará el proyecto. El comando instalado `orionis` importa `bootstrap.app` desde el directorio de trabajo.

## Dependencias según la tarea

SQLite, el motor de templates, hashing y los componentes principales están en las dependencias base. Los proveedores cloud y motores SQL adicionales se instalan mediante extras de la distribución. Por ejemplo, `python -m pip install -e ".[pgsql]"` instala el driver PostgreSQL de esta revisión. Los extras disponibles son `mysql`, `pgsql`, `oracle`, `sqlserver`, `redshift`, `database`, `s3`, `azure`, `gcs` y `storage`. Las agrupaciones `dev` y `docs` son grupos de desarrollo, no extras.

Consulta [Database](../../../database/docs/es/README.md) y [Storage](../../../storage/docs/es/README.md) para configurar el servicio además de instalar su driver. Una dependencia instalada no crea tablas, credenciales ni infraestructura.

## Entorno local y clave de aplicación

Prepara un `.env` local siguiendo `.env.example`, sin publicar credenciales. `Env` utiliza el `.env` del directorio de trabajo y sus valores prevalecen sobre variables homónimas del proceso. El arranque configura zona horaria y locale; el locale del sistema puede no estar instalado en todos los equipos.

`APP_KEY` protege los datos cifrados. Si falta una clave al construir la configuración base, el framework puede generarla y persistirla. Configura una clave estable y privada antes del primer despliegue con varios workers. No copies las claves fijas utilizadas en ejemplos aislados de estos manuales. Cambiar una clave sin una estrategia de lectura de datos antiguos puede impedir descifrarlos.

## Entender el primer arranque

`bootstrap/app.py` crea `Application`, habilita opcionalmente la caché de arranque, registra routing, scheduler, exception handler, providers y middleware, y llama `create()`. Las rutas declaradas deben existir y usar los imports de facade admitidos; una ruta inexistente detiene el arranque. La configuración de la aplicación se descubre en dataclasses frozen de `config/`.

El script `reactor` importa esa instancia y ejecuta `app.handleCommand(sys.argv)` mediante `Loop.run`. La aplicación HTTP exporta la misma instancia para ASGI o RSGI. Aprende la diferencia entre creación, providers preparados y kernel HTTP preparado en [el ciclo de vida](application-lifecycle.md).

## Diagnosticar problemas de inicio

| Síntoma | Comprobación |
|---|---|
| `ModuleNotFoundError` de una dependencia | Confirma el intérprete y que instalaste el checkout o el extra apropiado en ese entorno. |
| No se encuentra `bootstrap.app` | Ejecuta la consola desde la raíz de una aplicación que incluya ese módulo. |
| Error de tipo o valor de configuración | Revisa dataclass, enum y valor tipado del entorno; no presupongas que todo valor es texto. |
| Cambios de configuración que no aparecen | Revisa el orden de precedencia y la caché compilada antes de modificar servicios en ejecución. |
| Error de ruta en `withRouting` | Confirma el archivo real, su import de facade y la raíz de `Application`. |

La instalación anterior describe comandos reproducibles; esta reconstrucción no reinstaló dependencias ni contactó servicios externos. Los ejemplos locales se comprueban con las dependencias ya presentes.



Fuentes: [pyproject.toml](../../../../pyproject.toml) · [app.py](../../../../bootstrap/app.py) · [cli.py](../../../console/cli.py).

[Índice del módulo](README.md).
