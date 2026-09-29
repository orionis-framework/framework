import secrets

class SecretKey:

    @staticmethod
    def random(length: int = 32) -> str:
        """
        Generate a cryptographically secure random key as a hexadecimal string.

        Parameters
        ----------
        length : int, optional
            Length of the key in bytes. Default is 32.

        Returns
        -------
        str
            Randomly generated key represented as a hexadecimal string.
        """
        # Generate a secure random key and return as hex string
        return secrets.token_hex(length)
