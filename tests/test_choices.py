import pytest

from xocto.choices import Choices, TextChoices


class TestChoices:
    def test_names(self):
        class ChoiceTester(Choices):
            CHOICE_ONE = 1
            CHOICE_TWO = 2
            CHOICE_THREE = 3

            __labels__ = {"CHOICE_ONE": "One", "CHOICE_TWO": "Two"}
            __deprecated__ = ["CHOICE_THREE"]

        expected = ["CHOICE_ONE", "CHOICE_TWO", "CHOICE_THREE"]
        assert list(ChoiceTester.names()) == expected

    def test_values(self):
        class ChoiceTester(Choices):
            CHOICE_ONE = 1
            CHOICE_TWO = 2
            CHOICE_THREE = 3

            __labels__ = {"CHOICE_ONE": "One", "CHOICE_TWO": "Two"}
            __deprecated__ = ["CHOICE_THREE"]

        expected = [1, 2, 3]
        assert list(ChoiceTester.values()) == expected

    def test_labels(self):
        class ChoiceTester(Choices):
            CHOICE_ONE = 1
            CHOICE_TWO = 2
            CHOICE_THREE = 3

            __labels__ = {"CHOICE_ONE": "One", "CHOICE_TWO": "Two"}
            __deprecated__ = ["CHOICE_THREE"]

        assert ChoiceTester.CHOICE_ONE.label == "One"
        assert ChoiceTester.CHOICE_TWO.label == "Two"
        # No label returns the title case of the enum member
        assert ChoiceTester.CHOICE_THREE.label == "Choice Three"

    def test_labels_none_defined(self):
        class ChoiceTester(Choices):
            CHOICE_ONE = 1
            CHOICE_TWO = 2
            CHOICE_THREE = 3

        assert ChoiceTester.CHOICE_ONE.label == "Choice One"
        assert ChoiceTester.CHOICE_TWO.label == "Choice Two"
        assert ChoiceTester.CHOICE_THREE.label == "Choice Three"

    def test_choices(self):
        class ChoiceTester(Choices):
            CHOICE_ONE = 1
            CHOICE_TWO = 2
            CHOICE_THREE = 3

            __labels__ = {"CHOICE_ONE": "One", "CHOICE_TWO": "Two"}
            __deprecated__ = ["CHOICE_THREE"]

        expected = [(1, "One"), (2, "Two"), (3, "Choice Three")]
        assert list(ChoiceTester.choices()) == expected

    def test_available_choices(self):
        class ChoiceTester(Choices):
            CHOICE_ONE = 1
            CHOICE_TWO = 2
            CHOICE_THREE = 3

            __labels__ = {"CHOICE_ONE": "One", "CHOICE_TWO": "Two"}
            __deprecated__ = ["CHOICE_THREE"]

        expected = [(1, "One"), (2, "Two")]
        assert list(ChoiceTester.available_choices()) == expected

    def test_available_choices_none_deprecated(self):
        class ChoiceTester(Choices):
            CHOICE_ONE = 1
            CHOICE_TWO = 2
            CHOICE_THREE = 3

        expected = [(1, "Choice One"), (2, "Choice Two"), (3, "Choice Three")]
        assert list(ChoiceTester.available_choices()) == expected

    def test_unique(self):
        with pytest.raises(ValueError, match=r"duplicate values"):

            class ChoiceTester(Choices):
                CHOICE_ONE = 1
                CHOICE_TWO = 2
                CHOICE_THREE = 2


class TestTextChoices:
    def test_labels(self):
        class ChoiceTester(TextChoices):
            CHOICE_ONE = 1, "One"
            CHOICE_TWO = 2, "Two"

        assert ChoiceTester.CHOICE_ONE.label == "One"
        assert ChoiceTester.CHOICE_TWO.label == "Two"

    def test_descriptions(self):
        class ChoiceTester(TextChoices):
            CHOICE_ONE = 1, "One."
            CHOICE_TWO = 2, "Two"

        assert ChoiceTester.CHOICE_ONE.description == "One."
        assert ChoiceTester.CHOICE_TWO.description == "Two."
