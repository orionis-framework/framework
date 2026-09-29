from __future__ import annotations
from enum import Enum
from orionis.console.enums.styles import ANSIColors
from orionis.test import TestCase

class TestANSIColors(TestCase):

    # ------------------------------------------------------------------ #
    #  Type & membership                                                 #
    # ------------------------------------------------------------------ #

    def testIsEnumSubclass(self) -> None:
        """Verify that ANSIColors is a subclass of Enum.

        Ensures the class participates in Python's standard enum
        machinery and supports membership, iteration, and value lookup.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(ANSIColors, Enum))

    def testAllMembersHaveStringValues(self) -> None:
        """Verify that every member value is a string.

        Ensures each escape code can be used directly in string
        formatting without type conversion.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for member in ANSIColors:
            self.assertIsInstance(member.value, str)

    def testAllValuesAreUnique(self) -> None:
        """Verify that no two members share the same ANSI escape code.

        Ensures each visual style maps to exactly one enum member so
        that reverse-lookup is unambiguous.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        values = [m.value for m in ANSIColors]
        self.assertEqual(len(values), len(set(values)))

    def testAllNamesAreUnique(self) -> None:
        """Verify that no two members share the same name.

        Ensures the enum definition is self-consistent and free of
        accidental aliasing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        names = [m.name for m in ANSIColors]
        self.assertEqual(len(names), len(set(names)))

    # ------------------------------------------------------------------ #
    #  Required members exist                                            #
    # ------------------------------------------------------------------ #

    def testDefaultMemberExists(self) -> None:
        """Verify that the DEFAULT reset code member is defined.

        Ensures there is always a way to reset terminal styling back
        to its default state.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("DEFAULT", ANSIColors.__members__)

    def testBackgroundColorMembersExist(self) -> None:
        """Verify that all background colour members are defined.

        Ensures BG_INFO, BG_ERROR, BG_FAIL, BG_WARNING, and BG_SUCCESS
        are all present so that styled console panels can be rendered.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in ("BG_INFO", "BG_ERROR", "BG_FAIL", "BG_WARNING", "BG_SUCCESS"):
            self.assertIn(name, ANSIColors.__members__, msg=f"Missing: {name}")

    def testForegroundColorMembersExist(self) -> None:
        """Verify that all foreground colour members are defined.

        Ensures TEXT_INFO, TEXT_ERROR, TEXT_WARNING, TEXT_SUCCESS,
        TEXT_WHITE, and TEXT_MUTED are all present.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in (
            "TEXT_INFO",
            "TEXT_ERROR",
            "TEXT_WARNING",
            "TEXT_SUCCESS",
            "TEXT_WHITE",
            "TEXT_MUTED",
        ):
            self.assertIn(name, ANSIColors.__members__, msg=f"Missing: {name}")

    def testBoldColorMembersExist(self) -> None:
        """Verify that all bold-variant colour members are defined.

        Ensures TEXT_BOLD_INFO, TEXT_BOLD_ERROR, TEXT_BOLD_WARNING,
        TEXT_BOLD_SUCCESS, TEXT_BOLD_WHITE, and TEXT_BOLD_MUTED are present.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in (
            "TEXT_BOLD_INFO",
            "TEXT_BOLD_ERROR",
            "TEXT_BOLD_WARNING",
            "TEXT_BOLD_SUCCESS",
            "TEXT_BOLD_WHITE",
            "TEXT_BOLD_MUTED",
        ):
            self.assertIn(name, ANSIColors.__members__, msg=f"Missing: {name}")

    def testStyleMembersExist(self) -> None:
        """Verify that all text-style members are defined.

        Ensures TEXT_BOLD, TEXT_STYLE_UNDERLINE, DIM, ITALIC, CYAN,
        and MAGENTA are all present.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in (
            "TEXT_BOLD",
            "TEXT_STYLE_UNDERLINE",
            "DIM",
            "ITALIC",
            "CYAN",
            "MAGENTA",
        ):
            self.assertIn(name, ANSIColors.__members__, msg=f"Missing: {name}")

    # ------------------------------------------------------------------ #
    #  Individual member values                                          #
    # ------------------------------------------------------------------ #

    def testDefaultValue(self) -> None:
        """Verify that DEFAULT holds the ANSI reset escape code.

        Ensures the reset sequence is ``ESC[0m`` so that all
        preceding styles are cleared.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ANSIColors.DEFAULT.value, "\033[0m")

    def testBgInfoValue(self) -> None:
        """Verify that BG_INFO holds the expected blue background escape code.

        Ensures the informational background uses the standard ANSI blue
        background sequence ``ESC[44m``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ANSIColors.BG_INFO.value, "\033[44m")

    def testBgErrorValue(self) -> None:
        """Verify that BG_ERROR holds the expected red background escape code.

        Ensures the error background uses ``ESC[41m``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ANSIColors.BG_ERROR.value, "\033[41m")

    def testBgSuccessValue(self) -> None:
        """Verify that BG_SUCCESS holds the expected green background escape code.

        Ensures the success background uses ``ESC[42m``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ANSIColors.BG_SUCCESS.value, "\033[42m")

    def testTextErrorValue(self) -> None:
        """Verify that TEXT_ERROR holds the expected bright-red escape code.

        Ensures error text is rendered in bright red using ``ESC[91m``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ANSIColors.TEXT_ERROR.value, "\033[91m")

    def testTextSuccessValue(self) -> None:
        """Verify that TEXT_SUCCESS holds the expected green escape code.

        Ensures success text is rendered in green using ``ESC[32m``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ANSIColors.TEXT_SUCCESS.value, "\033[32m")

    def testTextBoldValue(self) -> None:
        """Verify that TEXT_BOLD holds the bold escape code.

        Ensures text is emboldened with ``ESC[1m``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ANSIColors.TEXT_BOLD.value, "\033[1m")

    def testCyanValue(self) -> None:
        """Verify that CYAN holds the cyan foreground escape code.

        Ensures cyan-coloured text uses ``ESC[36m``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(ANSIColors.CYAN.value, "\033[36m")

    # ------------------------------------------------------------------ #
    #  Lookup                                                            #
    # ------------------------------------------------------------------ #

    def testLookupByValue(self) -> None:
        """Verify that members can be retrieved by their escape-code value.

        Ensures a reset escape-code value resolves to ANSIColors.DEFAULT,
        enabling type-safe reverse lookup.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIs(ANSIColors("\033[0m"), ANSIColors.DEFAULT)

    def testLookupInvalidValueRaisesValueError(self) -> None:
        """Verify that looking up an unknown escape code raises ValueError.

        Ensures the enum rejects any string not defined as a member
        value, preventing silent misconfigurations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            ANSIColors("not_an_ansi_code")

    # ------------------------------------------------------------------ #
    #  Value format smoke-test                                           #
    # ------------------------------------------------------------------ #

    def testAllValuesStartWithEscapeSequence(self) -> None:
        """Verify that all member values begin with the ESC character.

        Ensures every code is a proper ANSI escape sequence rather than
        a plain string or empty value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for member in ANSIColors:
            self.assertTrue(
                member.value.startswith("\033["),
                msg=f"{member.name} value does not start with ESC sequence",
            )
