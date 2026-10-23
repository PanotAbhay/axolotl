# storage.py
#
# In-memory store. There was a SQLite adapter here once; it went away when the
# reporting job moved out. Kept the same function names so nothing had to change.

ORDERS = {}
REFUNDS = {}

_COUNTER = {"order": 0, "refund": 0}

ORDER_PREFIX = "ORD-"
REFUND_PREFIX = "REF-"


def reset():
    """Wipe everything. Tests call this before each case."""
    ORDERS.clear()
    REFUNDS.clear()
    _COUNTER["order"] = 0
    _COUNTER["refund"] = 0


def next_order_id():
    _COUNTER["order"] = _COUNTER["order"] + 1
    return "%s%04d" % (ORDER_PREFIX, _COUNTER["order"])


def next_refund_id():
    _COUNTER["refund"] = _COUNTER["refund"] + 1
    return "%s%04d" % (REFUND_PREFIX, _COUNTER["refund"])


def save_order(order):
    ORDERS[order["order_id"]] = order
    return order


def get_order(order_id):
    return ORDERS.get(order_id)


def save_refund(refund):
    REFUNDS[refund["refund_id"]] = refund
    return refund


def get_refund(refund_id):
    return REFUNDS.get(refund_id)


def all_orders():
    # sorted so callers get a stable order - dict order used to bite us
    return [ORDERS[k] for k in sorted(ORDERS.keys())]
