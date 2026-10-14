# Tipos y restricciones del esquema

Esta referencia complementa [modelos](models-and-attributes.md) y [creación de tablas](../../../database/docs/es/schema.md). Los tipos de Orionis producen `ColumnDefinition`; el compilador de Database los transforma al dialecto de destino. Son descripciones de almacenamiento, no schemas de validación de peticiones.

## Elegir tipos de columna

Los siguientes tipos se importan desde `orionis.orm` o `orionis.orm.schema.types`. Los parámetros opcionales relevantes aparecen entre paréntesis; los flags indicados con `=` son valores predeterminados.

| Familia | Tipos y opciones |
|---|---|
| Enteros genéricos | `Integer()`, `BigInteger()`, `SmallInteger()` |
| Booleanos | `Boolean(create_constraint=False, name=None)` |
| Texto | `String(length=255, collation=None)`, `Text(length=None, collation=None)` |
| Unicode | `Unicode(length=None, collation=None)`, `UnicodeText(length=None, collation=None)` |
| Fechas | `Date()`, `Time()`, `DateTime(timezone=False)` |
| Identidad UUID | `Uuid(as_uuid=True, native_uuid=True)` |
| Binarios | `LargeBinary(length=None)` |
| Números decimales | `Numeric(precision=None, scale=None, decimal_return_scale=None, asdecimal=True)` |
| Flotantes | `Float(precision=None, asdecimal=False, decimal_return_scale=None)`, `Double(...)` con las mismas opciones |
| Enumeración | `Enum(*enums, name=None, create_constraint=False, native_enum=True, length=None, validate_strings=False)` |
| Intervalo | `Interval(native=True, second_precision=None, day_precision=None)` |
| Objetos Python | `PickleType(protocol=5, pickler=None, impl=None)` |

Por ejemplo, `Numeric(12, 2)` expresa precisión/escala decimal; no uses float para decidir igualdad exacta de importes. La opción `timezone=True` pide un tipo temporal compatible, pero su resultado depende del motor y driver; no cambia por sí sola la zona horaria de la aplicación. `Enum` nativo y constraints de booleanos necesitan soporte del dialecto y una evolución deliberada al cambiar valores.

`PickleType` existe, pero la deserialización pickle requiere datos confiables; no lo uses para contenido que un tercero pueda modificar. El serializer de colas no utiliza este tipo.

## Tipos SQL explícitos

La familia `Strict` nombra variantes SQL concretas. No significa validación estricta de entrada Python ni garantía universal de portabilidad.

| Familia | Tipos |
|---|---|
| Enteros | `StrictInt()`, `StrictBigInt()`, `StrictSmallInt()` |
| Texto SQL | `StrictChar`, `StrictVarChar`, `StrictNChar`, `StrictNVarChar`, `StrictClob` |
| Binarios SQL | `StrictBinary`, `StrictVarBinary`, `StrictBlob` |
| Numéricos SQL | `StrictReal`, `StrictDoublePrecision`, `StrictDecimal` |
| JSON | `StrictJson(none_as_null=False)` |
| Timestamp | `StrictTimestamp(timezone=False)` |
| Array | `StrictArray(item_type, as_tuple=False, dimensions=None, zero_indexes=False)` |

Las variantes de texto aceptan `length` y `collation`; `StrictVarChar` usa longitud 255 por defecto y las otras, `None`. Binarios aceptan longitud opcional. `StrictReal`/`StrictDoublePrecision` reciben precisión y opciones de retorno como float. `StrictDecimal(precision=10, scale=2, decimal_return_scale=None, asdecimal=True)` exige precisión positiva y escala no negativa menor o igual a precisión; suministra ambas o ambas `None`.

`StrictArray(Integer())` declara el tipo de elemento; no presupongas soporte ARRAY fuera de un motor que lo implemente. `StrictJson` necesita igualmente un backend compatible. `SchemaType(name=None)`, `NumericCommon()` y `MatchType()` son descriptores auxiliares disponibles públicamente, no elecciones habituales para columnas de negocio. `ColumnType` identifica el vocabulario utilizado por los compiladores.

## Modificadores comunes

Todos los tipos de columna ofrecen `.primary()`, `.nullable()`, `.default(value)`, `.unique()`, `.index()`, `.foreign("table.column")`, `.autoIncrement()` y `.comment(text)`. Devuelven la misma definición; evita compartir una definición mutable entre columnas distintas.

`default` admite un valor estático o callable sin argumentos evaluado al insertar por el flujo compatible. No equivale a una expresión SQL de default arbitraria. `hasDefault()` distingue un default explícito, incluso `None`, de ausencia de default. `.foreign()` acepta exactamente `table.column`; para esquemas o claves compuestas usa las estructuras adecuadas en vez de inventar una cadena con más segmentos.

## Definir claves compuestas y tabla compartida

`TableDefinition` acepta `name`, `columns`, `primary_key="id"`, `schema=None`, `comment=None`, `composite_primary_key=None`, `unique_constraints=()`, `foreign_keys=()` e `indexes=()`. Las restricciones se importan de `orionis.orm.schema.constraints`:

```python
from orionis.orm import Integer
from orionis.orm.schema.constraints import CompositeForeignKey, TableIndex
from orionis.orm.schema.table import TableDefinition

team_id = Integer()
team_id.name = "team_id"
member_id = Integer()
member_id.name = "member_id"

TEAM_MEMBERS_V1 = TableDefinition(
    name="team_members",
    columns={"team_id": team_id, "member_id": member_id},
    primary_key="team_id",
    composite_primary_key=("team_id", "member_id"),
    foreign_keys=(
        CompositeForeignKey(("team_id",), "teams", ("id",)),
        CompositeForeignKey(("member_id",), "members", ("id",)),
    ),
    indexes=(TableIndex(("member_id",)),),
)
assert TEAM_MEMBERS_V1.hasColumn("member_id")
```

El ejemplo solo declara estructura. `CompositeForeignKey(columns, ref_table, ref_columns, name=None)` relaciona tuplas en el mismo orden; `UniqueConstraint(columns, name=None)` impone unicidad compuesta y `TableIndex(columns, name=None, unique=False)` declara índices. `ForeignReference(table, column)` representa una referencia simple.

Una PK compuesta del esquema no añade al Active Record una API completa de identidad compuesta: `find`, `save` y operaciones de instancia siguen usando su `primary_key` singular. Para tablas pivot utiliza relaciones y builders con filtros explícitos por todas las claves. Tampoco una declaración de constraint garantiza enforcement en Redshift; revisa [capacidades del motor](../../../database/docs/es/dialects-and-production.md).
