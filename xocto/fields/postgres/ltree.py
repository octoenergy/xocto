"""
This module's approach is inspired by

https://github.com/peopledoc/django-ltree-demo

One difference is that the <@ and @> operators are reversed compared to the
demo, since this makes for more natural querying e.g.

    filter(path__ancestor=my_path)

returns the *descendants* of my_path (the demo uses path_descendant for this).
"""

from django.db import models


class LtreeField(models.TextField):
    """
    LtreeField provides a django model field representation of the ltree type.

    The ltree extension must be installed in the database for this field to work e.g.

        CREATE EXTENSION IF NOT EXISTS ltree

    It is recommended to create a GiST index over the ltree field in order to
    optimize the ancestor/descendant look ups.

    More information can be found in the PostgreSQL documentation:

    https://www.postgresql.org/docs/current/ltree.html
    """

    description = "ltree"

    def db_type(self, connection):
        return "ltree"


class Ancestor(models.Lookup):
    """
    Ancestor provides a lookup for querying by an ltree path's ancestor.

    For example, if the model is defined as

        class Foo(models.Model):
            path = LtreeField

    and

        bar = Foo(path="my_path")

    then we can query as

        Foo.objects.filter(path__ancestor=bar.path)

    to obtain all of the instances of Foo that have bar as their ancestor i.e.
    bar's descendants.

    The relationship is reflexive i.e. bar is its own descendant.
    """

    lookup_name = "ancestor"

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return "%s <@ %s" % (lhs, rhs), params


class Descendant(models.Lookup):
    """
    Descendant provides a lookup for querying by an ltree path's descendant.

    For example, if the model is defined as

        class Foo(models.Model):
            path = LtreeField

    and

        bar = Foo(path="my_path")

    then we can query as

        Foo.objects.filter(path__descendant=bar.path)

    to obtain all of the instances of Foo that have bar as a descendant i.e.
    bar's ancestors.

    The relationship is reflexive i.e. bar is its own ancestor.
    """

    lookup_name = "descendant"

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return "%s @> %s" % (lhs, rhs), params


LtreeField.register_lookup(Ancestor)
LtreeField.register_lookup(Descendant)
