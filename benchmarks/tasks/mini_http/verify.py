import json, os, socket, subprocess, sys, tempfile, time, urllib.error, urllib.request
ws = sys.argv[1]
checks = []
def check(n, ok, d=""):
    checks.append({"name": n, "ok": bool(ok), "detail": d})

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def req(port, method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method,
                               headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            raw = resp.read()
            return resp.status, dict(resp.headers), (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: parsed = json.loads(raw) if raw else None
        except Exception: parsed = raw.decode(errors="replace")
        return e.code, dict(e.headers), parsed

if not os.path.isfile(os.path.join(ws, "server.py")):
    check("server.py exists", False)
else:
    check("server.py exists", True)
    td = tempfile.mkdtemp(); data = os.path.join(td, "data.json"); port = free_port()
    proc = subprocess.Popen([sys.executable, "server.py", "--port", str(port), "--data", data],
                            cwd=ws, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            start_new_session=True)
    try:
        ready = False
        for _ in range(60):
            try:
                st, _, body = req(port, "GET", "/items")
                if st == 200: ready = True; break
            except Exception: time.sleep(0.1)
        check("server starts and answers", ready)
        if ready:
            st, h, body = req(port, "GET", "/items")
            check("GET empty list", st == 200 and body == [] and "json" in h.get("Content-Type",""), f"{st} {body}")
            st, h, a = req(port, "POST", "/items", {"name": "a", "qty": 2})
            check("POST creates", st == 201 and isinstance(a, dict) and "id" in a and a.get("name") == "a", f"{st} {a}")
            st, _, b = req(port, "POST", "/items", {"name": "b"})
            check("POST second", st == 201 and b.get("id") != a.get("id"), f"{st} {b}")
            st, _, lst = req(port, "GET", "/items")
            check("GET two", st == 200 and len(lst) == 2, f"{st} {lst}")
            st, _, one = req(port, "GET", f"/items/{a['id']}")
            check("GET one", st == 200 and one.get("qty") == 2, f"{st} {one}")
            st, _, patched = req(port, "PATCH", f"/items/{a['id']}", {"qty": 5})
            check("PATCH merges", st == 200 and patched.get("qty") == 5 and patched.get("name") == "a", f"{st} {patched}")
            st, _, missing = req(port, "GET", "/items/does-not-exist")
            check("GET missing 404", st == 404, f"{st} {missing}")
            st, _, bad = req(port, "POST", "/items", None)
            check("POST invalid 400", st == 400, f"{st}")
            st, _, _ = req(port, "DELETE", f"/items/{b['id']}")
            check("DELETE 204", st == 204, f"{st}")
            st, _, _ = req(port, "DELETE", f"/items/{b['id']}")
            check("DELETE missing 404", st == 404, f"{st}")
            st, h, nf = req(port, "GET", "/nope")
            check("unknown route 404 json", st == 404 and isinstance(nf, dict) and nf.get("error") == "not found", f"{st} {nf}")
            time.sleep(0.2)
            try:
                disk = json.load(open(data))
                check("persisted data", isinstance(disk, (list, dict)) and len(disk) == 1, str(disk)[:200])
            except Exception as e:
                check("persisted data", False, repr(e))
    finally:
        proc.kill()
        try: proc.wait(timeout=5)
        except Exception: pass

print(json.dumps({"passed": all(c["ok"] for c in checks), "checks": checks}, ensure_ascii=False))
sys.exit(0 if all(c["ok"] for c in checks) else 1)
