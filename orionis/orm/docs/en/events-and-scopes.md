# Events, scopes, and soft deletes

These mechanisms add model behavior without repeating filters and checks in every consumer. They do not replace application authorization; raw table queries can bypass them.

## Centralize filters with scopes

A local scope is a static or class method named `scope<Name>`. Its fluent name removes the prefix and starts lowercase. The scope modifies the builder synchronously:

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

Inside an application, `await Document.published().get()` applies the scope. `query.scope("published")` is an explicit alternative; an absent name raises `ScopeNotFoundException`. Register global scopes through `Document.addGlobalScope("policy", callback)`; they apply before execution. `withoutGlobalScope("policy")`, `withoutGlobalScopes(...)`, and `removeGlobalScope("policy")` omit or remove them at their respective scope. Do not change the global registry for one concurrent request: modify that request's builder.

## Listen to and veto persistence

Events are `retrieved`, `saving`, `creating`, `created`, `updating`, `updated`, `saved`, `deleting`, `deleted`, `restoring`, and `restored`. A listener receives the model and may be synchronous or async.

```python
def require_title(document: Document) -> bool:
    return bool(document.title.strip())


Document.registerEvent("saving", require_title)
```

Only `saving`, `creating`, `updating`, `deleting`, and `restoring` allow veto by returning exactly `False`. Consequently, `save()`, `delete()`, and `restore()` can return `False` without a SQL exception. Inspect that result when persistence is required. `Model.create()` returns an instance even if `save()` was vetoed; use explicit construction and `save()` to detect a veto.

Observers expose methods named after events and register through `Document.observe(observer)`. Passing a class instantiates it without arguments: build the object first when it requires dependencies. `flushEvents(event=None)` removes listeners and helps test isolation. Registrations are class-level and inherited when subclasses are created; do not repeatedly register listeners on every request.

After-events run after the statement, rather than after an outer transaction commits. A `created` listener sending email may run before a later rollback. Design external effects with deliberate identities and retry behavior. Bulk builder writes do not run every instance lifecycle.

## Logical deletion

Soft deletion requires **both** `soft_deletes=True` and a declared nullable deletion column, normally `deleted_at`. The flag alone does not create the column. `DELETED_AT` changes its name. Shared definitions with a non-nullable deletion column are rejected during configuration.

`await document.delete()` stamps a timestamp instead of removing the row. Model queries exclude deleted rows by default; `withTrashed()` includes them and `onlyTrashed()` returns only deleted rows. `await document.restore()` clears the timestamp and fires events; `await document.forceDelete()` removes the row permanently. `document.trashed()` inspects local state.

Builder `.restore()` and `.forceDelete()` terminals return counts without per-instance listeners. `DB.table("documents")` sees deleted rows unless explicitly filtered; choose that policy deliberately for reporting and administration.

## Verify rules

Test veto, exception, and success paths separately. Verify ordinary queries exclude deleted rows and administrative access requires an explicit choice. If a scope separates organizations, also test raw queries and writes: a scope is not a database security boundary.
