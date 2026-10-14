# Relate and load models

A relationship is an instance method returning a specialized builder. Methods let models refer to each other without resolving relationships while their classes are being declared.

## One-to-many and inverse relationships

```python
from typing import ClassVar
from orionis.orm import Integer, Model, String


class Team(Model):
    id = Integer().primary().autoIncrement()
    name = String(120)
    timestamps = False
    fillable: ClassVar[list[str]] = ["name"]

    def players(self):
        return self.hasMany(Player)


class Player(Model):
    id = Integer().primary().autoIncrement()
    team_id = Integer().nullable()
    name = String(120)
    timestamps = False
    fillable: ClassVar[list[str]] = ["team_id", "name"]

    def team(self):
        return self.belongsTo(Team)
```

After creating `teams` and `players` and bootstrapping the application:

```python
async def recruit(team_id: int):
    team = await Team.findOrFail(team_id)
    player = await team.players().create({"name": "Ada"})
    teammates = await team.players().orderBy("id").get()
    owner = await player.team().getResults()
    return player, teammates, owner
```

`hasMany` resolves to a collection; `hasOne` and `belongsTo` resolve to a model or `None` through `getResults()`. Relationship `first()` returns the first model. `hasOne` does not impose database uniqueness: a true one-to-one relationship needs a unique constraint on its FK.

Conventions use `team_id` on `Player` for both `Team.hasMany(Player)` and `Player.belongsTo(Team)`, with the primary key as local/owner key. Customize through `hasMany(Player, foreign_key="owner_id", local_key="id")`, `hasOne(...)`, or `belongsTo(Team, foreign_key="owner_id", owner_key="id")`. Relationship builders retain these constraints when adding filters.

## Load a list without N+1 queries

```python
async def roster():
    teams = await Team.withRelations("players").orderBy("id").get()
    return [
        {"team": team.name, "players": [p.toDict() for p in team.getRelation("players")]}
        for team in teams
    ]
```

`withRelations("players")` loads the relationship for the batch and stores results through `setRelation`. `relationLoaded(name)` reports whether it was loaded; `getRelation(name, default=None)` retrieves it without querying. Calling `team.players()` constructs another relationship: use the stored result to avoid additional queries.

`ModelQueryBuilder.load(*names)` is a fluent eager-loading alias, rather than an async loader for an already retrieved instance. Nested paths such as `"players.team"` and restriction callbacks in `withRelations` are not supported by the implementation described here; use direct names and explicit queries for additional levels. Missing relationships raise `RelationNotFoundException` when executing a query with results.

## Many-to-many relationships

Declare a method returning `self.belongsToMany(Role)`, or specify names: `self.belongsToMany(Role, table="role_user", foreign_pivot_key="user_id", related_pivot_key="role_id")`. The default pivot table combines singular snake-case class names in alphabetical order; keys derive from each class.

For a relationship on a persisted user:

```python
async def replace_roles(user, role_ids: list[int]):
    return await user.roles().sync(role_ids)
```

This fragment requires an application model with a `roles()` method and a migrated pivot table. `attach(ids, attributes=None)` inserts links and returns a count; it accepts one identity, models, iterables, or an identity-to-pivot-attributes mapping. `detach(ids=None)` removes links; without arguments it removes all links for the parent. `sync(ids)` retains exactly those identities and returns `attached` and `detached` lists; `toggle(ids)` reverses links. `wherePivot(column, value)` or `(column, operator, value)` filters pivot reads.

The current implementation has no `updateExistingPivot` method or implicit atomic synchronization: `sync` reads, deletes, and inserts in separate steps. Wrap critical workflows in a [transaction](../../../database/docs/en/transactions.md) on the same connection and define a composite unique constraint to prevent duplicates. `detach` removes links; relationship `delete()` deletes related rows. Choose according to the intended business effect.
