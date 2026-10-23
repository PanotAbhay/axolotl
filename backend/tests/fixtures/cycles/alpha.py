"""Half of cycle 1: alpha imports beta, beta imports alpha."""
import beta


def alpha_total(values):
    return beta.beta_sum(values) + 1
