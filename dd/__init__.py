"""Package of algorithms based on decision diagrams."""
from dd.bdd import BDD
try:
    from ._version import version as __version__
except ImportError:
    __version__ = None
