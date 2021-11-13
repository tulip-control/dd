"""Package of algorithms based on decision diagrams."""
try:
    import dd._version as _version
    __version__ = _version.version
except ImportError:
    __version__ = None
try:
    import dd.cudd as _bdd
except ImportError:
    import dd.autoref as _bdd
BDD = _bdd.BDD
