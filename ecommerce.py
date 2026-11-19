"""
E-Commerce Order Processing System
Plain functions only: no classes, external libraries, databases, APIs or frameworks.

Advanced features demonstrated
  * **kwargs  -> process_order(order, products, **options)
  * *args     -> sum_amounts(*amounts), calculate_total(subtotal, *adjustments)
  * lambda    -> sorting customers / products / low-stock items
  * comprehensions and sets (unique customers, categories, duplicate order IDs)
  * LEGB      -> make_money_formatter() and make_status_tracker() (closures)
"""

# ------------------------------------------------------------------ constants
# Global scope (the "G" in LEGB): read-only configuration. Functions only READ
# these values; no function ever changes a global variable.
DEFAULT_CURRENCY = "$"
DISCOUNT_TIERS = ((1000, 0.15), (500, 0.10), (200, 0.05))   # (minimum, rate)
FREE_SHIPPING_THRESHOLD = 500
SHIPPING_FEE = 20
MAX_AMOUNT = 10 ** 9            # upper sanity limit for prices, stock, options
DEFAULT_OPTIONS = {
    "include_shipping": True,
    "apply_discount": True,
    "free_shipping_threshold": FREE_SHIPPING_THRESHOLD,
    "shipping_fee": SHIPPING_FEE,
}
BOOLEAN_OPTIONS = ("include_shipping", "apply_discount")
NUMERIC_OPTIONS = ("free_shipping_threshold", "shipping_fee")
STATUSES = ("paid", "pending", "rejected")
DEFAULT_LOW_STOCK_LIMIT = 10
NUMBER_LIMIT = 10 ** 19         # larger numbers are ignored by the money helpers
TEXT_LIMIT = 30                 # longest piece of user text shown in an error message


# ------------------------------------------------------------------ starter data
def get_starter_products():
    """Return a fresh product catalogue (no shared global data)."""
    return {
        "P001": {"name": "Laptop", "price": 1200, "category": "Electronics", "stock": 10},
        "P002": {"name": "Mouse", "price": 25, "category": "Accessories", "stock": 50},
        "P003": {"name": "Keyboard", "price": 75, "category": "Accessories", "stock": 20},
        "P004": {"name": "Monitor", "price": 300, "category": "Electronics", "stock": 15},
    }


def get_starter_orders():
    """Return the sample orders."""
    return [
        {"order_id": "ORD001", "customer": "Ali",
         "items": [{"product_id": "P001", "quantity": 1},
                   {"product_id": "P002", "quantity": 2}],
         "payment_status": "paid"},
        {"order_id": "ORD002", "customer": "Ahmed",
         "items": [{"product_id": "P003", "quantity": 2},
                   {"product_id": "P004", "quantity": 1}],
         "payment_status": "paid"},
        {"order_id": "ORD003", "customer": "Ali",
         "items": [{"product_id": "P002", "quantity": 5}],
         "payment_status": "pending"},
    ]


# ------------------------------------------------------------------ safe helpers
def describe(value):
    """Short, safe text for error messages. Never calls repr() on unknown objects,
    so deeply nested or huge values cannot crash the message itself."""
    if isinstance(value, str):
        return repr(value[:TEXT_LIMIT]) + ("..." if len(value) > TEXT_LIMIT else "")
    if value is None or isinstance(value, (bool, float)):
        return repr(value)
    if isinstance(value, int):
        return repr(value) if abs(value) < 10 ** 15 else "<very large int>"
    return f"<{type(value).__name__}>"


def is_number(value):
    """True for a real, finite int/float of sensible size (not bool, NaN or inf)."""
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and value == value and abs(value) <= NUMBER_LIMIT)


def sum_amounts(*amounts):
    """Add any number of money amounts and round to cents. (*args)
    Values that are not usable numbers are ignored instead of crashing."""
    return round(sum(a for a in amounts if is_number(a)), 2)


def calculate_total(subtotal, *adjustments):
    """Subtotal plus any number of adjustments (negative = discount). (*args)"""
    return sum_amounts(subtotal, *adjustments)


# ------------------------------------------------------------------ validation
def is_valid_amount(value):
    """True for a finite, non-negative number up to MAX_AMOUNT (not bool/NaN/inf)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if value != value:                    # NaN is the only value not equal to itself
        return False
    return 0 <= value <= MAX_AMOUNT       # also rules out infinity


def is_valid_whole_number(value, minimum=0):
    """True for a real integer (not bool) between minimum and MAX_AMOUNT."""
    return (isinstance(value, int) and not isinstance(value, bool)
            and minimum <= value <= MAX_AMOUNT)


def check_product(product):
    """Return '' if the product record is usable, otherwise the problem."""
    if not isinstance(product, dict):
        return "Invalid product data"
    for field in ("name", "category"):
        if not isinstance(product.get(field), str) or not product[field].strip():
            return f"Invalid product {field}"
    if not is_valid_amount(product.get("price")):
        return "Invalid product price"
    if not is_valid_whole_number(product.get("stock")):
        return "Invalid product stock"
    return ""


def validate_order(order, products):
    """Return a list of ALL error messages. An empty list means the order is valid."""
    if not isinstance(order, dict):
        return ["Order is not a valid object"]
    if not isinstance(products, dict) or not products:
        return ["No products available"]

    errors = []
    for field in ("order_id", "customer"):
        if not isinstance(order.get(field), str) or not order[field].strip():
            errors.append(f"Missing or invalid {field}")
    if order.get("payment_status") not in ("paid", "pending"):
        errors.append(f"Invalid payment_status: {describe(order.get('payment_status'))}")

    items = order.get("items")
    if not isinstance(items, list) or not items:
        errors.append("Order has no items")
        return errors

    requested = {}                        # combined quantity per product
    for item in items:
        if not isinstance(item, dict):
            errors.append("Invalid item entry")
            continue
        pid, qty = item.get("product_id"), item.get("quantity")

        if not isinstance(pid, str) or pid not in products:
            errors.append(f"Invalid product ID: {describe(pid)}")
        elif not is_valid_whole_number(qty, minimum=1):
            errors.append(f"Invalid quantity for {pid}: {describe(qty)}")
        else:
            requested[pid] = requested.get(pid, 0) + qty

    for pid, qty in requested.items():    # each product checked once
        problem = check_product(products[pid])
        if problem:
            errors.append(f"{problem} for {pid}")
        elif qty > products[pid]["stock"]:
            errors.append(f"Insufficient stock for {pid}: requested {qty}, "
                          f"available {products[pid]['stock']}")
    return errors


# ------------------------------------------------------------------ calculations
def valid_lines(order, products):
    """(product_id, quantity) for every well-formed item; anything else is skipped."""
    items = order.get("items") if isinstance(order, dict) else None
    if not isinstance(items, list) or not isinstance(products, dict):
        return []
    return [(i["product_id"], i["quantity"]) for i in items
            if isinstance(i, dict) and isinstance(i.get("product_id"), str)
            and i["product_id"] in products
            and check_product(products[i["product_id"]]) == ""
            and is_valid_whole_number(i.get("quantity"), minimum=1)]


def calculate_order_subtotal(order, products):
    """Return (subtotal, line_items). Malformed items are skipped, so a bad or
    empty order gives (0, []) instead of crashing."""
    line_items = [{"product_id": pid, "quantity": qty,
                   "line_total": products[pid]["price"] * qty}
                  for pid, qty in valid_lines(order, products)]
    return sum_amounts(*[line["line_total"] for line in line_items]), line_items


def calculate_discount(subtotal):
    """Discount AMOUNT: 15% >= 1000, 10% >= 500, 5% >= 200, otherwise 0.
    An invalid subtotal (None, text, NaN...) earns no discount."""
    if not is_number(subtotal):
        return 0
    for minimum, rate in DISCOUNT_TIERS:
        if subtotal >= minimum:
            return round(subtotal * rate, 2)
    return 0


def calculate_shipping(subtotal, free_threshold=FREE_SHIPPING_THRESHOLD,
                       fee=SHIPPING_FEE):
    """Free shipping at or above the threshold, otherwise the flat fee.
    Invalid arguments fall back to the defaults (an invalid subtotal pays the fee)."""
    threshold = free_threshold if is_valid_amount(free_threshold) else FREE_SHIPPING_THRESHOLD
    fee = fee if is_valid_amount(fee) else SHIPPING_FEE
    return 0 if is_number(subtotal) and subtotal >= threshold else fee


# ------------------------------------------------------------------ options (**kwargs)
def resolve_options(options):
    """Merge options with defaults. Returns (options, error_message)."""
    unknown = sorted(key for key in options if key not in DEFAULT_OPTIONS)
    if unknown:
        return None, f"Unknown option(s): {', '.join(unknown)}"
    merged = {**DEFAULT_OPTIONS, **options}
    bad = [k for k in BOOLEAN_OPTIONS if not isinstance(merged[k], bool)]
    bad += [k for k in NUMERIC_OPTIONS if not is_valid_amount(merged[k])]
    if bad:
        return None, f"Invalid value for option(s): {', '.join(sorted(bad))}"
    return merged, None


# ------------------------------------------------------------------ processing
def clean_text(value):
    """Trimmed text, or 'UNKNOWN' if the value is not usable text."""
    return value.strip() if isinstance(value, str) and value.strip() else "UNKNOWN"


def build_rejection(order, errors):
    """Standard 'rejected' result; never lets a bad value leak into reports."""
    is_dict = isinstance(order, dict)
    return {
        "order_id": clean_text(order.get("order_id") if is_dict else None),
        "customer": clean_text(order.get("customer") if is_dict else None),
        "status": "rejected", "items": [], "subtotal": 0, "discount": 0,
        "shipping": 0, "total": 0, "errors": errors,
    }


def update_inventory(order, products):
    """Reduce stock for each well-formed item. Never lets stock go below zero and
    quietly skips malformed items instead of crashing."""
    for pid, qty in valid_lines(order, products):
        if qty <= products[pid]["stock"]:
            products[pid]["stock"] -= qty


def process_order(order, products, /, **options):
    """
    Validate, price and (if paid) fulfil one order.

    Options (**kwargs): include_shipping=True, apply_discount=True,
                        free_shipping_threshold=500, shipping_fee=20

    Status returned:
      'paid'     valid + paid    -> stock reduced, counts as revenue
      'pending'  valid + unpaid  -> priced (amount due kept), stock untouched,
                                    never counted as revenue
      'rejected' invalid         -> stock untouched
    """
    opts, option_error = resolve_options(options)
    if option_error:
        return build_rejection(order, [option_error])

    errors = validate_order(order, products)
    if errors:
        return build_rejection(order, errors)

    subtotal, line_items = calculate_order_subtotal(order, products)
    discount = calculate_discount(subtotal) if opts["apply_discount"] else 0
    shipping = (calculate_shipping(subtotal, opts["free_shipping_threshold"],
                                   opts["shipping_fee"])
                if opts["include_shipping"] else 0)
    total = calculate_total(subtotal, -discount, shipping)

    if not all(is_valid_amount(amount) for amount in (subtotal, discount, shipping, total)):
        return build_rejection(order, ["Calculated amount is invalid or too large"])

    status = "paid" if order["payment_status"] == "paid" else "pending"
    if status == "paid":
        update_inventory(order, products)

    return {
        "order_id": clean_text(order["order_id"]),
        "customer": clean_text(order["customer"]),   # " Ali " and "Ali" are one customer
        "status": status, "items": line_items, "subtotal": subtotal,
        "discount": discount, "shipping": shipping, "total": total, "errors": [],
    }


def process_all_orders(orders, products, /, **options):
    """
    Process orders in sequence, so earlier orders affect later stock checks.
    A repeated order_id is rejected so one order is never fulfilled twice.
    """
    if not isinstance(orders, list):
        return []

    seen_ids = set()
    results = []
    for order in orders:
        order_id = clean_text(order.get("order_id") if isinstance(order, dict) else None)
        if order_id in seen_ids:          # checked BEFORE processing: no stock change
            results.append(build_rejection(order, ["Duplicate order_id"]))
            continue
        result = process_order(order, products, **options)
        if result["status"] != "rejected":
            seen_ids.add(result["order_id"])
        results.append(result)
    return results


# ------------------------------------------------------------------ LEGB closures
def make_money_formatter(symbol=None):
    """Closure showing all four LEGB scopes."""
    if not isinstance(symbol, str):       # L: local variable
        symbol = DEFAULT_CURRENCY         # G: global (read-only) constant

    def format_money(amount):
        # E: 'symbol' comes from the enclosing function
        # B: format() is a built-in
        try:
            return symbol + format(amount, ".2f")
        except (TypeError, ValueError, OverflowError):
            return "N/A"                  # not a number: show a placeholder

    return format_money


def make_status_tracker():
    """Closure: 'counts' lives in the enclosing scope, so no global is needed."""
    counts = {status: 0 for status in STATUSES}

    def record(status):
        if status in counts:              # unknown statuses are ignored
            counts[status] += 1           # inner function updates enclosing data

    def summary():
        return dict(counts)               # a copy, so callers cannot alter it

    return record, summary


# ------------------------------------------------------------------ reports
def is_valid_result(result):
    """True only for a complete, correctly typed result built by process_order."""
    if not isinstance(result, dict) or result.get("status") not in STATUSES:
        return False
    if not all(isinstance(result.get(f), str) for f in ("order_id", "customer")):
        return False
    if result["status"] == "rejected":
        errors = result.get("errors")
        return isinstance(errors, list) and all(isinstance(e, str) for e in errors)
    items = result.get("items")
    if not isinstance(items, list):
        return False
    for line in items:
        if not (isinstance(line, dict) and isinstance(line.get("product_id"), str)
                and is_valid_whole_number(line.get("quantity"), minimum=1)):
            return False
    return all(is_valid_amount(result.get(k))
               for k in ("subtotal", "discount", "shipping", "total"))


def usable_results(processed_orders):
    """Keep only well-formed results, so reports never crash on bad data."""
    if not isinstance(processed_orders, list):
        return []
    return [o for o in processed_orders if is_valid_result(o)]


def product_label(products, product_id):
    """Product name, falling back to its ID if the record is missing or broken."""
    record = products.get(product_id) if isinstance(products, dict) else None
    if isinstance(record, dict) and isinstance(record.get("name"), str):
        return record["name"]
    return str(product_id)


def generate_customer_report(processed_orders):
    """Top customer(s) by spend on PAID orders (ties are all returned)."""
    results = usable_results(processed_orders)
    spending = {}
    for order in results:
        if order["status"] == "paid":
            spending[order["customer"]] = sum_amounts(
                spending.get(order["customer"], 0), order["total"])

    ranking = sorted(spending.items(), key=lambda pair: pair[1], reverse=True)
    top = [name for name, amount in ranking if amount == ranking[0][1]]
    return {
        "top_customers": top,
        "top_spend": ranking[0][1] if ranking else 0,
        "ranking": ranking,
        # set: customers with at least one valid (paid or pending) order
        "unique_customers": {o["customer"] for o in results
                             if o["status"] != "rejected"},
    }


def generate_product_report(processed_orders, products,
                            low_stock_limit=DEFAULT_LOW_STOCK_LIMIT):
    """Best-selling product(s) by units in PAID orders, plus low-stock items."""
    warnings = []
    if not is_valid_whole_number(low_stock_limit):
        warnings.append(f"Invalid low_stock_limit {describe(low_stock_limit)}; "
                        f"using {DEFAULT_LOW_STOCK_LIMIT}")
        low_stock_limit = DEFAULT_LOW_STOCK_LIMIT
    catalogue = products if isinstance(products, dict) else {}

    units = {}
    for order in usable_results(processed_orders):
        if order["status"] == "paid":
            for item in order["items"]:
                units[item["product_id"]] = (
                    units.get(item["product_id"], 0) + item["quantity"])

    ranking = sorted(units.items(), key=lambda pair: pair[1], reverse=True)
    best = [product_label(catalogue, pid)
            for pid, qty in ranking if qty == ranking[0][1]]

    low_stock = sorted(
        [{"product_id": pid, "name": info["name"], "stock": info["stock"]}
         for pid, info in catalogue.items()
         if check_product(info) == "" and info["stock"] <= low_stock_limit],
        key=lambda entry: entry["stock"],
    )
    return {
        "best_products": best,
        "best_product_units": ranking[0][1] if ranking else 0,
        "units_by_product": dict(ranking),
        # set: categories that actually sold
        "categories_sold": {catalogue[pid]["category"] for pid in units
                            if check_product(catalogue.get(pid)) == ""},
        "low_stock": low_stock,
        "warnings": warnings,
    }


def generate_sales_report(processed_orders, products,
                          low_stock_limit=DEFAULT_LOW_STOCK_LIMIT):
    """Full report. Reads results only: it never changes products or orders."""
    results = usable_results(processed_orders)
    record, summary = make_status_tracker()
    for order in results:
        record(order["status"])
    counts = summary()

    paid = [o for o in results if o["status"] == "paid"]
    report = {
        "total_orders": len(results),
        "paid_orders": counts["paid"],
        "pending_orders": counts["pending"],
        "rejected_orders": counts["rejected"],
        "total_revenue": sum_amounts(*[o["total"] for o in paid]),
        "total_discount": sum_amounts(*[o["discount"] for o in paid]),
        "total_shipping": sum_amounts(*[o["shipping"] for o in paid]),
        "rejection_details": [{"order_id": o["order_id"], "errors": o["errors"]}
                              for o in results if o["status"] == "rejected"],
    }
    report.update(generate_customer_report(results))
    product_report = generate_product_report(results, products, low_stock_limit)
    report.update(product_report)
    skipped = (len(processed_orders) - len(results)
               if isinstance(processed_orders, list) else 0)
    if skipped:
        report["warnings"] = product_report["warnings"] + [
            f"{skipped} malformed result(s) were ignored"]
    return report


def join_names(value):
    """Comma-separated text from a list, tuple or set; empty text for anything else."""
    if isinstance(value, set):
        value = sorted(str(v) for v in value)
    return ", ".join(str(v) for v in value) if isinstance(value, (list, tuple)) else ""


def print_report(report, processed_orders, money=None):
    """Print results and report. Bad or missing data is skipped, never a crash."""
    formatter = money if callable(money) else make_money_formatter()

    def money(amount):                    # a broken formatter shows N/A, not a crash
        try:
            return str(formatter(amount))
        except Exception:
            return "N/A"

    if not isinstance(report, dict):
        print("No report to display.")
        return
    get = report.get

    print("=" * 56)
    print("ORDER RESULTS")
    print("=" * 56)
    for o in usable_results(processed_orders):
        if o["status"] == "rejected":
            print(f"{o['order_id']}: REJECTED -> {'; '.join(o['errors'])}")
        else:
            print(f"{o['order_id']}: {o['status'].upper():8} "
                  f"subtotal={money(o['subtotal'])} discount={money(o['discount'])} "
                  f"shipping={money(o['shipping'])} total={money(o['total'])}")

    print("\n" + "=" * 56)
    print("SALES REPORT")
    print("=" * 56)
    print(f"Total orders:        {get('total_orders', 0)}")
    print(f"Paid orders:         {get('paid_orders', 0)}")
    print(f"Pending orders:      {get('pending_orders', 0)}")
    print(f"Rejected orders:     {get('rejected_orders', 0)}")
    print(f"Total revenue:       {money(get('total_revenue', 0))}")
    print(f"Discount given:      {money(get('total_discount', 0))}")
    print(f"Shipping collected:  {money(get('total_shipping', 0))}")
    print(f"Top customer(s):     {join_names(get('top_customers')) or 'None'}"
          f" ({money(get('top_spend', 0))})")
    print(f"Best-selling:        {join_names(get('best_products')) or 'None'}"
          f" ({get('best_product_units', 0)} units each)")
    print(f"Unique customers:    {join_names(get('unique_customers'))}")
    print(f"Categories sold:     {join_names(get('categories_sold'))}")
    print("Low-stock products:")
    low_stock = [p for p in (get("low_stock") or []) if isinstance(p, dict)] \
        if isinstance(get("low_stock"), list) else []
    for p in low_stock:
        print(f"  - {p.get('product_id', '?')} {p.get('name', '?')}: {p.get('stock', '?')} left")
    if not low_stock:
        print("  None")
    for warning in (get("warnings") if isinstance(get("warnings"), list) else []):
        print(f"Warning: {warning}")


# ------------------------------------------------------------------ tests
def make_order(items, status="paid", order_id="T1", customer="Test"):
    return {"order_id": order_id, "customer": customer,
            "items": items, "payment_status": status}


def item_of(product_id, quantity):
    return {"product_id": product_id, "quantity": quantity}


def mouse(qty):
    return [{"product_id": "P002", "quantity": qty}]


def run_tests():
    # --- discount / shipping boundaries and *args helpers
    assert [calculate_discount(s) for s in (1000, 999.99, 500, 499.99, 200, 199.99)] \
        == [150.0, round(999.99 * 0.10, 2), 50.0, round(499.99 * 0.05, 2), 10.0, 0]
    assert calculate_shipping(500) == 0 and calculate_shipping(499.99) == 20
    assert sum_amounts() == 0 and calculate_total(100, -10, 20) == 110

    # --- every kind of bad order is rejected, never crashes, never touches stock
    p = get_starter_products()
    bad_orders = [
        make_order([{"product_id": "X", "quantity": 1}]),
        make_order(mouse(0)), make_order(mouse(-3)), make_order(mouse("2")),
        make_order(mouse(1.5)), make_order(mouse(True)), make_order(mouse(10 ** 400)),
        make_order([{"product_id": ["P002"], "quantity": 1}]),
        make_order([]), make_order("not a list"), make_order(["oops"]),
        make_order(mouse(1), "refunded"), make_order(mouse(1), customer=""),
        make_order(mouse(1), order_id=""), make_order(mouse(1), order_id=None),
        {"customer": "A", "items": mouse(1), "payment_status": "paid"},   # no order_id
        None, {}, [], "text", 42,
    ]
    for bad in bad_orders:
        assert process_order(bad, p)["status"] == "rejected", bad
    assert p == get_starter_products()

    # --- all errors are reported, not just the first
    multi = process_order(make_order([{"product_id": "X", "quantity": -1}], "refunded",
                                     customer=""), p)
    assert len(multi["errors"]) >= 3

    # --- stock: too much, and duplicate lines that together exceed stock
    assert process_order(make_order([{"product_id": "P001", "quantity": 11}]), p)["status"] == "rejected"
    dup = make_order([{"product_id": "P001", "quantity": 6}, {"product_id": "P001", "quantity": 6}])
    assert process_order(dup, p)["status"] == "rejected"
    assert p["P001"]["stock"] == 10

    # --- broken product data: NaN / inf / overflow prices, missing name, bad stock
    for broken in (
        {"name": "M", "category": "A", "price": float("nan"), "stock": 5},
        {"name": "M", "category": "A", "price": float("inf"), "stock": 5},
        {"name": "M", "category": "A", "price": 10 ** 400, "stock": 5},
        {"name": "M", "category": "A", "price": 1e308, "stock": 5},
        {"name": "M", "category": "A", "price": "free", "stock": 5},
        {"category": "A", "price": 5, "stock": 5},                     # no name
        {"name": ["x"], "category": "A", "price": 5, "stock": 5},      # list name
        {"name": "M", "category": "A", "price": 5, "stock": True},
    ):
        assert process_order(make_order(mouse(1)), {"P002": broken})["status"] == "rejected", broken
    assert process_order(make_order(mouse(1)), {})["status"] == "rejected"
    assert process_order(make_order(mouse(1)), None)["status"] == "rejected"

    # --- pending keeps its amount due, stock untouched
    r = process_order(make_order(mouse(5), "pending"), p)
    assert r["status"] == "pending" and r["total"] == 145 and p["P002"]["stock"] == 50

    # --- paid: 25*8 = 200 -> $10 discount + $20 shipping = $210, stock reduced
    r = process_order(make_order(mouse(8)), p)
    assert (r["status"], r["subtotal"], r["discount"], r["shipping"], r["total"]) \
        == ("paid", 200, 10, 20, 210) and p["P002"]["stock"] == 42

    # --- **kwargs options (all four) and invalid options
    p = get_starter_products()
    o = make_order(mouse(8))
    assert process_order(o, p, include_shipping=False)["total"] == 190
    assert process_order(o, p, apply_discount=False)["total"] == 220
    assert process_order(o, p, apply_discount=False, include_shipping=False)["total"] == 200
    assert process_order(o, p, free_shipping_threshold=100)["total"] == 190
    assert process_order(o, p, shipping_fee=5)["total"] == 195
    for bad_opt in ({"apply_discont": False}, {"include_shipping": "yes"},
                    {"shipping_fee": -1}, {"free_shipping_threshold": float("nan")},
                    {"shipping_fee": True}):
        assert process_order(o, p, **bad_opt)["status"] == "rejected", bad_opt

    # --- sequential stock, duplicate order IDs (stock must not change for a duplicate)
    p = get_starter_products()
    res = process_all_orders([
        make_order([{"product_id": "P001", "quantity": 9}], order_id="A"),
        make_order([{"product_id": "P001", "quantity": 2}], order_id="B"),   # only 1 left
        make_order(mouse(1), order_id="A"),                                   # duplicate
        make_order(mouse(1), "pending", order_id="C"),
        make_order(mouse(1), "pending", order_id="C"),                        # duplicate
    ], p)
    assert [x["status"] for x in res] == ["paid", "rejected", "rejected", "pending", "rejected"]
    assert p["P001"]["stock"] == 1 and p["P002"]["stock"] == 50
    assert process_all_orders("nope", p) == []

    # --- whitespace in names, ties
    p = get_starter_products()
    res = process_all_orders([
        make_order(mouse(4), order_id="1", customer=" Ann "),
        make_order(mouse(4), order_id="2", customer="Bob"),
        make_order(mouse(1), "pending", order_id="3", customer="Ann"),
    ], p)
    rep = generate_sales_report(res, p)
    assert rep["unique_customers"] == {"Ann", "Bob"}       # " Ann " == "Ann"
    assert rep["top_customers"] == ["Ann", "Bob"]          # tie at $120 each
    assert rep["best_products"] == ["Mouse"] and rep["best_product_units"] == 8

    # --- report never crashes on bad inputs and never changes anything
    for bad_results in (None, "x", 5, [None, 1, {}, {"status": "weird"}]):
        for bad_products in (None, [], "x", {}, {"P002": {"price": 1}}):
            rep = generate_sales_report(bad_results, bad_products)
            assert rep["total_orders"] == 0 and rep["total_revenue"] == 0
    rep = generate_sales_report(res, {"P002": {"price": 5, "stock": 5}})   # broken catalogue
    assert rep["best_products"] == ["P002"] and rep["low_stock"] == []
    for bad_limit in ("5", -1, None, 2.5, True):
        assert generate_sales_report(res, p, low_stock_limit=bad_limit)["warnings"]
    before = get_starter_products()
    snapshot = {k: dict(v) for k, v in p.items()}
    generate_sales_report(res, p)
    generate_sales_report(res, p)
    assert p == snapshot and before != snapshot            # reports leave stock alone

    # --- empty report
    rep = generate_sales_report([], get_starter_products())
    assert rep["total_revenue"] == 0 and rep["top_customers"] == []
    assert rep["best_products"] == [] and rep["unique_customers"] == set()

    # --- regression: option names that clash with parameter names, hostile values
    deep = []
    for _ in range(100000):
        deep = [deep]
    p = get_starter_products()
    r = process_order(make_order(mouse(1)), p, order=1)
    assert r["status"] == "rejected" and "order" in r["errors"][0]
    assert process_order(make_order(mouse(1)), p, products=1)["status"] == "rejected"
    assert process_all_orders([], p, orders=1) == []
    for hostile in (make_order(mouse(1), deep), make_order([item_of(deep, 1)]),
                    make_order([item_of("P002", deep)]), make_order(mouse(10 ** 5000))):
        assert process_order(hostile, p)["status"] == "rejected"

    # --- regression: malformed results, helpers and money formatter never crash
    good = process_order(make_order(mouse(1)), get_starter_products())
    bad_results = [{"status": "paid"}, dict(good, total="12"), dict(good, items=5),
                   dict(good, customer=["x"]), {"status": "rejected"},
                   dict(good, items=[{"product_id": ["a"], "quantity": 1}])]
    rep = generate_sales_report(bad_results + [good], get_starter_products())
    assert rep["total_orders"] == 1 and any("ignored" in w for w in rep["warnings"])
    assert calculate_discount(None) == 0 and calculate_shipping(None) == 20
    assert sum_amounts("a", 5, None, float("nan")) == 5
    assert calculate_order_subtotal({}, p) == (0, []) and update_inventory({}, p) is None
    assert make_money_formatter()("x") == "N/A" and make_money_formatter(5)(1) == "$1.00"
    make_status_tracker()[0]("weird")

    # --- scope helpers
    assert make_money_formatter()(5) == "$5.00" and make_money_formatter("PKR ")(5) == "PKR 5.00"
    print("All tests passed.\n")


# ------------------------------------------------------------------ main
def main():
    run_tests()

    products = get_starter_products()
    orders = get_starter_orders() + [
        # extra edge cases
        {"order_id": "ORD004", "customer": "Sara",
         "items": [{"product_id": "P999", "quantity": 1}], "payment_status": "paid"},
        {"order_id": "ORD005", "customer": "Sara",
         "items": [{"product_id": "P001", "quantity": 50}], "payment_status": "paid"},
        {"order_id": "ORD006", "customer": "Bilal",
         "items": [{"product_id": "P002", "quantity": -2}], "payment_status": "paid"},
        {"order_id": "ORD001", "customer": "Ali",            # duplicate order ID
         "items": [{"product_id": "P002", "quantity": 1}], "payment_status": "paid"},
    ]

    money = make_money_formatter()
    processed = process_all_orders(orders, products)
    report = generate_sales_report(processed, products)
    print_report(report, processed, money)

    print("\nInventory after processing (real product data is updated):")
    for pid, info in products.items():
        print(f"  {pid} {info['name']}: {info['stock']}")

    print("\n--- Same orders with apply_discount=False, include_shipping=False ---")
    products_2 = get_starter_products()
    processed_2 = process_all_orders(orders, products_2,
                                     apply_discount=False, include_shipping=False)
    report_2 = generate_sales_report(processed_2, products_2)
    print(f"Revenue: {money(report_2['total_revenue'])} | "
          f"Discount: {money(report_2['total_discount'])} | "
          f"Shipping: {money(report_2['total_shipping'])}")


if __name__ == "__main__":
    main()