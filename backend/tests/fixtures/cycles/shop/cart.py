"""Half of cycle 2, via a relative import."""
from . import tax


def cart_total(prices):
    return tax.with_tax(sum(prices))
