# Authentication and authorization

Orionis resolves the current identity through browser sessions or personal access tokens and evaluates permissions, roles and policies. Context belongs to a request; shared services do not retain a global user.

1. [Identity and session login](identity-and-session.md): models, guards, login and logout.
2. [Permissions, roles and policies](authorization.md): protect capabilities and resources.
3. [Personal access tokens](personal-access-tokens.md): issue, restrict and revoke credentials.
4. [Remember-me and account recovery](account-recovery.md): persistent cookies, resets and default pages.

Requires Python 3.14+, a configured ORM identity model, hashing and authentication migrations for persistence. Facade/repository examples require a booted application; snapshot examples are independent. Review [sessions](../../../session/docs/en/README.md), [HTTP](../../../http/docs/en/README.md) and [ORM](../../../orm/docs/en/README.md).
