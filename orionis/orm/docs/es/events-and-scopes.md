# Eventos, scopes y soft deletes

Estos mecanismos incorporan comportamiento al modelo sin repetir filtros y comprobaciones en cada consumidor. No sustituyen controles de autorización de la aplicación; las consultas de tabla cruda pueden saltarlos.

## Centralizar filtros con scopes

Un scope local es un método estático o de clase llamado `scope<Name>`. Su nombre fluido elimina el prefijo y usa inicial minúscula. El scope modifica el builder de forma síncrona:

```python
from orionis.orm import DateTime, Integer, Model, String


class Document(Model):
    id = Integer().primary().autoIncrement()
    title = String(180)
    status = String(30)
    deleted_at = DateTime().nullable()
    timestamps = False
    soft_deletes = True

    @staticmethod
    def scopePublished(query):
        query.where("status", "published")


plan = Document.published().toPlan()
assert len(plan.wheres) == 1
```

En una aplicación, `await Document.published().get()` aplica el scope. `query.scope("published")` es una alternativa explícita; un nombre ausente produce `ScopeNotFoundException`. Los scopes globales se registran con `Document.addGlobalScope("policy", callback)` y se aplican antes de ejecutar. `withoutGlobalScope("policy")`, `withoutGlobalScopes(...)` y `removeGlobalScope("policy")` permiten omitirlos/eliminarlos según alcance. No cambies el registro global para resolver una sola petición concurrente: modifica únicamente su builder.

## Escuchar y vetar persistencia

Los eventos son `retrieved`, `saving`, `creating`, `created`, `updating`, `updated`, `saved`, `deleting`, `deleted`, `restoring` y `restored`. Un listener recibe el modelo y puede ser síncrono o async.

```python
def require_title(document: Document) -> bool:
    return bool(document.title.strip())


Document.registerEvent("saving", require_title)
```

Solo `saving`, `creating`, `updating`, `deleting` y `restoring` admiten veto devolviendo exactamente `False`. `save()`, `delete()` y `restore()` pueden por ello devolver `False` sin excepción SQL. No ignores ese resultado cuando la operación sea obligatoria. `Model.create()` devuelve una instancia aunque `save()` haya sido vetado; usa construcción y `save()` explícitos si necesitas detectar el veto.

Un observer es un objeto con métodos nombrados como eventos; se registra con `Document.observe(observer)`. Si pasas una clase, se instancia sin argumentos: construye el objeto antes si necesita dependencias. `flushEvents(event=None)` limpia listeners y resulta útil para aislamiento de pruebas. El registro es por clase y se hereda al crear subclases; no registres listeners repetidamente durante cada petición.

Los eventos posteriores ocurren después de la sentencia, no después de la confirmación de una transacción exterior. Un listener `created` que envía correo puede ejecutarse antes de un rollback posterior. Diseña efectos externos con identidad y reintentos deliberados. Las escrituras masivas de builder no ejecutan cada ciclo de instancia.

## Eliminación lógica

Para activar soft deletes necesitas **tanto** `soft_deletes=True` como una columna de borrado declarada, normalmente `deleted_at`, anulable. La opción por sí sola no crea la columna. `DELETED_AT` cambia su nombre. Con definiciones compartidas, una columna no anulable se rechaza durante configuración.

`await document.delete()` estampa la fecha en vez de eliminar. Las consultas de modelo excluyen filas eliminadas por defecto; `withTrashed()` las incluye y `onlyTrashed()` devuelve solo eliminadas. `await document.restore()` borra la fecha y dispara eventos; `await document.forceDelete()` elimina definitivamente. `document.trashed()` consulta el estado local.

Los terminales de builder `.restore()` y `.forceDelete()` devuelven recuentos y no ejecutan listeners por instancia. `DB.table("documents")` ve filas eliminadas salvo que añadas el filtro; define conscientemente esa política al escribir informes y administración.

## Verificar reglas

Prueba el veto, la excepción y el éxito por separado. Comprueba que una consulta habitual excluya eliminados y que una consulta administrativa requiera una selección explícita. Si usas un scope para separar organizaciones, incluye tests de consultas crudas y de escrituras: el scope no establece una frontera de seguridad de base de datos.
