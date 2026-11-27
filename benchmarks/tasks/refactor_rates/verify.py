import hashlib, json, os, subprocess, sys
ws = sys.argv[1]
checks = []
def check(n, ok, d=""):
    checks.append({"name": n, "ok": bool(ok), "detail": d})

TEST_SHA = "fe439363b8b80b83b4874fbdbfecd433e7d843f8e8c82e50a68a67730dc974e2"
test = os.path.join(ws, "test_pricing.py")
check("test_pricing.py unchanged", os.path.isfile(test) and hashlib.sha256(open(test,"rb").read()).hexdigest() == TEST_SHA)

p = subprocess.run([sys.executable, "test_pricing.py"], cwd=ws, capture_output=True, text=True, timeout=60)
check("provided tests pass", p.returncode == 0 and "ALL TESTS PASSED" in p.stdout, (p.stdout + p.stderr)[-800:])

HIDDEN = r'''
from pricing.rates import tax_rate
from pricing.orders import total_cents, apply_discount
from pricing.invoices import invoice_total
assert tax_rate("Fr") == 0.20 and tax_rate("de") == 0.19 and tax_rate("eS") == 0.21
assert tax_rate("") == 0.0
assert total_cents(999, 3, "XX") == 2997
assert total_cents(100, 1, "ES") == 121
assert invoice_total([], "FR") == 0
assert invoice_total([(1000, 1)], "DE") == 1190
assert apply_discount(1000, "WELCOME10") == 900
assert apply_discount(999, "WELCOME10") == 899
try: apply_discount(100, "X")
except ValueError: pass
else: raise AssertionError("bad code")
print("HIDDEN-OK")
'''
h = subprocess.run([sys.executable, "-c", HIDDEN], cwd=ws, capture_output=True, text=True, timeout=60)
check("hidden behaviour", h.returncode == 0 and "HIDDEN-OK" in h.stdout, (h.stdout + h.stderr)[-800:])

src = {f: open(os.path.join(ws, "pricing", f)).read() for f in ("orders.py", "invoices.py", "rates.py") if os.path.isfile(os.path.join(ws, "pricing", f))}
dupes = [f for f, s in src.items() if f != "rates.py" and "0.19" in s]
check("no duplicated rate table", not dupes, f"duplicated in {dupes}")

print(json.dumps({"passed": all(c["ok"] for c in checks), "checks": checks}, ensure_ascii=False))
sys.exit(0 if all(c["ok"] for c in checks) else 1)
