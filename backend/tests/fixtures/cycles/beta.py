"""Other half of cycle 1, plus a plain dependency on leaf."""
import leaf
from alpha import alpha_total


def beta_sum(values):
    return sum(leaf.clean(v) for v in values)


def beta_again(values):
    return alpha_total(values)
