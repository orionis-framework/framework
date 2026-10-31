# Consultar, actualizar y paginar

## Elegir modelos o tablas

`Article.query()` y los accesos de clase como `Article.where(...)` crean builders nuevos y recuperan modelos. `DB.table("articles")` crea un builder que devuelve diccionarios. Ambos utilizan el mismo lenguaje de consultas, pero la tabla cruda no aplica scopes, eventos, ocultación ni eliminación lógica del modelo.

Las cláusulas son síncronas. Solo espera el terminal: `await query.get()`, no `await query.where(...)`. Este plan se puede inspeccionar sin conexión:

```python
from orionis.orm import Integer, Model, String


class Article(Model):
    id = Integer().primary().autoIncrement()
    title = String(180)
    status = String(30)
    timestamps = False


base = Article.where("status", "published")
recent = base.clone().whereContains("title", "Orionis").orderBy("id", "desc").limit(10)
assert recent.toPlan().limit_value == 10
assert len(base.toPlan().wheres) == 1
```

Los builders mutan su propio estado: usa `clone()` para ramificar consultas y no compartas uno entre tareas concurrentes.

## Componer filtros seguros

`where("status", "published")` significa igualdad; `where("id", ">", 10)` especifica operador. Un callback agrupa condiciones:

```python
async def search_articles():
    return await (
        Article.where("status", "published")
        .where(lambda group: group.whereContains("title", "Python")
               .orWhere("title", "Orionis"))
        .whereIn("id", [1, 2, 3])
        .orderBy("id")
        .get()
    )
```

Ejecuta esta función en una aplicación inicializada con la tabla `articles`. También están disponibles `whereNull`, `whereNotNull`, `whereBetween`, `whereNotBetween`, `whereNotIn`, comparaciones con `whereColumn`, subconsultas `whereExists`/`whereNotExists` y filtros `whereLike`, `whereILike`, `whereStartsWith`, `whereEndsWith`, `whereRegexpMatch`. No todos los dialectos admiten las mismas expresiones de regex.

Valores se enlazan como parámetros. `whereRaw`, `selectRaw` y `havingRaw` aceptan SQL confiable y bindings; no interpolan de forma segura texto arbitrario. Controla columnas, operadores y ordenación desde una lista permitida cuando provienen de una petición.

## Inspeccionar SQL

`toSql(*, literal_binds=False) -> str` es síncrono y utiliza el dialecto y prefijo de la conexión seleccionada. Requiere una aplicación inicializada o un `ConnectionResolver` configurado, pero no crea un motor ni abre conexiones a la base de datos. La tabla no necesita existir para compilar el SQL.

```python
query = Article.where("status", "published").whereIn("id", [1, 2]).limit(10)
sql = query.toSql()
debug_sql = query.toSql(literal_binds=True)
```

También funciona con `DB.table(...)` y directamente desde la clase del modelo, como `Article.toSql()`. Por defecto conserva placeholders, cuyo formato depende del dialecto, y expande los parámetros de `IN`. Los scopes globales y el filtro de eliminación lógica se aplican sobre un clon: inspeccionar no modifica el builder original.

`literal_binds=True` incluye valores con el escape del dialecto para depuración. **Puede revelar datos sensibles** y algunos tipos, como JSON o valores personalizados, no tienen representación literal y producen `QueryException`. No uses la salida literal como sustituto de la ejecución parametrizada.

La salida describe el SELECT del plan actual. No anticipa cambios de un terminal posterior ni consultas adicionales de relaciones o paginación, y no compila escrituras.

## Proyectar, unir y agrupar

Este fragmento de aplicación produce un informe con tablas crudas existentes:

```python
from orionis.support.facades import DB


async def articles_by_author():
    return await (
        DB.table("articles", alias="a")
        .join("authors", "a.author_id", "=", "u.id", alias="u")
        .select("u.id", "u.name")
        .selectRaw("COUNT(*) AS article_count")
        .groupBy("u.id", "u.name")
        .havingRaw("COUNT(*) > :minimum", {"minimum": 1})
        .orderBy("u.id")
        .get()
    )
```

`leftJoin`, `rightJoin`, `fullJoin`, `crossJoin`, `joinSub` y sus variantes permiten otras formas; su compatibilidad depende del motor. Usa nombres calificados para evitar ambigüedad. `select`, `addSelect`, `selectSub`, `distinct`, `union` y `unionAll` completan las proyecciones. Para modelos que después se guardarán o cargarán relaciones, conserva PK y claves de relación en la selección.

## Resultados y paginación

| Terminal async | Resultado |
|---|---|
| `get()` | `Collection` de modelos o diccionarios. |
| `first()` / `find(key)` | Un resultado o `None`. |
| `firstOrFail()` / `findOrFail(key)` | Modelo; error si no existe, solo en builder de modelos. |
| `value(column)` / `pluck(column)` | Un valor o colección de valores. |
| `count`, `exists`, `doesntExist` | Entero o booleano. |
| `min`, `max`, `avg`, `sum` | Agregado; `sum` devuelve 0 sin resultados. |
| `paginate(page=1, per_page=15)` | `Paginator` con items y metadatos. |

`limit`, `offset`, `take`, `skip` y `forPage` componen límites sin ejecutar. Usa orden determinista, incluyendo una clave única, para páginas estables. `Paginator` expone `items`, `total`, `page`, `perPage`, `lastPage`, `hasNext`, `hasPrevious` y `toDict()`/`toJson()`. Recuento y lectura son dos consultas: fuera de una transacción pueden observar cambios distintos y ejecutarse concurrentemente; dentro se ejecutan en secuencia. Página y tamaño deben ser enteros positivos.

## Escrituras y locks

`await DB.table("articles").insert({...})` devuelve `InsertResult`; admite también lista de filas. `update(values)` y `delete()` devuelven recuentos. **Sin filtro afectan a todas las filas**. No añadas `limit()` suponiendo que limita la escritura: los planes update/delete se construyen con las condiciones, no con la paginación de lectura.

Las escrituras masivas no hidratan cada modelo ni ejecutan su `fillable`, mutadores o eventos de instancia. Usa instancias cuando necesites esas reglas. El builder de modelos mantiene timestamps de actualización y políticas de soft delete; las tablas crudas no.

`lockForUpdate()` y `sharedLock()` se usan dentro de una [transacción](../../../database/docs/es/transactions.md), siempre según soporte del backend. Redshift los rechaza. Una consulta limitada materializa su resultado; no existe aquí una promesa de cursor streaming. Los fallos de composición producen `InvalidQueryException`; ejecución/compilación SQL produce errores de la capa de base de datos.
