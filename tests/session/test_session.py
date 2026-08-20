from __future__ import annotations
from orionis.session.flash import ERRORS_KEY, OLD_INPUT_KEY
from orionis.session.session import Session
from orionis.test import TestCase

class _FakeValidationException(Exception):
    """Duck-typed validation exception exposing a full error bag."""

    def __init__(self, errors: dict[str, list[str]]) -> None:
        """
        Store the error bag reported by the schema layer.

        Parameters
        ----------
        errors : dict[str, list[str]]
            Field-indexed validation messages.

        Returns
        -------
        None
        """
        super().__init__("invalid")
        self.errors = errors

class TestSession(TestCase):
    """Unit tests for the Session runtime object."""

    # ── Construction ─────────────────────────────────────────────────────────

    def testDefaultInitHasNullIdentifier(self) -> None:
        """
        Yield None as the identifier for a brand-new session.

        Validates that a session constructed without arguments has no
        identifier assigned before the first write.
        """
        session = Session()
        self.assertIsNone(session.id)

    def testDefaultInitNotStarted(self) -> None:
        """
        Mark a brand-new session as not yet started.

        Validates that the started flag is False when no arguments are
        supplied to the constructor.
        """
        session = Session()
        self.assertFalse(session.started)

    def testDefaultInitNotDirty(self) -> None:
        """
        Leave the dirty flag clear on a freshly constructed session.

        Validates that a new session has no pending write when no
        mutations have been applied.
        """
        session = Session()
        self.assertFalse(session.dirty)

    def testDefaultInitNotInvalidated(self) -> None:
        """
        Leave the invalidated flag clear on construction.

        Validates that a new session is not scheduled for deletion
        unless invalidate() is explicitly called.
        """
        session = Session()
        self.assertFalse(session.invalidated)

    def testDefaultInitIsNew(self) -> None:
        """
        Report isNew as True for a session not loaded from a store.

        Validates that the default construction path marks the session
        as a new one that was not restored from backing storage.
        """
        session = Session()
        self.assertTrue(session.isNew)

    def testDefaultInitWantsRegenerateFalse(self) -> None:
        """
        Leave wantsRegenerate clear on construction.

        Validates that a new session does not request ID rotation until
        regenerate() is explicitly invoked.
        """
        session = Session()
        self.assertFalse(session.wantsRegenerate)

    def testInitWithExplicitId(self) -> None:
        """
        Store the provided identifier verbatim.

        Validates that passing an explicit id string sets the session
        identifier without modification.
        """
        session = Session(id="abc123")
        self.assertEqual(session.id, "abc123")

    def testInitWithExplicitData(self) -> None:
        """
        Preserve the provided data dictionary.

        Validates that passing an initial data mapping makes those
        key-value pairs accessible through get().
        """
        session = Session(data={"key": "value"})
        self.assertEqual(session.get("key"), "value")

    def testInitWithNoneDataDefaultsToEmpty(self) -> None:
        """
        Default to an empty dict when data is None.

        Validates that omitting the data argument produces a session
        with no pre-existing keys.
        """
        session = Session(data=None)
        self.assertEqual(session.all(), {})

    def testInitWithStartedTrue(self) -> None:
        """
        Honor the started flag passed at construction.

        Validates that pre-built sessions restored from a backing store
        correctly report their started state.
        """
        session = Session(id="x", started=True)
        self.assertTrue(session.started)

    def testInitWithIsNewFalse(self) -> None:
        """
        Honor is_new=False for sessions restored from a store.

        Validates that sessions loaded from a backing store are not
        misclassified as brand-new sessions.
        """
        session = Session(id="x", is_new=False)
        self.assertFalse(session.isNew)

    # ── put / get ────────────────────────────────────────────────────────────

    def testPutActivatesSession(self) -> None:
        """
        Activate the session on the first put call.

        Validates that calling put() sets both the started flag and
        assigns a non-None identifier.
        """
        session = Session()
        session.put("key", "value")
        self.assertTrue(session.started)
        self.assertIsNotNone(session.id)

    def testPutMarksDirty(self) -> None:
        """
        Mark the session dirty after storing a value.

        Validates that a write via put() signals the manager that
        the session must be persisted before the response is sent.
        """
        session = Session()
        session.put("x", 1)
        self.assertTrue(session.dirty)

    def testPutSameValueIsNoOp(self) -> None:
        """
        Skip the dirty flag when the value is unchanged.

        Validates that writing the same value a second time does not
        re-mark the session as dirty, avoiding unnecessary store writes.
        """
        session = Session()
        session.put("x", 42)
        session._markClean()
        session.put("x", 42)
        self.assertFalse(session.dirty)

    def testPutDifferentValueMarksDirty(self) -> None:
        """
        Dirty the session when an existing key receives a new value.

        Validates that updating a key from one value to another
        correctly triggers the dirty flag.
        """
        session = Session()
        session.put("x", 1)
        session._markClean()
        session.put("x", 2)
        self.assertTrue(session.dirty)

    def testGetReturnsStoredValue(self) -> None:
        """
        Return the value stored under the requested key.

        Validates that get() retrieves exactly what was stored by put().
        """
        session = Session()
        session.put("name", "Alice")
        self.assertEqual(session.get("name"), "Alice")

    def testGetReturnsDefaultWhenAbsent(self) -> None:
        """
        Return the default when the key is not present.

        Validates that get() falls back to the supplied default when
        the session does not contain the requested key.
        """
        session = Session()
        result = session.get("missing", "fallback")
        self.assertEqual(result, "fallback")

    def testGetReturnsNoneByDefault(self) -> None:
        """
        Return None as the implicit default for absent keys.

        Validates that get() returns None when no default argument
        is provided and the key does not exist.
        """
        session = Session()
        self.assertIsNone(session.get("missing"))

    # ── has ──────────────────────────────────────────────────────────────────

    def testHasReturnsTrueForExistingKey(self) -> None:
        """
        Confirm key presence after a put operation.

        Validates that has() reports True immediately after a value is
        written under the tested key.
        """
        session = Session()
        session.put("present", True)
        self.assertTrue(session.has("present"))

    def testHasReturnsFalseForMissingKey(self) -> None:
        """
        Report False for a key that was never written.

        Validates that has() correctly distinguishes absent keys from
        keys that hold a falsy value.
        """
        session = Session()
        self.assertFalse(session.has("ghost"))

    # ── forget ───────────────────────────────────────────────────────────────

    def testForgetRemovesExistingKey(self) -> None:
        """
        Remove a key from the session via forget().

        Validates that after forget() the key is no longer accessible
        through get() or has().
        """
        session = Session(id="s", data={"a": 1}, started=True)
        session.forget("a")
        self.assertFalse(session.has("a"))

    def testForgetMarksDirtyWhenStarted(self) -> None:
        """
        Dirty the session after removing an existing key from a started session.

        Validates that deleting a key triggers a store write by setting
        the dirty flag when the session has already been activated.
        """
        session = Session(id="s", data={"a": 1}, started=True)
        session.forget("a")
        self.assertTrue(session.dirty)

    def testForgetAbsentKeyIsNoOp(self) -> None:
        """
        Silently ignore forget() calls for non-existent keys.

        Validates that calling forget() on a key that does not exist
        neither raises an exception nor marks the session dirty.
        """
        session = Session(id="s", data={}, started=True)
        session.forget("ghost")
        self.assertFalse(session.dirty)

    def testForgetDoesNotDirtyUnstartedSession(self) -> None:
        """
        Skip dirty-marking when the session has not been started.

        Validates that removing a key from a never-written session does
        not trigger a persistence cycle.
        """
        session = Session(data={"a": 1})
        session.forget("a")
        self.assertFalse(session.dirty)

    # ── clear ────────────────────────────────────────────────────────────────

    def testClearRemovesAllKeys(self) -> None:
        """
        Remove all key-value pairs from the session.

        Validates that clear() leaves the session payload empty
        regardless of how many keys were previously stored.
        """
        session = Session(id="s", data={"a": 1, "b": 2}, started=True)
        session.clear()
        self.assertEqual(session.all(), {})

    def testClearMarksDirtyWhenStarted(self) -> None:
        """
        Dirty the session after clearing non-empty data.

        Validates that clear() signals the manager to delete the
        session record from the backing store.
        """
        session = Session(id="s", data={"a": 1}, started=True)
        session.clear()
        self.assertTrue(session.dirty)

    def testClearOnEmptyDataDoesNotDirty(self) -> None:
        """
        Skip dirty-marking when there is nothing to clear.

        Validates that clear() on an already-empty session avoids an
        unnecessary round-trip to the backing store.
        """
        session = Session(id="s", data={}, started=True)
        session.clear()
        self.assertFalse(session.dirty)

    # ── flash / getFlash ─────────────────────────────────────────────────────

    def testFlashActivatesSession(self) -> None:
        """
        Activate the session on the first flash call.

        Validates that flash() behaves like put() with respect to
        session activation and ID assignment.
        """
        session = Session()
        session.flash("msg", "hello")
        self.assertTrue(session.started)
        self.assertIsNotNone(session.id)

    def testFlashMarksDirty(self) -> None:
        """
        Mark the session dirty after storing a flash value.

        Validates that flash() triggers a persistence cycle so the
        flash bag is written to the backing store.
        """
        session = Session()
        session.flash("msg", "hello")
        self.assertTrue(session.dirty)

    def testFlashSameValueIsNoOp(self) -> None:
        """
        Skip dirty-marking when the flash value is unchanged.

        Validates that writing the identical flash value a second time
        does not re-mark the session dirty.
        """
        session = Session()
        session.flash("msg", "hello")
        session._markClean()
        session.flash("msg", "hello")
        self.assertFalse(session.dirty)

    def testGetFlashReturnsValueAfterAging(self) -> None:
        """
        Return a flash value written in the previous simulated request.

        Validates the complete lifecycle: flash() → _ageFlashData() →
        getFlash() to confirm the value travels from the new to the
        old flash bag.
        """
        session = Session()
        session.flash("notice", "saved")
        session._ageFlashData()
        self.assertEqual(session.getFlash("notice"), "saved")

    def testGetFlashReturnsDefaultWhenAbsent(self) -> None:
        """
        Return the default when no flash value exists for the key.

        Validates that getFlash() falls back to the supplied default
        instead of raising when the key is missing.
        """
        session = Session()
        result = session.getFlash("missing", "fallback")
        self.assertEqual(result, "fallback")

    def testGetFlashReturnsNoneByDefault(self) -> None:
        """
        Return None as the implicit default for absent flash keys.

        Validates that getFlash() returns None when no default is
        provided and the flash bag is empty.
        """
        session = Session()
        self.assertIsNone(session.getFlash("missing"))

    def testGetFlashPrefersCurrentRequestValue(self) -> None:
        """
        Prefer the value flashed during the current request.

        Validates that a key present in both bags resolves to the newest
        value, so a handler re-rendering its own view is not served the
        stale one.
        """
        session = Session()
        session.flash("msg", "old")
        session._ageFlashData()
        session.flash("msg", "new")
        self.assertEqual(session.getFlash("msg"), "new")

    def testGetFlashFallsBackToPreviousRequestValue(self) -> None:
        """
        Fall back to the previous bag for keys absent from the new one.

        Validates that flashing an unrelated key during this request
        does not hide values inherited from the previous request.
        """
        session = Session()
        session.flash("first", "a")
        session._ageFlashData()
        session.flash("second", "b")
        self.assertEqual(session.getFlash("first"), "a")

    def testFlashValueIsAccessibleBeforeAging(self) -> None:
        """
        Expose flash values written during the current request.

        Validates that a handler re-rendering its own view reads back
        what it just flashed, without having to redirect first.
        """
        session = Session()
        session.flash("msg", "pending")
        self.assertEqual(session.getFlash("msg"), "pending")

    # ── regenerate ───────────────────────────────────────────────────────────

    def testRegenerateSetsFlag(self) -> None:
        """
        Set the wantsRegenerate flag after calling regenerate().

        Validates that the session signals the manager to rotate the
        identifier before the next persistence operation.
        """
        session = Session()
        session.regenerate()
        self.assertTrue(session.wantsRegenerate)

    def testRegenerateActivatesSession(self) -> None:
        """
        Activate the session when regenerate() is called.

        Validates that ID rotation also activates the session so the
        manager will persist the new identifier.
        """
        session = Session()
        session.regenerate()
        self.assertTrue(session.started)
        self.assertIsNotNone(session.id)

    def testRegenerateMarksDirty(self) -> None:
        """
        Dirty the session after requesting regeneration.

        Validates that the session is scheduled for persistence after
        an ID rotation is requested.
        """
        session = Session()
        session.regenerate()
        self.assertTrue(session.dirty)

    # ── invalidate ───────────────────────────────────────────────────────────

    def testInvalidateClearsData(self) -> None:
        """
        Empty the session payload after invalidation.

        Validates that all keys stored in the session are removed when
        invalidate() is called.
        """
        session = Session(data={"a": 1, "b": 2})
        session.invalidate()
        self.assertEqual(session.all(), {})

    def testInvalidateSetsFlag(self) -> None:
        """
        Set the invalidated flag after calling invalidate().

        Validates that the session signals the manager to remove the
        backing-store record and clear the browser cookie.
        """
        session = Session()
        session.invalidate()
        self.assertTrue(session.invalidated)

    def testInvalidateMarksDirty(self) -> None:
        """
        Mark the session dirty after invalidation.

        Validates that the manager will write the deletion to the store
        even though the session is being destroyed.
        """
        session = Session()
        session.invalidate()
        self.assertTrue(session.dirty)

    def testInvalidateClearsRegenerateFlag(self) -> None:
        """
        Clear wantsRegenerate when the session is invalidated.

        Validates that a pending ID rotation is cancelled when the
        session is destroyed; the manager should not both rotate and
        delete the session.
        """
        session = Session()
        session.regenerate()
        session.invalidate()
        self.assertFalse(session.wantsRegenerate)

    # ── all ──────────────────────────────────────────────────────────────────

    def testAllReturnsShallowCopy(self) -> None:
        """
        Return a shallow copy of the session payload.

        Validates that mutating the returned dict does not affect the
        internal session state.
        """
        session = Session(data={"a": 1})
        copy = session.all()
        copy["a"] = 99
        self.assertEqual(session.get("a"), 1)

    def testAllIncludesAllKeys(self) -> None:
        """
        Include all stored key-value pairs in the returned dict.

        Validates that all() mirrors the complete internal _data
        mapping, including internal flash bags.
        """
        session = Session(data={"x": 10, "y": 20})
        result = session.all()
        self.assertEqual(result, {"x": 10, "y": 20})

    # ── _ageFlashData ────────────────────────────────────────────────────────

    def testAgeFlashDataMovesNewToOld(self) -> None:
        """
        Advance flash data from the new bag to the old bag.

        Validates that _ageFlashData() relocates the payload between the
        internal bags instead of duplicating it.
        """
        session = Session()
        session.flash("k", "v")
        session._ageFlashData()
        payload = session.all()
        self.assertEqual(payload["_flash_old"], {"k": "v"})
        self.assertNotIn("_flash_new", payload)

    def testAgeFlashDataDiscardsOldBag(self) -> None:
        """
        Discard the previous old flash bag during aging.

        Validates that values readable in the current request are
        removed when _ageFlashData() is called again.
        """
        session = Session()
        session.flash("k", "v")
        session._ageFlashData()
        session._ageFlashData()
        self.assertIsNone(session.getFlash("k"))

    def testAgeFlashDataMarksDirtyOnChange(self) -> None:
        """
        Dirty the session when the flash state changes during aging.

        Validates that any flash lifecycle transition (new → old) sets
        the dirty flag so the aged state is persisted.
        """
        session = Session()
        session.flash("k", "v")
        session._markClean()
        session._ageFlashData()
        self.assertTrue(session.dirty)

    def testAgeFlashDataMarksDirtyWhenDiscardingOldBag(self) -> None:
        """
        Dirty the session when only the previous bag is dropped.

        Validates that the removal of consumed flash values is persisted
        even though no new value was written.
        """
        session = Session()
        session.flash("k", "v")
        session._ageFlashData()
        session._markClean()
        session._ageFlashData()
        self.assertTrue(session.dirty)

    def testAgeFlashDataNoOpOnEmptySession(self) -> None:
        """
        Skip dirty-marking when no flash data exists.

        Validates that _ageFlashData() on a session without any flash
        data does not set the dirty flag unnecessarily.
        """
        session = Session()
        session._ageFlashData()
        self.assertFalse(session.dirty)

    # ── _rotateId ────────────────────────────────────────────────────────────

    def testRotateIdReturnsOldIdentifier(self) -> None:
        """
        Return the identifier that was active before the rotation.

        Validates that the manager receives the old ID so it can delete
        the corresponding backing-store record.
        """
        session = Session(id="original")
        old_id = session._rotateId()
        self.assertEqual(old_id, "original")

    def testRotateIdAssignsNewIdentifier(self) -> None:
        """
        Assign a fresh identifier after rotating.

        Validates that _rotateId() generates and stores a new ID that
        differs from the one that was returned as the old ID.
        """
        session = Session(id="original")
        old_id = session._rotateId()
        self.assertIsNotNone(session.id)
        self.assertNotEqual(session.id, old_id)

    def testRotateIdClearsRegenerateFlag(self) -> None:
        """
        Clear the wantsRegenerate flag after rotation.

        Validates that the session no longer requests rotation once
        _rotateId() has been executed by the manager.
        """
        session = Session()
        session.regenerate()
        session._rotateId()
        self.assertFalse(session.wantsRegenerate)

    def testRotateIdReturnsNoneWhenNoId(self) -> None:
        """
        Return None as the old ID for a session that had none.

        Validates that rotating a lazily-activated session that never
        had an explicit ID does not raise and returns None.
        """
        session = Session()
        old_id = session._rotateId()
        self.assertIsNone(old_id)

    # ── _markClean ───────────────────────────────────────────────────────────

    def testMarkCleanClearsDirtyFlag(self) -> None:
        """
        Clear the dirty flag after a successful persistence operation.

        Validates that _markClean() resets the dirty state so the
        manager does not schedule a redundant store write.
        """
        session = Session()
        session.put("x", 1)
        self.assertTrue(session.dirty)
        session._markClean()
        self.assertFalse(session.dirty)

    # ── previous URL ─────────────────────────────────────────────────────────

    def testGetPreviousUrlDefaultsToNone(self) -> None:
        """
        Return None when no page has been recorded yet.

        Validates the initial state of a brand-new session.
        """
        self.assertIsNone(Session().getPreviousUrl())

    def testSetPreviousUrlIsReadBack(self) -> None:
        """
        Store and read back the last visited page.

        Validates the round trip used to redirect back after a failed
        form submission.
        """
        session = Session()
        session.setPreviousUrl("http://orionis.test/users/create")
        self.assertEqual(
            session.getPreviousUrl(),
            "http://orionis.test/users/create",
        )

    def testSetPreviousUrlActivatesSession(self) -> None:
        """
        Activate the session when the previous page is recorded.

        Validates that the value is persisted like any other session
        entry.
        """
        session = Session()
        session.setPreviousUrl("http://orionis.test/login")
        self.assertTrue(session.started)
        self.assertTrue(session.dirty)

    def testSetPreviousUrlTwiceWithSameValueKeepsSessionClean(self) -> None:
        """
        Skip a redundant write when revisiting the same page.

        Validates that browsing the same URL again does not schedule an
        extra store write.
        """
        session = Session()
        session.setPreviousUrl("http://orionis.test/login")
        session._markClean()
        session.setPreviousUrl("http://orionis.test/login")
        self.assertFalse(session.dirty)

class TestSessionActivation(TestCase):
    """Unit tests for the lazy-activation rules of a session."""

    def testPutKeepsIdentifierOfRestoredSession(self) -> None:
        """
        Reuse the identifier of a session restored from a store.

        Validates that writing to an already-started session never
        rotates its identifier.
        """
        session = Session(id="restored", started=True, is_new=False)
        session.put("a", 1)
        self.assertEqual(session.id, "restored")

    def testFlashKeepsIdentifierOfRestoredSession(self) -> None:
        """
        Reuse the identifier when flashing on a restored session.

        Validates that the flash path shares the activation guard used
        by put().
        """
        session = Session(id="restored", started=True, is_new=False)
        session.flash("msg", "hi")
        self.assertEqual(session.id, "restored")

    def testFlashOnExistingBagKeepsIdentifier(self) -> None:
        """
        Reuse the identifier when appending to an existing flash bag.

        Validates that the second flash of a request takes the merge
        branch without re-activating the session.
        """
        session = Session()
        session.flash("first", 1)
        first_id = session.id
        session.flash("second", 2)
        self.assertEqual(session.id, first_id)
        self.assertEqual(session.getFlash("second"), 2)

    def testFlashOnNeverStartedSessionWithExistingBagActivates(self) -> None:
        """
        Activate a preloaded session on its first flash write.

        Validates that a session built with a flash bag but never
        started still receives an identifier when written to.
        """
        session = Session(data={"_flash_new": {"a": 1}})
        session.flash("b", 2)
        self.assertTrue(session.started)
        self.assertIsNotNone(session.id)

    def testClearOnNeverStartedSessionDoesNotDirty(self) -> None:
        """
        Skip dirty-marking when clearing a session that never started.

        Validates that discarding preloaded data does not schedule a
        store write for an inactive session.
        """
        session = Session(data={"a": 1})
        session.clear()
        self.assertEqual(session.all(), {})
        self.assertFalse(session.dirty)

    def testRegenerateOnStartedSessionKeepsIdentifier(self) -> None:
        """
        Defer the identifier swap on an already-started session.

        Validates that regenerate() only raises the flag; the manager
        performs the actual rotation.
        """
        session = Session(id="abc", started=True, is_new=False)
        session.regenerate()
        self.assertEqual(session.id, "abc")
        self.assertTrue(session.wantsRegenerate)

class TestSessionOldInput(TestCase):
    """Unit tests for the reserved old-input flash bag."""

    def testFlashInputStripsSensitiveFields(self) -> None:
        """
        Never repopulate credential-like fields.

        Validates that a submitted password is dropped before reaching
        the flash bag.
        """
        session = Session()
        session.flashInput({"email": "a@b.c", "password": "secret"})
        self.assertEqual(session.getOldInput("email"), "a@b.c")
        self.assertIsNone(session.getOldInput("password"))

    def testFlashInputActivatesSession(self) -> None:
        """
        Activate the session when a payload is remembered.

        Validates that the reserved bag follows the regular flash
        lifecycle.
        """
        session = Session()
        session.flashInput({"email": "a@b.c"})
        self.assertTrue(session.started)
        self.assertTrue(session.dirty)

    def testFlashInputMergesRepeatedCalls(self) -> None:
        """
        Accumulate fields across successive calls in one request.

        Validates that a second call does not replace the bag written
        by the first one.
        """
        session = Session()
        session.flashInput({"email": "a@b.c"})
        session.flashInput({"name": "Ada"})
        self.assertEqual(session.getOldInput("email"), "a@b.c")
        self.assertEqual(session.getOldInput("name"), "Ada")

    def testFlashInputDoesNotMergeWithPreviousRequest(self) -> None:
        """
        Keep values of the previous request out of the new bag.

        Validates that only the bag written during this request is
        merged, so stale fields never leak forward.
        """
        session = Session()
        session.flashInput({"email": "a@b.c"})
        session._ageFlashData()
        session.flashInput({"name": "Ada"})
        session._ageFlashData()
        self.assertIsNone(session.getOldInput("email"))
        self.assertEqual(session.getOldInput("name"), "Ada")

    def testFlashInputReplacesNonMappingBag(self) -> None:
        """
        Rebuild the reserved bag when it holds a corrupted value.

        Validates that a non-mapping value stored under the reserved key
        is replaced instead of crashing the merge.
        """
        session = Session()
        session.flash(OLD_INPUT_KEY, "corrupted")
        session.flashInput({"email": "a@b.c"})
        self.assertEqual(session.getOldInput("email"), "a@b.c")

    def testFlashInputSurvivesOneRequestCycle(self) -> None:
        """
        Expose the payload during exactly one further request.

        Validates that the bag is discarded after the second aging pass.
        """
        session = Session()
        session.flashInput({"email": "a@b.c"})
        session._ageFlashData()
        self.assertEqual(session.getOldInput("email"), "a@b.c")
        session._ageFlashData()
        self.assertIsNone(session.getOldInput("email"))

    def testGetOldInputReturnsDefaultWhenBagIsMissing(self) -> None:
        """
        Return the default when nothing was ever submitted.

        Validates that reading old input on a blank session is safe.
        """
        self.assertEqual(Session().getOldInput("email", "fallback"), "fallback")

    def testGetOldInputReturnsDefaultForCorruptedBag(self) -> None:
        """
        Return the default when the reserved bag is not a mapping.

        Validates the defensive type check protecting the read path.
        """
        session = Session()
        session.flash(OLD_INPUT_KEY, "corrupted")
        self.assertEqual(session.getOldInput("email", "fallback"), "fallback")

    def testGetOldInputReturnsDefaultForUnknownField(self) -> None:
        """
        Return the default for a field absent from the bag.

        Validates that unrelated fields do not resolve to another
        field's value.
        """
        session = Session()
        session.flashInput({"email": "a@b.c"})
        self.assertIsNone(session.getOldInput("name"))

class TestSessionErrors(TestCase):
    """Unit tests for the reserved validation-errors flash bag."""

    def testFlashErrorsNormalisesMessages(self) -> None:
        """
        Store every message as a list of strings.

        Validates that a single message is wrapped so views can always
        iterate the bag.
        """
        session = Session()
        session.flashErrors({"email": "required"})
        self.assertEqual(session.getErrors(), {"email": ["required"]})

    def testFlashErrorsAcceptsAnException(self) -> None:
        """
        Accept a duck-typed validation exception.

        Validates that controllers can hand the raised exception over
        without unpacking it first.
        """
        session = Session()
        session.flashErrors(_FakeValidationException({"email": ["invalid"]}))
        self.assertEqual(session.getErrors(), {"email": ["invalid"]})

    def testFlashErrorsMergesRepeatedCalls(self) -> None:
        """
        Accumulate fields across successive calls in one request.

        Validates that reporting a second field does not discard the
        first one.
        """
        session = Session()
        session.flashErrors({"email": "required"})
        session.flashErrors({"name": "required"})
        self.assertEqual(
            session.getErrors(),
            {"email": ["required"], "name": ["required"]},
        )

    def testFlashErrorsReplacesNonMappingBag(self) -> None:
        """
        Rebuild the reserved bag when it holds a corrupted value.

        Validates that a non-mapping value stored under the reserved key
        is replaced instead of crashing the merge.
        """
        session = Session()
        session.flash(ERRORS_KEY, "corrupted")
        session.flashErrors({"email": "required"})
        self.assertEqual(session.getErrors(), {"email": ["required"]})

    def testGetErrorsReturnsEmptyBagByDefault(self) -> None:
        """
        Return an empty mapping when nothing failed.

        Validates that views can call the accessor unconditionally.
        """
        self.assertEqual(Session().getErrors(), {})

    def testGetErrorsReturnsEmptyBagForCorruptedValue(self) -> None:
        """
        Return an empty mapping when the reserved bag is not a mapping.

        Validates the defensive type check protecting the read path.
        """
        session = Session()
        session.flash(ERRORS_KEY, "corrupted")
        self.assertEqual(session.getErrors(), {})

    def testFlashErrorsSurvivesOneRequestCycle(self) -> None:
        """
        Expose the errors during exactly one further request.

        Validates that the bag is discarded after the second aging pass.
        """
        session = Session()
        session.flashErrors({"email": "required"})
        session._ageFlashData()
        self.assertEqual(session.getErrors(), {"email": ["required"]})
        session._ageFlashData()
        self.assertEqual(session.getErrors(), {})
