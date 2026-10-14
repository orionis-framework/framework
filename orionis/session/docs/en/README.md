# HTTP sessions

Sessions keep data on the server and send only a random identifier to the browser. Orionis creates sessions lazily: reading an empty session does not automatically create a record or cookie. Web middleware coordinates restoration, flash, persistence and cleanup.

1. [State and flash](state-and-flash.md): preferences, forms and navigation between requests.
2. [Storage and concurrency](stores-and-concurrency.md): choose a driver and implement a store.
3. [Configuration and secure lifecycle](configuration-and-security.md): cookies, renewal and rotation.

You need Python 3.14+ and web routes for automatic persistence. `orionis.session` exports no classes at its root: inject `ISession`, use the `Session` facade or import implementations from their modules. Start with [HTTP](../../../http/docs/en/README.md) and continue with [authentication](../../../auth/docs/en/README.md).
