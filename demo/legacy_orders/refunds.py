# refunds.py
#
# Partial refunds. Reuses the pricing rules on purpose: a refund has to come
# back through exactly the same discount-then-round-then-tax path the original
# order went through, or the customer gets a penny more or less than they paid.

import pricing
import storage

STATUS_REFUNDED = "refunded"
STATUS_REJECTED = "rejected"

REJECT_NO_ORDER = "order_not_found"
REJECT_NOTHING = "no_lines"
REJECT_TOO_MANY = "quantity_exceeds_order"


def partial_refund(order_id, lines):
    """Refund some lines of an existing order.

    lines is a list of dicts: {"sku": ..., "quantity": 1}

    The refunded amount is recomputed from the original unit prices and the
    original customer category, through pricing.finalise_amount, for just the
    quantities being sent back.
    """
    order = storage.get_order(order_id)
    if order is None:
        return {
            "refund_id": None,
            "order_id": order_id,
            "status": STATUS_REJECTED,
            "reason": REJECT_NO_ORDER,
        }

    if lines is None or len(lines) == 0:
        return {
            "refund_id": None,
            "order_id": order_id,
            "status": STATUS_REJECTED,
            "reason": REJECT_NOTHING,
        }

    original_by_sku = {}
    for line in order["lines"]:
        original_by_sku[line["sku"]] = line

    to_price = []
    for line in lines:
        sku = line["sku"]
        if sku not in original_by_sku:
            return {
                "refund_id": None,
                "order_id": order_id,
                "status": STATUS_REJECTED,
                "reason": REJECT_NO_ORDER,
                "sku": sku,
            }

        original = original_by_sku[sku]
        wanted = int(line["quantity"])
        if wanted > original["quantity"]:
            return {
                "refund_id": None,
                "order_id": order_id,
                "status": STATUS_REJECTED,
                "reason": REJECT_TOO_MANY,
                "sku": sku,
            }

        to_price.append(
            {
                "sku": sku,
                "unit_price": original["unit_price"],
                "quantity": wanted,
            }
        )

    priced = pricing.finalise_amount(to_price, order["category"])

    refund_id = storage.next_refund_id()
    refund = {
        "refund_id": refund_id,
        "order_id": order_id,
        "status": STATUS_REFUNDED,
        "category": order["category"],
        "lines": priced["lines"],
        "subtotal": priced["subtotal"],
        "tax": priced["tax"],
        "total": priced["total"],
    }

    storage.save_refund(refund)

    order["refunded_total"] = priced["total"]
    storage.save_order(order)

    return refund
