# Query, update, and paginate

## Choose models or tables

`Article.query()` and class entry points such as `Article.where(...)` create fresh builders returning models. `DB.table("articles")` creates a builder returning dictionaries. They share a query language, but raw table queries do not apply model scopes, events, hidden attributes, or soft deletion.

Clauses are synchronous. Await only the terminal: `await query.get()`, rather than `await query.where(...)`. This plan can be inspected without a connection:

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

Builders mutate their own state: use `clone()` when branching and do not share one builder between concurrent tasks.

## Compose safe filters

`where("status", "published")` means equality; `where("id", ">", 10)` supplies an operator. A callback groups conditions:

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

Run this function inside a booted application with the `articles` table. Other predicates include `whereNull`, `whereNotNull`, `whereBetween`, `whereNotBetween`, `whereNotIn`, `whereColumn`, `whereExists`/`whereNotExists` subqueries, and `whereLike`, `whereILike`, `whereStartsWith`, `whereEndsWith`, `whereRegexpMatch`. Regex support differs by dialect.

Values are bound as parameters. `whereRaw`, `selectRaw`, and `havingRaw` accept trusted SQL and bindings; they do not safely interpolate arbitrary text. Allowlist column names, operators, and ordering received from requests.

## Project, join, and group

This application fragment produces a report over existing raw tables:

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

`leftJoin`, `rightJoin`, `fullJoin`, `crossJoin`, `joinSub`, and their variants cover other forms, subject to backend support. Qualify names to avoid ambiguity. `select`, `addSelect`, `selectSub`, `distinct`, `union`, and `unionAll` extend projections. Include the primary and relationship keys when selecting models that will later be saved or related.

## Results and pagination

| Async terminal | Result |
|---|---|
| `get()` | `Collection` of models or dictionaries. |
| `first()` / `find(key)` | One result or `None`. |
| `firstOrFail()` / `findOrFail(key)` | Model or missing-result error; model builders only. |
| `value(column)` / `pluck(column)` | One value or a collection of values. |
| `count`, `exists`, `doesntExist` | Integer or boolean. |
| `min`, `max`, `avg`, `sum` | Aggregate; `sum` returns 0 without results. |
| `paginate(page=1, per_page=15)` | `Paginator` containing items and metadata. |

`limit`, `offset`, `take`, `skip`, and `forPage` compose bounds without executing. Use deterministic ordering, including a unique key, for stable pages. `Paginator` exposes `items`, `total`, `page`, `perPage`, `lastPage`, `hasNext`, `hasPrevious`, and `toDict()`/`toJson()`. Count and fetch are two queries: outside transactions they may observe different changes and run concurrently; inside they run sequentially. Page and page size must be positive integers.

## Writes and locks

`await DB.table("articles").insert({...})` returns `InsertResult` and also accepts a list of rows. `update(values)` and `delete()` return counts. **Without filters they affect every row**. Do not assume `limit()` bounds writes: update/delete plans use conditions, rather than read pagination.

Bulk writes do not hydrate each model or run its `fillable`, mutators, or instance events. Use instances when those rules are required. Model builders maintain update timestamps and soft-delete policy; raw tables do not.

Use `lockForUpdate()` and `sharedLock()` inside a [transaction](../../../database/docs/en/transactions.md), subject to backend support. Redshift rejects them. Bounded queries materialize results; this API does not promise cursor streaming. Composition failures raise `InvalidQueryException`; SQL compilation/execution failures come from the database layer.
