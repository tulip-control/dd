"""Python 2 to 3 version compatibility."""


def items(d):
    """Try to return `dict.iteritems()`, else `dict.items()`.

    Compatibility between Python v2 and v3.
    Preserves readability, w/o damaging performance.
    """
    try:
        return d.iteritems()
    except AttributeError:
        return d.items()


def values(d):
    """Try to return `dict.itervalues()`, else `dict.values()`."""
    try:
        return d.itervalues()
    except AttributeError:
        return d.values()
