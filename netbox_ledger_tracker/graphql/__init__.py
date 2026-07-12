from .schema import LedgerTrackerQuery

# NetBox discovers the plugin schema as the ``schema`` attribute of the
# ``graphql`` package (resource path ``graphql.schema``) and ``extend()``s it
# onto the global registry, so this must be an iterable of query classes.
schema = [LedgerTrackerQuery]

__all__ = ['schema']
