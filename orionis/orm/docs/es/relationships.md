# Relacionar y cargar modelos

Una relación es un método de instancia que devuelve un builder especializado. Se declara mediante métodos para que dos modelos puedan referenciarse sin resolver la relación durante la definición de la clase.

## Uno a muchos y relación inversa

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

Después de crear `teams` y `players` y arrancar la aplicación:

```python
async def recruit(team_id: int):
    team = await Team.findOrFail(team_id)
    player = await team.players().create({"name": "Ada"})
    teammates = await team.players().orderBy("id").get()
    owner = await player.team().getResults()
    return player, teammates, owner
```

`hasMany` devuelve colección; `hasOne` y `belongsTo` devuelven modelo o `None` a través de `getResults()`. `first()` sobre una relación devuelve el primer modelo. `hasOne` no impone unicidad en la base: una relación realmente uno a uno necesita una restricción única sobre la FK.

Las convenciones son `team_id` en `Player` para `Team.hasMany(Player)` y para `Player.belongsTo(Team)`, y PK como clave local/propietaria. Personaliza con `hasMany(Player, foreign_key="owner_id", local_key="id")`, `hasOne(...)` o `belongsTo(Team, foreign_key="owner_id", owner_key="id")`. Los builders de relación mantienen esas condiciones al añadir filtros.

## Cargar una lista sin N+1

```python
async def roster():
    teams = await Team.withRelations("players").orderBy("id").get()
    return [
        {"team": team.name, "players": [p.toDict() for p in team.getRelation("players")]}
        for team in teams
    ]
```

`withRelations("players")` carga la relación para todo el lote y guarda resultados con `setRelation`. `relationLoaded(name)` comprueba si se cargó; `getRelation(name, default=None)` la recupera sin otra consulta. Acceder al método `team.players()` construye otra relación: usa el resultado cargado si quieres evitar consultas adicionales.

`ModelQueryBuilder.load(*names)` es un alias fluido de eager loading, no un método async para cargar una instancia ya recuperada. No hay soporte demostrado aquí para rutas de eager loading anidadas como `"players.team"` ni callbacks de restricción en `withRelations`; utiliza nombres directos y consultas explícitas cuando necesites más niveles. Una relación inexistente produce `RelationNotFoundException` al ejecutar una consulta con resultados.

## Muchos a muchos

Declara un método con `return self.belongsToMany(Role)` o explicita sus nombres: `self.belongsToMany(Role, table="role_user", foreign_pivot_key="user_id", related_pivot_key="role_id")`. La tabla pivot predeterminada combina los nombres de clases en snake case y orden alfabético, sin pluralizar; las claves derivan de cada clase.

Sobre una relación de usuario persistido:

```python
async def replace_roles(user, role_ids: list[int]):
    return await user.roles().sync(role_ids)
```

Este fragmento requiere un modelo de aplicación con método `roles()` y su pivot ya migrada. `attach(ids, attributes=None)` inserta vínculos y devuelve recuento; admite una identidad, modelos, iterables o un mapping de identidad a atributos pivot. `detach(ids=None)` desvincula; sin argumento elimina todos los vínculos del padre. `sync(ids)` deja exactamente esas identidades y devuelve listas `attached` y `detached`; `toggle(ids)` invierte vínculos. `wherePivot(column, value)` o `(column, operator, value)` restringe lecturas pivot.

La implementación actual no tiene `updateExistingPivot` ni ofrece sincronización atómica implícita: `sync` consulta, elimina e inserta en pasos. Para operaciones críticas envuelve el flujo en una [transacción](../../../database/docs/es/transactions.md) de la misma conexión y define una restricción única compuesta para evitar duplicados. `detach` elimina vínculos; `delete()` sobre una relación elimina filas relacionadas. Elige deliberadamente según el efecto de negocio.
