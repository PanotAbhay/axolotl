# orders.py
#
# Order placement.

import customers
import pricing
import storage

STATUS_PLACED = "placed"
STATUS_REJECTED = "rejected"

REJECT_INELIGIBLE = "customer_not_eligible"
REJECT_EMPTY = "no_lines"


def place_order(customer_id, items):
    """Place an order and return it as a dict.

    items is a list of dicts: {"sku": ..., "unit_price": "2.45", "quantity": 1}

    Rejections come back as a dict with status 'rejected' rather than an
    exception - the till used to swallow exceptions and we lost orders.
    """
    if items is None or len(items) == 0:
        return {
            "order_id": None,
            "customer_id": customer_id,
            "status": STATUS_REJECTED,
            "reason": REJECT_EMPTY,
        }

    if not customers.is_eligible(customer_id):
        return {
            "order_id": None,
            "customer_id": customer_id,
            "status": STATUS_REJECTED,
            "reason": REJECT_INELIGIBLE,
        }

    category = customers.category_for(customer_id)
    priced = pricing.finalise_amount(items, category)

    order_id = storage.next_order_id()

    order = {
        "order_id": order_id,
        "customer_id": customer_id,
        "category": category,
        "status": STATUS_PLACED,
        "lines": priced["lines"],
        "subtotal": priced["subtotal"],
        "tax": priced["tax"],
        "total": priced["total"],
        "refunded_total": None,
    }

    storage.save_order(order)
    return order


def order_summary(order_id):
    """Human-readable one-liner. Used by the support tool."""
    order = storage.get_order(order_id)
    if order is None:
        return "no such order %s" % order_id
    return "%s for %s: %s line(s), total %s" % (
        order["order_id"],
        customers.describe(order["customer_id"]),
        len(order["lines"]),
        order["total"],
    )
