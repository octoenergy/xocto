from typing import Generic, Tuple, TypeVar, Union

from django.contrib.auth import models as auth_models
from django.db import models
from django.db.models.expressions import Combinable
from django.http import HttpRequest


# A type variable which can be used in generic types, and represents a Django model of some
# description
Model = TypeVar("Model", bound=models.Model)


# A type variable for representing arbitrary user models
User = TypeVar("User", bound=auth_models.AbstractBaseUser)


# Helpers for declaring django relations on classes
# These are one-item Unions so that mypy knows they are type aliases and not strings
ForeignKey = Union["models.ForeignKey[Union[Model, Combinable], Model]"]
OptionalForeignKey = Union[
    "models.ForeignKey[Union[Model, Combinable, None], Union[Model, None]]"
]

OneToOneField = Union["models.OneToOneField[Union[Model, Combinable], Model]"]
OptionalOneToOneField = Union[
    "models.OneToOneField[Union[Model, Combinable, None], Union[Model, None]]"
]

# A type variable to describe the Django model choices kwarg
Choices = Tuple[Tuple[str, str], ...]


class AuthenticatedRequest(HttpRequest, Generic[User]):
    """
    This class represents HttpRequests that are guaranteed to have an auth user associated
    with them, for use when hinting requests that are known to be authenticated.
    """

    user: User
