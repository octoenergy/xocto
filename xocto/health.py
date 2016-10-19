from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.loader import MigrationLoader


def check_migrations():
    """
    Check if there are any migrations that haven't been applied yet
    """
    return _num_unapplied_migrations() == 0


def _num_unapplied_migrations():
    """
    Return the number of unapplied migrations
    """
    connection = connections[DEFAULT_DB_ALIAS]
    loader = MigrationLoader(connection)
    graph = loader.graph

    # Count unapplied migrations
    num_unapplied_migrations = 0
    for app_name in loader.migrated_apps:
        for node in graph.leaf_nodes(app_name):
            for plan_node in graph.forwards_plan(node):
                if plan_node not in loader.applied_migrations:
                    num_unapplied_migrations += 1

    return num_unapplied_migrations
