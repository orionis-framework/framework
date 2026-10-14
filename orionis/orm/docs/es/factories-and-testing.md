# Factories y pruebas

Una factory construye modelos de ejemplo mediante su constructor normal. Úsala para tests y datos de desarrollo; las factories no descubren relaciones, migran tablas ni convierten automáticamente contraseñas en hashes.

## Generar datos reproducibles sin persistir

```python
from typing import ClassVar
from orionis.orm import Integer, Model, String
from orionis.orm.factories import Factory, Sequence


class Product(Model):
    id = Integer().primary().autoIncrement()
    name = String(120)
    status = String(30)
    timestamps = False
    fillable: ClassVar[list[str]] = ["name", "status"]


class ProductFactory(Factory[Product]):
    model = Product

    def definition(self) -> dict:
        return {"name": self.fake.word(), "status": "draft"}


products = ProductFactory(seed=7).count(2).sequence(
    Sequence({"status": "draft"}, {"status": "published"})
).make()
assert [product.status for product in products] == ["draft", "published"]
assert all(product.isDirty("name") for product in products)
```

`definition()` debe ser síncrono y devolver un diccionario. `model` debe ser un modelo concreto. `make()` no usa la base ni dispara eventos de persistencia: con count 1 devuelve un modelo; con otra cantidad devuelve `Collection`. `count(0)` permite colección vacía. `seed` afecta al generador aleatorio de esa instancia, evitando depender del estado aleatorio de otro test.

## Estados, secuencias y overrides

`state({...})` añade un estado fijo; `state(callable)` permite derivar atributos del diccionario previo. Los estados se aplican en orden, luego la secuencia y finalmente los overrides de `make(name="Fixed")` o `create(name="Fixed")`. Conserva los nombres del modelo y sus reglas `fillable` en todos los niveles. Los atributos anidados se copian para evitar compartir accidentalmente un diccionario entre modelos.

`Sequence({...}, {...})` rota estados; admite estados callable según el contrato de secuencia. El índice pertenece a la factory y avanza entre generaciones. No dependas de un índice global compartido entre tests.

`self.fake` es la facade de Faker con nombres camelCase: `firstName()`, `safeEmail()` y `word()` son ejemplos. `locale=` selecciona idioma; sin él se intenta `app.locale` y se utiliza `en_US` si no hay configuración/locale usable. `fake.unique` conserva valores vistos por esa instancia; `clearUnique()` permite reiniciar ese registro. Unicidad de Faker no garantiza unicidad contra filas existentes en la base. No uses estos datos para credenciales reales.

`fake.optional` ofrece una vista de proveedores con parámetro `prob`; `fake.addProvider(provider)` registra proveedores personalizados e invalida métodos cacheados. `seedInstance(seed)` y `seedLocale(locale, seed)` permiten reseed explícito; `locales` devuelve una lista independiente. `UniqueFake` y `OptionalFake` están exportadas para tipado y extensión de estas vistas, sin exponer servicios dentro de los atributos generados.

## Persistir con control de fallos

Con la aplicación inicializada y `products` migrada:

```python
from orionis.support.facades import DB


async def create_catalog():
    async with DB.transaction():
        return await ProductFactory(seed=7).count(3).create(status="published")
```

`create()` espera `save()` de cada modelo, ejecuta mutadores/casts/eventos y devuelve la misma cardinalidad que `make()`. **No abre una transacción por sí mismo**: si el tercer modelo falla, los anteriores persisten salvo transacción del llamador. Un veto de evento produce `FactoryPersistenceException`, a diferencia de la comodidad `Model.create()` que devuelve su instancia sin exponer ese veto como booleano.

## Generar por iteración

`iterMake()` produce modelos progresivamente sin colección completa; `iterCreate()` es un iterador async que guarda uno a uno. Cierra un iterador parcialmente consumido antes de reutilizar la factory. Para un iterador async usa `contextlib.aclosing` cuando interrumpas anticipadamente:

```python
from contextlib import aclosing


async def create_first_product():
    factory = ProductFactory(seed=7).count(100)
    async with aclosing(factory.iterCreate()) as stream:
        async for product in stream:
            return product
```

Este ejemplo persiste solo el primero y necesita infraestructura de base. No es una API de lectura streaming del ORM.

Una factory conserva contador, estados, secuencia y estado de Faker. Su uso solapado o reconfiguración durante iteración produce `FactoryConcurrencyException`: crea una instancia por tarea. `FactoryConfigurationException` y `FactoryDefinitionException` distinguen definición inválida de error de persistencia. Los fallos SQL conservan los errores de la capa de base de datos.

Para pruebas aisladas, usa SQLite en memoria y un gestor/resolver propios, como los tests del módulo. `ConnectionResolver.setManager(manager)` instala el puente global y `clear()` lo elimina; no sustituyas ese global mientras otras pruebas/tareas consultan. Las pruebas de dialecto requieren el servidor correspondiente. Integra estas prácticas con el módulo [Testing](../../../test/docs/es/README.md).
