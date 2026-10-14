# Remember-me, recovery and email verification

Persistent authentication and recovery use credentials separate from personal API tokens. They require an ORM identity, authentication migrations, hashing and email delivery. Default controllers are a starting integration to adapt to your application's model and views.

## Remembering a browser

`await Auth.attempt(credentials, remember=True)` issues a persistent credential after password verification. The identity needs a `remember_token` column. Restoration rotates it without extending its original deadline and fails closed for invalid/expired cookies, inactive users, changed passwords or rotation failure.

`AUTH_REMEMBER_COOKIE` defaults to `orionis_remember`, `AUTH_REMEMBER_LIFETIME` to 43200 minutes and `AUTH_REMEMBER_SECURE` to true. Secure mode does not restore over HTTP. The name must differ from the session cookie. Test the appropriate scheme rather than disabling HTTPS in a production flow.

## Recovering a password

```python
from orionis.auth.passwords.broker import PasswordBroker

async def reset_password(broker: PasswordBroker, email: str, token: str, password: str) -> bool:
    identity = await broker.reset(email, token, password)
    return identity is not None
```

`issue(email)` returns `(identity, plain_token)` or `None`; callers must deliver the secret privately. `valid(email, token)` checks without consuming and does not reserve the token: another request may consume it first. `reset` combines checking/consumption and password change in a transaction; do not call only `valid` and then write a hash separately.

The broker normalizes email, stores a secret hash and conditionally checks the previous password to resolve races. It rejects consumed, expired and previous-password-bound tokens. The flow clears `remember_token` and revokes personal tokens; check these guarantees before adding custom mechanisms. Validate application password requirements before calling the service.

`AUTH_PASSWORD_RESET_EXPIRATION` defaults to 60 minutes, `AUTH_PASSWORD_RESET_THROTTLE` to 60 seconds and `AUTH_PASSWORD_RESET_TABLE` to `password_reset_tokens`. Use a uniform public response for link requests so callers cannot discover account existence.

## Pages and verification email

`Route.auth()` registers login, sign-up, forgot-password, reset-password, verify-email and POST logout. Controllers use application-flow views and schemas; registration explicitly depends on `app.models.user.User`. Replace individual controllers through `Route.auth` arguments when your domain differs. Reset links run in background work after returning a response; this is not a durable queue and process failure may prevent delivery.

The `MustVerifyEmail` marker makes default registration create an inactive identity and send verification. It is not a complete verification service: the link encrypts the identifier without a dedicated expiration deadline. Build explicit policy for expiring or single-use links. Verification should not become implicit login.

Keep CSRF on forms, private/no-store responses and abuse controls. Review default registration exception handling for production because it can present the error message in the form. Provider errors must not disclose secrets.

Evidence: [remember](../../remember.py), [broker](../../passwords/broker.py), [routes](../../../http/routes/auth.py), [registration](../../../http/default/controllers/register_controller.py), [recovery](../../../http/default/controllers/forgot_password_controller.py). Tests: [remember](../../../../tests/auth/test_remember.py), [reset](../../../../tests/auth/test_password_reset.py), [routes](../../../../tests/auth/test_auth_routes.py). Related: [HTTP pages](../../../http/docs/en/default-responses.md).
