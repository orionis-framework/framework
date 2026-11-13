# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Reject malformed stored hashes through the installed password backends."""

from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher
from orionis.test import TestCase


class TestInvalidStoredHashes(TestCase):
    """Check malformed records without executing expensive attacker-selected costs."""

    async def testBcryptPreservesItsPasswordByteLimit(self) -> None:
        """Reject oversized bcrypt candidates without truncating their bytes.

        Returns
        -------
        None
            No return value.
        """
        hasher = BcryptHasher(rounds=4)
        for prefix, oversized in (("a" * 72, "a" * 73), ("é" * 36, "é" * 37)):
            with self.subTest(encoded_length=len(oversized.encode("utf-8"))):
                encoded = await hasher.make(prefix)
                self.assertTrue(await hasher.check(prefix, encoded))
                self.assertFalse(await hasher.check(oversized, encoded))
                with self.assertRaises(ValueError):
                    await hasher.make(oversized)

    async def testBcryptPreservesSupportedLegacyPrefixes(self) -> None:
        """Verify existing bcrypt prefixes and rehash non-default prefixes.

        Returns
        -------
        None
            No return value.
        """
        hasher = BcryptHasher(rounds=4)
        encoded = await hasher.make("candidate")
        for prefix in ("2a", "2b", "2x", "2y"):
            with self.subTest(prefix=prefix):
                legacy = f"${prefix}${encoded[4:]}"
                self.assertTrue(await hasher.check("candidate", legacy))
                self.assertEqual(hasher.needsRehash(legacy), prefix != "2b")

    async def testMalformedBcryptHashesAreRejected(self) -> None:
        """Reject invalid bcrypt cost and salt encodings during verification.

        Returns
        -------
        None
            No return value.
        """
        hasher = BcryptHasher(rounds=4)
        records = (
            "$2b$00$" + "a" * 53,
            "$2b$99$" + "a" * 53,
            "$2b$04$" + "+" * 53,
            "$2b$04$" + "a" * 53,
        )
        for encoded in records:
            with self.subTest(encoded=encoded, operation="check"):
                self.assertFalse(await hasher.check("candidate", encoded))
            with self.subTest(encoded=encoded, operation="needsRehash"):
                self.assertTrue(hasher.needsRehash(encoded))

    async def testMalformedArgon2HashesRequireRehash(self) -> None:
        """Mark malformed Argon2 records for replacement without raising.

        Returns
        -------
        None
            No return value.
        """
        hasher = Argon2Hasher(memory=32, threads=1, time=1)
        records = [
            "$argon2id$v=19$m=32,t=1,p=1",
            "$argon2id$v=19$m=32,t=1,p=1$" + "!" * 22 + "$" + "A" * 43,
            "$argon2id$v=19$m=32,t=1,p=1$" + "A" * 22 + "$" + "!" * 43,
        ]
        valid = await hasher.make("candidate")
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        for field in (-2, -1):
            parts = valid.split("$")
            value = parts[field]
            parts[field] = value[:-1] + alphabet[alphabet.index(value[-1]) + 1]
            records.append("$".join(parts))
        for encoded in records:
            with self.subTest(encoded=encoded):
                self.assertFalse(await hasher.check("candidate", encoded))
                self.assertTrue(hasher.needsRehash(encoded))
