import enum
from typing import Dict, List

from django.db import models


class _ChoicesMeta(enum.EnumMeta):
    def __new__(metacls, classname, bases, classdict):
        cls = super().__new__(metacls, classname, bases, classdict)
        return enum.unique(cls)


class Choices(enum.Enum, metaclass=_ChoicesMeta):
    """
    Group and format django choices.

    This class provides a wrapper around the Enum class to provide some methods for formatting
    django choices.
    Remember to allow all choices for database fields but restrict forms to available choices to
    restrict users putting in deprecated choices.

    Properties:
        __labels__ - provide a mapping of 'member: label' pairs.
        __deprecated__ - provide a list of deprecated members

    Methods:
        names - iterate through the member variable names
        values - iterate through the member variable values
        choices - return a formatted tuple of tuples suitable for django model choices
        available_choices - return the above, excluding deprecated choices

    Usage:

        class DjangoChoice(Choices):
            CHOICE_1 = "1"
            CHOICE_2 = "2"
            CHOICE_3 = "3"
            CHOICE_4 = "4"

            __labels__ = {"CHOICE_1": "One"}
            __deprecated__ = ["CHOICE_3"]

        models.py
        =========

        django_field = models.CharField(max_length=20, choices=DjangoChoice.choices())


        module.py
        =========

        DjangoChoice.CHOICE_1.label  // One
        DjangoChoice.CHOICE_2.label  // Choice Two

    """

    __labels__: Dict[str, str] = {}
    __deprecated__: List[str] = []

    @classmethod
    def names(cls):
        return (member.name for member in cls)

    @classmethod
    def values(cls):
        return (member.value for member in cls)

    @classmethod
    def choices(cls):
        # All choices include deprecated ones
        return ((member.value, member.label) for name, member in cls.__members__.items())

    @classmethod
    def available_choices(cls):
        # All currently available choices excluding deprecated ones
        return (
            (member.value, member.label)
            for name, member in cls.__members__.items()
            if member.name not in cls.__deprecated__
        )

    @property
    def label(self):
        """
        Get a human readable name for a member.

        This works because when you do Enum.CHOICE you get an instance of this class. Any methods
        which aren't classmethod decorated will apply to the individual member.
        """

        if self.name in self.__labels__:
            return self.__labels__[self.name]
        # Default to title-case version of member name. Replace underscores with spaces
        return self.name.title().replace("_", " ")

    @property
    def description(self):
        """
        Get documentation for a member. Used to generate labels for options in GraphiQL.
        """
        return self.label


class TextChoices(models.TextChoices):
    """
    TextChoices class which can facilitate descriptions for GraphiQL.

    It does exactly the same as the inbuilt django TextChoices, just has an additional property
    which means labels can automatically be rendered in GraphiQL documentation.
    """

    @property
    def description(self):
        """
        Get documentation for a member. Used to generate labels for options in GraphiQL.

        We're adding a full stop as the descriptions for the graphQL API are meant to have full
        stops at the end.
        """
        if self.label.endswith("."):
            return self.label
        return self.label + "."
