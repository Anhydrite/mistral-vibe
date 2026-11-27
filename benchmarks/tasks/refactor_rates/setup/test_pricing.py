from pricing.rates import tax_rate
from pricing.orders import total_cents, apply_discount
from pricing.invoices import invoice_total

assert tax_rate("fr") == 0.20
assert tax_rate("DE") == 0.19
assert tax_rate("es") == 0.21
assert tax_rate("XX") == 0.0
assert total_cents(1000, 2, "FR") == 2400
assert total_cents(1000, 1, "DE") == 1190
assert invoice_total([(1000, 2), (500, 1)], "ES") == 3025
assert apply_discount(2400, "WELCOME10") == 2160
try:
    apply_discount(2400, "NOPE")
except ValueError:
    pass
else:
    raise AssertionError("invalid code must raise ValueError")
print("ALL TESTS PASSED")
