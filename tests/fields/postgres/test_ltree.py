import pytest

from tests.models import models


pytestmark = pytest.mark.django_db


class TestLtreeField:
    def test_get_descendants_no_children(self):
        root = models.TreeModel.objects.create(parent=None, path="root")

        results = models.TreeModel.objects.filter(path__ancestor=root.path)

        # The root node is considered to be a descendant of itself
        assert set(results) == {root}

    def test_get_descendants(self):
        root = models.TreeModel.objects.create(parent=None, path="root")
        child = models.TreeModel.objects.create(parent=root, path="root.child")
        grandchild = models.TreeModel.objects.create(
            parent=root, path="root.child.grandchild"
        )

        results = models.TreeModel.objects.filter(path__ancestor=root.path)

        # The root node is considered to be a descendant of itself
        assert set(results) == {root, child, grandchild}

        results = models.TreeModel.objects.filter(path__ancestor=child.path)

        # The root node should not appear as a descendant of the child
        assert set(results) == {child, grandchild}

    def test_get_descendants_with_siblings(self):
        root = models.TreeModel.objects.create(parent=None, path="root")
        child1 = models.TreeModel.objects.create(parent=root, path="root.child1")
        child2 = models.TreeModel.objects.create(parent=root, path="root.child2")

        results = models.TreeModel.objects.filter(path__ancestor=root.path)

        assert set(results) == {root, child1, child2}

    def test_get_ancestors_none(self):
        root = models.TreeModel.objects.create(parent=None, path="root")

        results = models.TreeModel.objects.filter(path__descendant=root.path)

        # The grandchild node is considered to be an ancestor of itself
        assert set(results) == {root}

    def test_get_ancestors(self):
        root = models.TreeModel.objects.create(parent=None, path="root")
        child = models.TreeModel.objects.create(parent=root, path="root.child")
        grandchild = models.TreeModel.objects.create(
            parent=root, path="root.child.grandchild"
        )

        results = models.TreeModel.objects.filter(path__descendant=grandchild.path)

        # The grandchild node is considered to be an ancestor of itself
        assert set(results) == {root, child, grandchild}

        results = models.TreeModel.objects.filter(path__descendant=child.path)

        # The grandchild should not appear as an ancestor of the child
        assert set(results) == {root, child}
