# E-Commerce Order Processing System

Core order-processing logic for a small e-commerce platform, written in plain Python.
It validates orders, applies discounts and shipping rules, checks stock and payment,
updates inventory, and produces a sales report.

**Constraints followed:** no classes, no external libraries, no databases, no APIs and no
frameworks. The solution is built entirely from functions.

## Project Files

| File | Purpose |
|---|---|
| `order_processing.py` | The complete solution: validation, pricing, processing, inventory and reports. |
| `test.py` | Plain-Python test script covering all required edge cases. |
| `README.md` | This document. |

## Requirements

- Python 3.8 or newer
- Nothing to install

## How to Run

Run the program (it runs its built-in self-checks first, then processes the sample
orders and prints the results and the sales report):

```bash
python order_processing.py
```

Run the test script:

```bash
python test.py
```

Each check prints `PASS` or `FAIL`, followed by a summary such as `26/26 tests passed`.
The script exits with an error code if any check fails.

## Business Rules

### Discounts

| Subtotal | Discount |
|---|---|
| $1,000 or more | 15% |
| $500 or more | 10% |
| $200 or more | 5% |
| Below $200 | 0% |

### Shipping

| Subtotal | Shipping |
|---|---|
| $500 or more | Free |
| Below $500 | $20 |

### Order total

```
total = subtotal - discount + shipping
```

### Order statuses

| Status | Meaning | Stock reduced? | Counted as revenue? |
|---|---|---|---|
| `paid` | Valid order with `payment_status == "paid"` | Yes | Yes |
| `pending` | Valid order with `payment_status == "pending"` | No | No (amount due is still shown) |
| `rejected` | Failed validation | No | No |

Stock is reduced only after an order is fully validated and paid. Orders are processed
in sequence, so an earlier paid order can cause a later one to be rejected for
insufficient stock.

## Validation

An order is rejected, never crashing the program, when any of these is true.
All problems found are reported together, not just the first one.

- The order is not a dictionary, or `order_id` / `customer` is missing or blank
- `payment_status` is anything other than `"paid"` or `"pending"`
- `items` is missing, empty, or not a list
- A product ID is unknown or malformed
- A quantity is zero, negative, not a whole number, or a boolean
- The requested quantity exceeds available stock (duplicate lines for the same product
  are combined before checking)
- The products dictionary is empty or invalid
- A product record is broken (missing name or category, NaN/infinite/negative price,
  invalid stock)
- The `order_id` was already processed (duplicates are rejected without touching stock)
- A calculated amount is invalid or too large

## Configurable Processing

`process_order(order, products, **options)` accepts these keyword options:

| Option | Default | Effect |
|---|---|---|
| `apply_discount` | `True` | Apply the tiered discount |
| `include_shipping` | `True` | Add shipping cost |
| `free_shipping_threshold` | `500` | Subtotal at which shipping becomes free |
| `shipping_fee` | `20` | Flat shipping fee below the threshold |

Unknown option names (for example a typo such as `apply_discont`) and invalid values cause
the order to be rejected rather than being silently ignored.

```python
result = process_order(order, products, apply_discount=False, include_shipping=False)
```

## Main Functions

| Function | Description |
|---|---|
| `calculate_order_subtotal(order, products)` | Line totals and the order subtotal |
| `calculate_discount(subtotal)` | Discount amount for the subtotal |
| `calculate_shipping(subtotal, ...)` | Shipping cost for the subtotal |
| `calculate_total(subtotal, *adjustments)` | Subtotal plus any number of adjustments |
| `validate_order(order, products)` | List of all validation errors (empty if valid) |
| `process_order(order, products, **options)` | Validate, price and fulfil one order |
| `process_all_orders(orders, products, **options)` | Process a list of orders in sequence |
| `generate_customer_report(processed_orders)` | Top customer(s) and customer spending |
| `generate_product_report(processed_orders, products)` | Best-selling product(s) and low-stock items |
| `generate_sales_report(processed_orders, products)` | Complete sales report |
| `print_report(report, processed_orders, money)` | Print results and report |

## Sales Report

`generate_sales_report` returns a dictionary containing:

- `total_orders`, `paid_orders`, `pending_orders`, `rejected_orders`
- `total_revenue`, `total_discount`, `total_shipping` (paid orders only)
- `top_customers` and `top_spend` (ties return every tied customer)
- `best_products` and `best_product_units` (ties return every tied product)
- `unique_customers` and `categories_sold` (sets)
- `low_stock` (products at or below the limit, lowest first; default limit is 10)
- `rejection_details` (order ID and reasons for every rejected order)
- `warnings` (for example, an invalid `low_stock_limit` falls back to the default)

The report only reads data: it never changes the products or the processed orders.

## Python Concepts Demonstrated

| Concept | Where |
|---|---|
| `**kwargs` | `process_order(order, products, **options)` |
| `*args` | `sum_amounts(*amounts)`, `calculate_total(subtotal, *adjustments)` |
| `lambda` | Sorting customers, products and low-stock items in the reports |
| Comprehensions | Line items, error lists, tie detection, low-stock list |
| Sets | Unique customers, categories sold, duplicate order IDs |
| LEGB scopes | `make_money_formatter()` and `make_status_tracker()` closures; global values are read-only constants |

## Edge Cases Covered by `test.py`

1. Unknown product ID
2. Zero quantity
3. Negative quantity
4. Quantity greater than available stock
5. Order with no items
6. Invalid payment status
7. Empty products dictionary
8. Empty orders list
9. Multiple orders from the same customer
10. Ties in top-selling products
11. No low-stock products

It also checks discount tiers, shipping, paid and pending behaviour, inventory updates,
duplicate order IDs, invalid options, NaN prices and garbage input.

## Sample Output (starter data)

| Order | Customer | Status | Total |
|---|---|---|---|
| ORD001 | Ali | Paid | $1,062.50 (15% discount, free shipping) |
| ORD002 | Ahmed | Paid | $447.50 (5% discount, $20 shipping) |
| ORD003 | Ali | Pending | $145.00 (not counted as revenue) |

- Total revenue: **$1,510.00**
- Total discount: **$210.00**
- Shipping collected: **$20.00**
- Top customer: **Ali** ($1,062.50)
- Best-selling products: **Mouse** and **Keyboard** (tied at 2 units each)
- Low-stock products: **Laptop** (9 left)
- Final inventory: Laptop 9, Mouse 48, Keyboard 18, Monitor 14
