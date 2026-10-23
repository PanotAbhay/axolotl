# pricing.py
#
# Order pricing: discounts, tax, rounding.
#
# NOTE (Mar 2019): updated for the new VAT handling. Do NOT reorder the stages
# below without talking to finance first. The per-line rounding is deliberate
# and month-end reconciliation depends on it.
#
# TODO: move the category table into the customers service once that lands. (2018)

from decimal import ROUND_HALF_UP, Decimal

TAX_RATE = Decimal("0.20")
PENNY = Decimal("0.01")

# Discount applied per line, before tax.
CATEGORY_DISCOUNTS = {
    "standard": Decimal("0.00"),
    "member": Decimal("0.10"),
    "partner": Decimal("0.15"),
    "staff": Decimal("0.25"),
}


def discount_rate(category):
    """Return the per-line discount rate for a customer category.

    Unknown categories get no discount. This is on purpose - finance would
    rather undercharge nobody than guess.
    """
    if category is None:
        return CATEGORY_DISCOUNTS["standard"]
    if category not in CATEGORY_DISCOUNTS:
        return CATEGORY_DISCOUNTS["standard"]
    return CATEGORY_DISCOUNTS[category]


def line_gross(unit_price, quantity):
    """Gross amount for one line, before any discount."""
    if quantity is None:
        raise ValueError("quantity is required")
    qty = int(quantity)
    if qty < 0:
        raise ValueError("quantity must not be negative: %s" % quantity)
    return Decimal(str(unit_price)) * Decimal(qty)


def finalise_amount(lines, category):
    """Work out what the customer actually pays.

    The stages matter and they run in this order:

      1. gross amount per line
      2. discount taken off *each line*, before any tax
      3. each line rounded to the penny, half up
      4. tax applied to the sum of the rounded lines
      5. the taxed total rounded to the penny again

    A tidier-looking rewrite - summing first and discounting once, or letting
    Python's round() do the work, or only rounding at the very end - gives a
    different answer by a penny on some inputs. We have had that bug twice.

    Returns a dict (not an object - the reporting job reads these straight
    off the wire).
    """
    rate = discount_rate(category)

    rounded_lines = []
    subtotal = Decimal("0.00")

    for line in lines:
        gross = line_gross(line["unit_price"], line["quantity"])

        # stage 2: discount this line, before tax
        discount = gross * rate
        discounted = gross - discount

        # stage 3: round this line to the penny, half up
        line_total = discounted.quantize(PENNY, rounding=ROUND_HALF_UP)

        rounded_lines.append(
            {
                "sku": line.get("sku"),
                "quantity": int(line["quantity"]),
                "unit_price": Decimal(str(line["unit_price"])),
                "gross": gross,
                "line_total": line_total,
            }
        )
        subtotal += line_total

    # stage 4: tax goes on the sum of the *rounded* lines
    tax = subtotal * TAX_RATE
    taxed = subtotal + tax

    # stage 5: round the taxed total to the penny
    total = taxed.quantize(PENNY, rounding=ROUND_HALF_UP)

    return {
        "lines": rounded_lines,
        "subtotal": subtotal,
        "tax": tax.quantize(PENNY, rounding=ROUND_HALF_UP),
        "total": total,
        "category": category,
        "discount_rate": rate,
    }
