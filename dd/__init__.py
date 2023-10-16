"""Package of algorithms based on decision diagrams."""
from enum import IntFlag,auto

class Cudd_ReorderingType(IntFlag):
    CUDD_REORDER_SAME = 0
    CUDD_REORDER_NONE = auto()
    CUDD_REORDER_RANDOM = auto()
    CUDD_REORDER_RANDOM_PIVOT = auto()
    CUDD_REORDER_SIFT = auto()
    CUDD_REORDER_SIFT_CONVERGE = auto()
    CUDD_REORDER_SYMM_SIFT = auto()
    CUDD_REORDER_SYMM_SIFT_CONV = auto()
    CUDD_REORDER_WINDOW2 = auto()
    CUDD_REORDER_WINDOW3 = auto()
    CUDD_REORDER_WINDOW4 = auto()
    CUDD_REORDER_WINDOW2_CONV = auto()
    CUDD_REORDER_WINDOW3_CONV = auto()
    CUDD_REORDER_WINDOW4_CONV = auto()
    CUDD_REORDER_GROUP_SIFT = auto()
    CUDD_REORDER_GROUP_SIFT_CONV = auto()
    CUDD_REORDER_ANNEALING = auto()
    CUDD_REORDER_GENETIC = auto()
    CUDD_REORDER_LINEAR = auto()
    CUDD_REORDER_LINEAR_CONVERGE = auto()
    CUDD_REORDER_LAZY_SIFT = auto()
    CUDD_REORDER_EXACT = auto()

try:
    from ._version import version as __version__
except ImportError:
    __version__ = None
try:
    from dd import cudd as _bdd
except ImportError:
    from dd import autoref as _bdd
BDD = _bdd.BDD
