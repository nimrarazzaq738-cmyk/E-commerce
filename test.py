"""Plain-Python tests for order_processing.py (no pytest, no libraries).
Run from the same folder:  python test.py"""
import ecommerce as op

results = []                                    # (test name, passed?)

def check(name, condition):
    results.append((name, bool(condition)))

def fresh():
    return op.get_starter_products()

def item(pid, qty):
    return {"product_id": pid, "quantity": qty}

def order(items, status="paid", oid="T1", customer="Test"):
    return {"order_id": oid, "customer": customer, "items": items, "payment_status": status}

def is_rejected(an_order, products=None):
    """True if the order is rejected AND the products were left untouched."""
    products = fresh() if products is None else products
    before = repr(products)
    return op.process_order(an_order, products)["status"] == "rejected" and repr(products) == before

def report_for(orders, products, **options):
    return op.generate_sales_report(op.process_all_orders(orders, products), products, **options)

def required_edge_cases():
    check("1. unknown product ID", is_rejected(order([item("P999", 1)])))
    check("2. zero quantity", is_rejected(order([item("P002", 0)])))
    check("3. negative quantity", is_rejected(order([item("P002", -2)])))
    p = fresh()
    check("4a. quantity above stock", is_rejected(order([item("P001", 11)])))
    check("4b. quantity equal to stock is accepted",
          op.process_order(order([item("P001", 10)]), p)["status"] == "paid" and p["P001"]["stock"] == 0)
    check("5. order with no items", is_rejected(order([])) and is_rejected(order(None)))
    check("6. invalid payment status",
          all(is_rejected(order([item("P002", 1)], s)) for s in ("refunded", "PAID", None)))
    check("7a. empty products dictionary", is_rejected(order([item("P001", 1)]), {}))
    check("7b. report with empty products",
          report_for([order([item("P001", 1)])], {})["rejected_orders"] == 1)
    report = report_for([], fresh())
    check("8a. empty orders list", op.process_all_orders([], fresh()) == [])
    check("8b. empty report is all zeros", report["total_orders"] == 0 and report["total_revenue"] == 0
          and report["top_customers"] == [] and report["best_products"] == [])
    report = report_for([order([item("P002", 4)], oid="A", customer="Ali"),
                         order([item("P002", 4)], oid="B", customer="Ali"),
                         order([item("P003", 1)], oid="C", customer="Sara")], fresh())
    check("9. same customer: spend combined, counted once",
          report["top_customers"] == ["Ali"] and report["top_spend"] == 240
          and report["unique_customers"] == {"Ali", "Sara"})
    report = report_for(op.get_starter_orders(), fresh())
    check("10. tie in top-selling products", sorted(report["best_products"]) == ["Keyboard", "Mouse"])
    check("11a. no low-stock products", report_for([], fresh(), low_stock_limit=5)["low_stock"] == [])
    check("11b. low-stock product appears when stock is low",
          [e["name"] for e in report["low_stock"]] == ["Laptop"])

def business_rules():
    check("discount tiers", [op.calculate_discount(s) for s in (199.99, 200, 500, 1000)] == [0, 10, 50, 150])
    check("shipping rule", op.calculate_shipping(499.99) == 20 and op.calculate_shipping(500) == 0)
    p = fresh()
    r = op.process_order(order([item("P002", 8)]), p)               # $200 -> 5% off + $20
    check("paid order totals and stock",
          (r["discount"], r["shipping"], r["total"]) == (10, 20, 210) and p["P002"]["stock"] == 42)
    p = fresh()
    r = op.process_order(order([item("P002", 5)], "pending"), p)
    check("pending: stock kept, amount due kept",
          r["status"] == "pending" and r["total"] == 145 and p["P002"]["stock"] == 50)
    p = fresh()
    report = report_for(op.get_starter_orders(), p)
    check("starter data report", (report["paid_orders"], report["pending_orders"]) == (2, 1)
          and report["total_revenue"] == 1510 and report["total_discount"] == 210
          and report["total_shipping"] == 20 and report["top_customers"] == ["Ali"])
    check("real inventory updated", [p[k]["stock"] for k in sorted(p)] == [9, 48, 18, 14])

def extra_edge_cases():
    p = fresh()
    done = op.process_all_orders([order([item("P002", 1)], oid="A"),
                                  order([item("P002", 1)], oid="A")], p)
    check("duplicate order ID rejected, stock reduced once",
          [r["status"] for r in done] == ["paid", "rejected"] and p["P002"]["stock"] == 49)
    r = op.process_order(order([item("P002", 8)]), fresh(), apply_discount=False, include_shipping=False)
    check("options turn off discount and shipping", r["total"] == 200)
    check("misspelled option is rejected",
          op.process_order(order([item("P002", 1)]), fresh(), apply_discont=False)["status"] == "rejected")
    nan_catalogue = {"P1": {"name": "X", "category": "Y", "price": float("nan"), "stock": 5}}
    check("NaN price rejected", is_rejected(order([item("P1", 1)]), nan_catalogue))
    check("garbage orders never crash", all(is_rejected(o) for o in (None, {}, [], "text", 42)))

if __name__ == "__main__":
    required_edge_cases()
    business_rules()
    extra_edge_cases()
    for name, ok in results:
        print(("PASS  " if ok else "FAIL  ") + name)
    failed = [name for name, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} tests passed")
    if failed:
        raise SystemExit(1)