# main.py
#
# Thin CLI over the order service. Reads one JSON document from argv or stdin.
#
#   python main.py place '{"customer_id": "C-1001", "items": [...]}'
#   python main.py refund '{"order_id": "ORD-0001", "lines": [...]}'
#
# Not used by anything automated. The ops team run it by hand now and again.

import json
import sys

import orders
import refunds

USAGE = "usage: main.py [place|refund] '<json>'"


def _money(value):
    # Decimal is not JSON serialisable, and str() keeps the exact digits.
    return str(value)


def _plain(obj):
    if isinstance(obj, dict):
        out = {}
        for key in sorted(obj.keys()):
            out[key] = _plain(obj[key])
        return out
    if isinstance(obj, list):
        return [_plain(x) for x in obj]
    if obj.__class__.__name__ == "Decimal":
        return _money(obj)
    return obj


def run(argv):
    if len(argv) < 3:
        print(USAGE)
        return 2

    command = argv[1]
    try:
        payload = json.loads(argv[2])
    except ValueError as exc:
        print("bad json: %s" % exc)
        return 2

    if command == "place":
        result = orders.place_order(payload.get("customer_id"), payload.get("items"))
    elif command == "refund":
        result = refunds.partial_refund(payload.get("order_id"), payload.get("lines"))
    else:
        print(USAGE)
        return 2

    print(json.dumps(_plain(result), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv))
