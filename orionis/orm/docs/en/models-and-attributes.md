# Models, attributes, and persistence

## Define an entity

A concrete model extends `Model` and declares columns using types exported by `orionis.orm`. This example runs without a database:

```python
from typing import ClassVar
from orionis.orm import Boolean, Integer, Model, String


class Article(Model):
    id = Integer().primary().autoIncrement()
    title = String(180)
    status = String(30).default("draft")
    internal_token = String(80).nullable()
    published = Boolean().default(False)
    timestamps = False
    fillable: ClassVar[list[str]] = ["title", "status", "published"]
    hidden: ClassVar[list[str]] = ["internal_token"]
    casts: ClassVar[dict[str, str]] = {"published": "bool"}
    appends: ClassVar[list[str]] = ["label"]

    def setTitleAttribute(self, value: str) -> str:
        return value.strip()

    def getLabelAttribute(self, value=None) -> str:
        return self.title.upper()


article = Article({"title": " Orionis ", "published": "yes"})
assert Article.__meta__.table_name == "articles"
assert article.title == "Orionis"
assert article.published is True
assert article.toDict()["label"] == "ORIONIS"
assert article.isDirty("title")
```

The table name is derived through snake case and pluralization. Set `table = "content_articles"` when conventions do not fit, and `connection = "reporting"` for a registered connection. `primary_key`, `incrementing`, and `uuids` customize identity. `uuids=True` generates a client identity during save; also declare the column and adjust `incrementing` when the key is not server-generated.

Declare `created_at` and `updated_at` with date/time types for automatic timestamp maintenance. `timestamps=True` alone **does not add columns**. Customize names with `CREATED_AT` and `UPDATED_AT`. `table_definition` shares a versioned definition with [migrations](../../../database/docs/en/schema.md); it cannot be combined with inline columns or conflicting table/PK settings.

`freshTimestamp()` returns an aware instant in the application timezone. The ORM stores its managed creation, update, and soft-delete timestamps in UTC using each column's own timezone flag. Reading an offset-less value from these columns treats it as UTC, including historical rows. Assigning an offset-less timestamp to the model uses application time. Override `newUniqueId()` for a custom client-generated identity.

## Control input and output

The constructor, `fill()`, and `update(attributes)` apply mass-assignment rules. `fillable` is an allowlist; `guarded` blocks attributes and supports `"*"`. Unknown or disallowed columns raise `MassAssignmentException`. An empty `fillable` allows every non-guarded column: define an explicit policy for external input.

Direct assignment (`article.status = "published"`) and `setAttribute` apply mutators/casts but bypass `fillable`. Use them only in trusted logic. A mutator returns the stored value; casting follows. Available casts are `int`, `float`, `bool`, `datetime`, `date`, `json`, and `uuid`; `None` remains `None`. Casting does not replace input validation or SQL constraints.

The `datetime` cast returns a `pendulum.DateTime` in the application timezone. It interprets naive values as application-local time and converts timezone-aware values and POSIX timestamps without changing the instant they represent.

A user-defined column with a `datetime` cast stores local application time when its SQL type discards the offset. Historical values use the same convention. During a fall-back transition two instants can share that wall time. Preserving the distinction for user-defined fields requires a type and backend that retain the offset or an explicit UTC representation. The `date` cast extracts the application-local day from a `datetime` and preserves plain dates.

`toDict()`/`serialize()` convert attributes and loaded relationships; `hidden` excludes secrets and `appends` adds computed accessors. `toJson(**kwargs)` produces JSON. `only(*keys)` and `exclude(*keys)` select from the serialized representation. Hiding a column neither encrypts it nor prevents queries.

## Save and update

After bootstrap and table creation, application code can accept the model declared above:

```python
async def publish(article: Article) -> bool:
    article.status = "published"
    article.published = True
    return await article.save()
```

`save()` inserts new instances and updates only dirty attributes of retrieved instances. It returns `False` when a before-event vetoes the operation or an update finds no stored row. Successful after-events are not emitted for that failed write. `await Article.create({...})` returns the instance, but currently does not surface a `save()` veto as a boolean result: construct the model and inspect `await model.save()` when persistence must be explicitly checked.

Models retrieved through a selected connection retain that exact connection for later instance writes. New instances use their model connection policy.

`find(id)` and `first()` return a model or `None`; their `OrFail` variants raise `ModelNotFoundException`. Instance `update({...})` returns a boolean; `delete()` returns a boolean and respects soft deletes. [Builder operations](querying.md) return counts and differ from each instance's lifecycle.

`getDirty`, `isDirty`, `isClean`, `getOriginal`, `wasChanged`, and `getChanges` describe changes before/after save. A newly assigned attribute is dirty even when it has no original value. `syncOriginal()` publishes a new original snapshot only after every value has been copied successfully. They are not optimistic locking: concurrent writers can overwrite changes. Use [transactions](../../../database/docs/en/transactions.md) and appropriate locks where the backend supports them.
