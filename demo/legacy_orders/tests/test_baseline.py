# Existing test suite that shipped with the order service.
#
# Public behaviour only - these are the tests a migration must keep passing.
# They deliberately do NOT pin the internal rounding stages; that convention is
# only observable through the totals below.

from decimal import Decimal

import customers
import orders
import pricing
import refunds
import storage


def setup_function(function):
    storage.reset()


def test_standard_customer_pays_list_price_plus_vat():
    result = pricing.finalise_amount(
        [{"sku": "SKU-A", "unit_price": "1.25", "quantity": 1}], "standard"
    )
    assert result["subtotal"] == Decimal("1.25")
    assert result["total"] == Decimal("1.50")


def test_member_discount_is_taken_off_before_tax():
    result = pricing.finalise_amount(
        [{"sku": "SKU-A", "unit_price": "10.00", "quantity": 2}], "member"
    )
    assert result["subtotal"] == Decimal("18.00")
    assert result["total"] == Decimal("21.60")


def test_unknown_category_prices_as_standard():
    assert pricing.discount_rate("not-a-category") == Decimal("0.00")
    assert pricing.discount_rate(None) == Decimal("0.00")


def test_negative_quantity_is_rejected():
    try:
        pricing.line_gross("2.45", -1)
    except ValueError:
        return
    raise AssertionError("expected ValueError for a negative quantity")


def test_closed_account_prices_as_standard_but_cannot_order():
    assert customers.category_for("C-1005") == "standard"
    assert customers.is_eligible("C-1005") is False


def test_place_order_returns_a_saved_order():
    order = orders.place_order("C-1002", [{"sku": "SKU-A", "unit_price": "10.00", "quantity": 2}])
    assert order["status"] == "placed"
    assert order["order_id"] == "ORD-0001"
    assert order["total"] == Decimal("24.00")
    assert storage.get_order("ORD-0001") == order


def test_place_order_rejects_empty_basket():
    order = orders.place_order("C-1001", [])
    assert order["status"] == "rejected"
    assert order["reason"] == "no_lines"


def test_place_order_rejects_closed_account():
    order = orders.place_order("C-1005", [{"sku": "SKU-A", "unit_price": "5.00", "quantity": 1}])
    assert order["status"] == "rejected"
    assert order["reason"] == "customer_not_eligible"


def test_partial_refund_reprices_through_pricing():
    orders.place_order(
        "C-1002",
        [
            {"sku": "SKU-A", "unit_price": "10.00", "quantity": 2},
            {"sku": "SKU-B", "unit_price": "5.00", "quantity": 1},
        ],
    )
    refund = refunds.partial_refund("ORD-0001", [{"sku": "SKU-A", "quantity": 1}])
    assert refund["status"] == "refunded"
    assert refund["refund_id"] == "REF-0001"
    assert refund["total"] == Decimal("12.00")
    assert storage.get_order("ORD-0001")["refunded_total"] == Decimal("12.00")


def test_refund_rejects_unknown_order():
    refund = refunds.partial_refund("ORD-9999", [{"sku": "SKU-A", "quantity": 1}])
    assert refund["status"] == "rejected"
    assert refund["reason"] == "order_not_found"


def test_refund_rejects_more_than_was_ordered():
    orders.place_order("C-1002", [{"sku": "SKU-A", "unit_price": "5.00", "quantity": 1}])
    refund = refunds.partial_refund("ORD-0001", [{"sku": "SKU-A", "quantity": 4}])
    assert refund["status"] == "rejected"
    assert refund["reason"] == "quantity_exceeds_order"


def test_order_ids_are_deterministic_after_reset():
    first = orders.place_order("C-1002", [{"sku": "SKU-A", "unit_price": "5.00", "quantity": 1}])
    storage.reset()
    second = orders.place_order("C-1002", [{"sku": "SKU-A", "unit_price": "5.00", "quantity": 1}])
    assert first["order_id"] == second["order_id"] == "ORD-0001"
