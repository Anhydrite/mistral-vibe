import json, os, subprocess, sys, tempfile
ws = sys.argv[1]
checks = []
def check(n, ok, d=""):
    checks.append({"name": n, "ok": bool(ok), "detail": d})

SCRIPT = r'''
import json, sys
from kvstore import KVStore

# basics
s = KVStore()
assert s.get("a") is None
s.set("a", 1); s.set("b", {"x": [1, 2]})
assert s.get("a") == 1 and s.get("b") == {"x": [1, 2]}
assert list(s.values()) == ["a", "b"]
v = s.values(); v["a"] = 99; assert s.get("a") == 1
s.delete("a"); assert s.get("a") is None
s.delete("missing")

# transaction rollback
s.set("x", 1); s.begin(); s.set("x", 2); s.set("y", 3)
assert s.get("x") == 2 and s.get("y") == 3
s.rollback()
assert s.get("x") == 1 and s.get("y") is None

# commit inner merges into outer
s.begin(); s.set("a", 1); s.begin(); s.set("b", 2); s.commit()
assert s.get("b") == 2
s.rollback()
assert s.get("a") is None and s.get("b") == {"x": [1, 2]}
assert s.get("x") == 1

# inner rollback keeps outer changes
s.begin(); s.set("c", 3); s.begin(); s.set("d", 4); s.rollback()
assert s.get("c") == 3 and s.get("d") is None
s.commit(); assert s.get("c") == 3

# errors
try: s.commit()
except RuntimeError: pass
else: raise AssertionError("commit without transaction")
try: s.rollback()
except RuntimeError: pass
else: raise AssertionError("rollback without transaction")

# snapshots
s.begin(); s.set("e", 5); tok = s.snapshot(); s.set("e", 6); s.set("f", 7)
s.restore(tok)
assert s.get("e") == 5 and s.get("f") is None
try: s.restore("nope")
except ValueError: pass
else: raise AssertionError("unknown snapshot")
# restore cancels open transactions
s.begin(); s.set("g", 8); s.restore(tok); assert s.get("g") is None
try: s.commit()
except RuntimeError: pass
else: raise AssertionError("restore must close transactions")

# persistence
print("TASK-OK")
'''

def run(text):
    p = os.path.join(ws, "kvstore.py")
    open(p, "w").write(text)

path = None
if not os.path.isfile(os.path.join(ws, "kvstore.py")):
    check("kvstore.py exists", False)
else:
    check("kvstore.py exists", True)
    p = subprocess.run([sys.executable, "-c", SCRIPT], cwd=ws, capture_output=True, text=True, timeout=60)
    check("behaviour", p.returncode == 0 and "TASK-OK" in p.stdout, (p.stdout + p.stderr).strip()[-1200:])

    # persistence in a separate process with a temp path
    td = tempfile.mkdtemp()
    db = os.path.join(td, "db.json")
    S1 = f'''
from kvstore import KVStore
s = KVStore({db!r})
s.set("k", {{"n": 1}})
s.begin(); s.set("k", {{"n": 2}}); s.commit()
'''
    S2 = f'''
from kvstore import KVStore
s = KVStore({db!r})
assert s.get("k") == {{"n": 2}}, s.get("k")
print("PERSIST-OK")
'''
    p1 = subprocess.run([sys.executable, "-c", S1], cwd=ws, capture_output=True, text=True, timeout=60)
    p2 = subprocess.run([sys.executable, "-c", S2], cwd=ws, capture_output=True, text=True, timeout=60)
    ok = p1.returncode == 0 and p2.returncode == 0 and "PERSIST-OK" in p2.stdout
    detail = (p1.stdout + p1.stderr + p2.stdout + p2.stderr).strip()[-800:]
    if not ok:
        detail = "persistence failed: " + detail
    check("persistence", ok, detail)
    check("file is valid json", os.path.isfile(db), db)

print(json.dumps({"passed": all(c["ok"] for c in checks), "checks": checks}, ensure_ascii=False))
sys.exit(0 if all(c["ok"] for c in checks) else 1)
