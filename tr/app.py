"""
EN ↔ AR Translator — Flask Web App
════════════════════════════════════════════
pip install flask argostranslate
python app.py
Open  http://localhost:5000
════════════════════════════════════════════
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# ── Package readiness flags (written by background thread, read by routes) ──────
_pkg = {"en_ar": False, "ar_en": False, "msg": "Starting…", "busy": True}
_pkg_lock = threading.Lock()

# ── History ──────────────────────────────────────────────────────────────────────
HIST_PATH = Path(__file__).parent / "translation_history.json"


class HistoryManager:
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()
        self._rows: list = []
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                d = json.loads(self._path.read_text("utf-8"))
                self._rows = d if isinstance(d, list) else []
            except Exception:
                self._rows = []

    def _save(self):
        self._path.write_text(
            json.dumps(self._rows, ensure_ascii=False, indent=2), "utf-8"
        )

    def add(self, sl: str, tl: str, src: str, tgt: str):
        with self._lock:
            self._rows.append({
                "ts":  datetime.now().strftime("%Y-%m-%d  %H:%M"),
                "sl":  sl, "tl": tl,
                "src": src.strip(),
                "tgt": tgt.strip(),
            })
            self._save()

    def all(self) -> list:
        with self._lock:
            return list(reversed(self._rows))

    def search(self, q: str) -> list:
        q = q.lower()
        with self._lock:
            return list(reversed([
                r for r in self._rows
                if q in r["src"].lower() or q in r["tgt"].lower()
            ]))

    def delete_oldest(self, n: int) -> int:
        with self._lock:
            n = max(0, min(n, len(self._rows)))
            self._rows = self._rows[n:]
            self._save()
            return n

    def count(self) -> int:
        with self._lock:
            return len(self._rows)


hist = HistoryManager(HIST_PATH)


# ── Background package bootstrap ─────────────────────────────────────────────────
def _bootstrap():
    # Phase 1: check what is already installed — pure local disk read, no network.
    # We do this BEFORE any other argostranslate call so an offline startup with
    # pre-installed packages never touches the network.
    try:
        import argostranslate.package as atp
    except Exception as ex:
        with _pkg_lock:
            _pkg["busy"] = False
            _pkg["msg"]  = f"err:Cannot import argostranslate: {ex}"
        return

    with _pkg_lock:
        _pkg["msg"] = "Checking installed packages…"

    try:
        installed = {(p.from_code, p.to_code) for p in atp.get_installed_packages()}
    except Exception:
        installed = set()

    need_ea = ("en", "ar") not in installed
    need_ae = ("ar", "en") not in installed

    # Phase 2: if both packages are present we are done — no network needed.
    if not need_ea and not need_ae:
        with _pkg_lock:
            _pkg["en_ar"] = True
            _pkg["ar_en"] = True
            _pkg["busy"]  = False
            _pkg["msg"]   = "ready"
        return

    # Phase 3: packages are missing — attempt network download.
    with _pkg_lock:
        _pkg["msg"] = "Downloading package index (internet required for first install)…"

    try:
        atp.update_package_index()
    except Exception as ex:
        with _pkg_lock:
            _pkg["busy"] = False
            _pkg["msg"]  = (
                "err:No internet connection. "
                "Run once with internet to install EN↔AR packages, "
                "then the app works offline forever."
            )
        return

    try:
        for pkg in atp.get_available_packages():
            if pkg.from_code == "en" and pkg.to_code == "ar" and need_ea:
                with _pkg_lock:
                    _pkg["msg"] = "Installing EN→AR package…"
                atp.install_from_path(pkg.download())
                need_ea = False
            elif pkg.from_code == "ar" and pkg.to_code == "en" and need_ae:
                with _pkg_lock:
                    _pkg["msg"] = "Installing AR→EN package…"
                atp.install_from_path(pkg.download())
                need_ae = False
            if not need_ea and not need_ae:
                break
    except Exception as ex:
        with _pkg_lock:
            _pkg["busy"] = False
            _pkg["msg"]  = f"err:Install failed: {ex}"
        return

    # Phase 4: verify
    try:
        final = {(p.from_code, p.to_code) for p in atp.get_installed_packages()}
    except Exception:
        final = set()

    en_ar = ("en", "ar") in final
    ar_en = ("ar", "en") in final

    with _pkg_lock:
        _pkg["en_ar"] = en_ar
        _pkg["ar_en"] = ar_en
        _pkg["busy"]  = False
        if en_ar and ar_en:
            _pkg["msg"] = "ready"
        else:
            missing = [l for l, ok in [("EN→AR", en_ar), ("AR→EN", ar_en)] if not ok]
            _pkg["msg"] = "err:Could not install: " + ", ".join(missing)


threading.Thread(target=_bootstrap, daemon=True).start()


# ── Routes ────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    with _pkg_lock:
        return jsonify(dict(_pkg))


@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.get_json(force=True) or {}
    text = data.get("text", "").strip()
    sl   = data.get("from_lang", "en")
    tl   = data.get("to_lang",   "ar")

    if not text:
        return jsonify({"result": ""})

    with _pkg_lock:
        ready = _pkg["en_ar"] if sl == "en" else _pkg["ar_en"]
    if not ready:
        return jsonify({"error": "Packages not ready yet"}), 503

    try:
        import argostranslate.translate as att
        import re as _re

        # Split on BOTH English comma "," AND Arabic comma "،" (U+060C).
        # Without splitting on "،", Arabic input is sent as one giant string
        # and reliably hits argostranslate's internal content filter, which
        # silently truncates output mid-sentence.
        # We preserve which separator each position used so we can restore
        # the correct separator style in the output.
        SEP_RE = _re.compile(r'([،,])')
        tokens = SEP_RE.split(text)   # ['chunk', ',', 'chunk', '،', ...]

        parts = []       # (text_chunk, original_separator)
        i = 0
        while i < len(tokens):
            chunk = tokens[i].strip()
            sep_char = tokens[i + 1] if i + 1 < len(tokens) else ""
            i += 2
            if chunk:
                parts.append((chunk, sep_char))

        out_sep = "،" if tl == "ar" else ","
        results = []

        for chunk, _ in parts:
            try:
                r = att.translate(chunk, sl, tl)
                results.append(r.strip() if r and r.strip() else chunk)
            except Exception:
                results.append(chunk)

        result = (out_sep + "  ").join(results)

    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

    if result:
        hist.add(sl, tl, text, result)

    return jsonify({"result": result})


@app.route("/api/history")
def api_history():
    q       = request.args.get("q", "").strip()
    entries = hist.search(q) if q else hist.all()
    return jsonify({"entries": entries, "count": hist.count()})


@app.route("/api/history/delete", methods=["POST"])
def api_history_delete():
    data    = request.get_json(force=True) or {}
    n       = int(data.get("n", 0))
    deleted = hist.delete_oldest(n)
    return jsonify({"deleted": deleted, "count": hist.count()})


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5001, threaded=True)