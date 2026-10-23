"""Other half of cycle 2, via a relative import back."""
from .cart import cart_total


def with_tax(amount):
    return amount * 1.2


def taxed_basket(prices):
    return cart_total(prices)
