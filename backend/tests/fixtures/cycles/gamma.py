"""Depends on cycle 1 from outside it, and imports beta dynamically."""
import importlib

import alpha


def gamma_report(values):
    helper = importlib.import_module("beta")
    return alpha.alpha_total(values), helper
