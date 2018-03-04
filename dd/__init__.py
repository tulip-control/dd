"""Package of algorithms based on decision diagrams."""
try:
    from ._version import version as __version__
except ImportError:
    __version__ = None
try:
    from dd import cudd as _bdd
except ImportError:
    from dd import autoref as _bdd
BDD = _bdd.BDD
