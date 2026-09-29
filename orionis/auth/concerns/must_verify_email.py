class MustVerifyEmail:
    """
    Require identities to verify their email address before activation.

    Applications mix this marker into the model that requires email
    verification. Models without it do not enter the verification flow.
    """
