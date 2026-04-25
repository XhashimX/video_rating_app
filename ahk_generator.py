"""
AutoHotkey v2 Script Generator for PC Gaming
=============================================
pip install customtkinter

New in this version:
  - Key Capture Mode: click any slot button to capture the next keyboard /
    mouse press instead of scrolling through the dropdown list.
    Toggle it ON/OFF from the header bar.
  - Default save folder: C:\\Users\\Stark\\Documents\\AutoHotkey
  - Script Name field: leave empty for an auto-generated filename.
"""

import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime

# -----------------------------------------------------------------------
#  APPEARANCE
# -----------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# -----------------------------------------------------------------------
#  DEFAULT SAVE PATH
# -----------------------------------------------------------------------
DEFAULT_SAVE_DIR = r"C:\Users\Stark\Documents\AutoHotkey"

# -----------------------------------------------------------------------
#  KEY TABLES  (display name  →  AHK v2 token)
# -----------------------------------------------------------------------

_KEY_TABLE: list = []

def _r(display: str, ahk: str) -> None:
    _KEY_TABLE.append((display, ahk))

for _c in "abcdefghijklmnopqrstuvwxyz":
    _r(_c.upper(), _c)
for _n in range(10):
    _r(str(_n), str(_n))
for _i in range(1, 13):
    _r(f"F{_i}", f"F{_i}")
for _d, _a in [
    ("Ctrl","Ctrl"),         ("Shift","Shift"),
    ("Alt","Alt"),           ("Win","LWin"),
    ("Left Ctrl","LCtrl"),   ("Right Ctrl","RCtrl"),
    ("Left Shift","LShift"), ("Right Shift","RShift"),
    ("Left Alt","LAlt"),     ("Right Alt","RAlt"),
    ("Left Win","LWin"),     ("Right Win","RWin"),
]:
    _r(_d, _a)
for _d, _a in [
    ("Enter","Enter"),         ("Space","Space"),
    ("Tab","Tab"),             ("Backspace","Backspace"),
    ("Escape","Escape"),       ("Delete","Delete"),
    ("Insert","Insert"),       ("Home","Home"),
    ("End","End"),             ("Page Up","PgUp"),
    ("Page Down","PgDn"),      ("Up Arrow","Up"),
    ("Down Arrow","Down"),     ("Left Arrow","Left"),
    ("Right Arrow","Right"),   ("Caps Lock","CapsLock"),
    ("Num Lock","NumLock"),    ("Scroll Lock","ScrollLock"),
    ("Print Screen","PrintScreen"), ("Pause","Pause"),
]:
    _r(_d, _a)
for _n in range(10):
    _r(f"Numpad {_n}", f"Numpad{_n}")
for _d, _a in [
    ("Numpad Enter","NumpadEnter"), ("Numpad +","NumpadAdd"),
    ("Numpad -","NumpadSub"),       ("Numpad *","NumpadMult"),
    ("Numpad /","NumpadDiv"),       ("Numpad .","NumpadDot"),
]:
    _r(_d, _a)
for _d, _a in [
    ("- Minus","-"),     ("= Equals","="),
    ("[ Bracket","["),   ("] Bracket","]"),
    ("; Semicolon","`;"),("' Quote","'"),
    (", Comma",","),     (". Period","."),
    ("/ Slash","/"),     ("\\ Backslash","\\"),
    ("` Backtick","``"),
]:
    _r(_d, _a)
for _d, _a in [
    ("Left Click","LButton"),   ("Right Click","RButton"),
    ("Middle Click","MButton"), ("Mouse Button 4","XButton1"),
    ("Mouse Button 5","XButton2"), ("Wheel Up","WheelUp"),
    ("Wheel Down","WheelDown"),
]:
    _r(_d, _a)

DISPLAY_KEYS  = [d for d, _ in _KEY_TABLE]
_TO_AHK       = {d: a for d, a in _KEY_TABLE}
STOP_KEY_LIST = [f"F{i}" for i in range(1, 13)] + ["Pause", "ScrollLock", "Insert"]
_MOD_PREFIX   = {
    "Ctrl":"^","LCtrl":"^","RCtrl":"^",
    "Shift":"+","LShift":"+","RShift":"+",
    "Alt":"!","LAlt":"!","RAlt":"!",
    "LWin":"#","RWin":"#",
}

def to_ahk(display: str) -> str:
    return _TO_AHK.get(display, display)

# -----------------------------------------------------------------------
#  KEYSYM / MOUSE  →  display name  (for Key Capture Mode)
# -----------------------------------------------------------------------

_KEYSYM_MAP: dict = {
    # letters
    **{c: c.upper() for c in "abcdefghijklmnopqrstuvwxyz"},
    # digits (top row)
    **{str(n): str(n) for n in range(10)},
    # function keys
    **{f"F{i}": f"F{i}" for i in range(1, 13)},
    # modifiers
    "Control_L":"Left Ctrl",  "Control_R":"Right Ctrl",
    "Shift_L":"Left Shift",   "Shift_R":"Right Shift",
    "Alt_L":"Left Alt",       "Alt_R":"Right Alt",
    "Super_L":"Left Win",     "Super_R":"Right Win",
    "Meta_L":"Left Win",      "Meta_R":"Right Win",
    # navigation
    "Return":"Enter",         "space":"Space",
    "Tab":"Tab",              "BackSpace":"Backspace",
    "Escape":"Escape",        "Delete":"Delete",
    "Insert":"Insert",        "Home":"Home",
    "End":"End",              "Prior":"Page Up",
    "Next":"Page Down",       "Up":"Up Arrow",
    "Down":"Down Arrow",      "Left":"Left Arrow",
    "Right":"Right Arrow",    "Caps_Lock":"Caps Lock",
    "Num_Lock":"Num Lock",    "Scroll_Lock":"Scroll Lock",
    "Print":"Print Screen",   "Pause":"Pause",
    # numpad
    "KP_0":"Numpad 0","KP_1":"Numpad 1","KP_2":"Numpad 2",
    "KP_3":"Numpad 3","KP_4":"Numpad 4","KP_5":"Numpad 5",
    "KP_6":"Numpad 6","KP_7":"Numpad 7","KP_8":"Numpad 8",
    "KP_9":"Numpad 9","KP_Insert":"Numpad 0","KP_End":"Numpad 1",
    "KP_Down":"Numpad 2","KP_Next":"Numpad 3","KP_Left":"Numpad 4",
    "KP_Begin":"Numpad 5","KP_Right":"Numpad 6","KP_Home":"Numpad 7",
    "KP_Up":"Numpad 8","KP_Prior":"Numpad 9",
    "KP_Enter":"Numpad Enter","KP_Add":"Numpad +",
    "KP_Subtract":"Numpad -","KP_Multiply":"Numpad *",
    "KP_Divide":"Numpad /","KP_Decimal":"Numpad .","KP_Delete":"Numpad .",
    # punctuation
    "minus":"- Minus",         "equal":"= Equals",
    "bracketleft":"[ Bracket", "bracketright":"] Bracket",
    "semicolon":"; Semicolon", "apostrophe":"' Quote",
    "comma":", Comma",         "period":". Period",
    "slash":"/ Slash",         "backslash":"\\ Backslash",
    "grave":"` Backtick",
}

# tkinter Button number → display name
_MOUSE_MAP = {
    1: "Left Click",
    2: "Middle Click",
    3: "Right Click",
    4: "Mouse Button 4",
    5: "Mouse Button 5",
}

def keysym_to_display(keysym: str) -> str | None:
    """Return display name for a tkinter keysym, or None if unknown."""
    return _KEYSYM_MAP.get(keysym)

def mouse_btn_to_display(btn_num: int, delta: int = 0) -> str | None:
    if delta > 0:
        return "Wheel Up"
    if delta < 0:
        return "Wheel Down"
    return _MOUSE_MAP.get(btn_num)

# -----------------------------------------------------------------------
#  CAPTURE STATE  (module-level singleton)
# -----------------------------------------------------------------------

class _CaptureState:
    """Tracks the one slot that is currently waiting for a key press."""
    active_slot = None   # reference to the KeySlot currently capturing

_CS = _CaptureState()

# -----------------------------------------------------------------------
#  AHK CODE BUILDERS
# -----------------------------------------------------------------------

def _send_token(ahk_key: str) -> str:
    mm = {
        "LButton":"{Click}",       "RButton":"{Click Right}",
        "MButton":"{Click Middle}","XButton1":"{Click X1}",
        "XButton2":"{Click X2}",   "WheelUp":"{WheelUp}",
        "WheelDown":"{WheelDown}",
    }
    if ahk_key in mm:
        return mm[ahk_key]
    if len(ahk_key) == 1:
        return ahk_key
    return "{" + ahk_key + "}"

def build_output_send(display_keys: list) -> str:
    ahk_keys = [to_ahk(k) for k in display_keys]
    mods     = [k for k in ahk_keys if k in _MOD_PREFIX]
    regs     = [k for k in ahk_keys if k not in _MOD_PREFIX]
    seen = set(); prefix = ""
    for m in mods:
        s = _MOD_PREFIX[m]
        if s not in seen:
            prefix += s; seen.add(s)
    if not regs:
        return "".join(_send_token(m) for m in mods)
    result = prefix + _send_token(regs[0])
    for k in regs[1:]:
        result += _send_token(k)
    return result

def build_input_trigger(display_keys: list) -> str:
    ahk_keys = [to_ahk(k) for k in display_keys]
    mods     = [k for k in ahk_keys if k in _MOD_PREFIX]
    regs     = [k for k in ahk_keys if k not in _MOD_PREFIX]
    seen = set(); prefix = ""
    for m in mods:
        s = _MOD_PREFIX[m]
        if s not in seen:
            prefix += s; seen.add(s)
    if regs:
        return prefix + regs[-1]
    elif mods:
        return prefix + mods[-1]
    return ""

# -----------------------------------------------------------------------
#  COLOURS
# -----------------------------------------------------------------------
_BG          = "#0b0d16"
_ROW_A       = "#141722"
_ROW_B       = "#191d2c"
_ACCENT      = "#4ab3ff"
_DIM         = "#3d4a5c"
_DIM2        = "#252f40"
_SLOT_ADD_FG = "#1a2d4a"
_SLOT_ADD_HV = "#132240"
_SLOT_DEL_FG = "#2a1818"
_SLOT_DEL_HV = "#1e1010"
_ROW_DEL_FG  = "#4a1616"
_ROW_DEL_HV  = "#3a1010"
_BTN_ADD_FG  = "#164a28"
_BTN_ADD_HV  = "#0f3a1e"
_BTN_CLR_FG  = "#2a2a3c"
_BTN_CLR_HV  = "#1e1e2c"
_BTN_PRV_FG  = "#1a3060"
_BTN_PRV_HV  = "#132450"
_BTN_SAV_FG  = "#3a1068"
_BTN_SAV_HV  = "#2c0c54"

# Capture-button colours
_CAP_IDLE_FG  = "#1a2a1a"   # dark green tint — idle
_CAP_IDLE_HV  = "#142214"
_CAP_WAIT_FG  = "#5a3a00"   # amber — waiting for press
_CAP_WAIT_HV  = "#5a3a00"
_CAP_ICON     = "⊙"         # icon shown in capture button

# -----------------------------------------------------------------------
#  KEY SLOT WIDGET
# -----------------------------------------------------------------------

class KeySlot(ctk.CTkFrame):
    """
    One key selector.
    • Normal mode  : shows a combobox dropdown.
    • Capture mode : shows a button; clicking it listens for the next
                     keyboard / mouse event and assigns it to this slot.
    """

    _COMBO_W = 138
    _BTN_W   = 138

    def __init__(self, master, default="A", on_remove=None,
                 capture_mode_var: ctk.BooleanVar = None, **kw):
        kw.setdefault("fg_color", "transparent")
        super().__init__(master, **kw)
        self._on_remove       = on_remove
        self._capture_mode_var = capture_mode_var
        self._listening        = False
        self._ignore_next_click = False

        self._var = ctk.StringVar(value=default)

        # ── combobox (normal mode) ────────────────────────────────
        self._dd = ctk.CTkComboBox(
            self, variable=self._var, values=DISPLAY_KEYS,
            width=self._COMBO_W, font=ctk.CTkFont(size=12),
            fg_color="#0d111e", border_color="#2a3550",
            button_color="#1e2d48", dropdown_fg_color="#111827",
        )
        self._dd.grid(row=0, column=0, padx=(0, 2))

        # ── capture button (capture mode) ─────────────────────────
        self._cap = ctk.CTkButton(
            self, text=self._short(default),
            width=self._BTN_W, height=28,
            font=ctk.CTkFont(size=12),
            fg_color=_CAP_IDLE_FG, hover_color=_CAP_IDLE_HV,
            text_color="#86efac", corner_radius=5,
            command=self._start_capture,
        )
        # trace var changes to keep button label in sync
        self._var.trace_add("write", self._sync_cap_label)

        # ── remove button ─────────────────────────────────────────
        self._rm = ctk.CTkButton(
            self, text="x", width=22, height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=_SLOT_DEL_FG, hover_color=_SLOT_DEL_HV,
            text_color="#f87171", corner_radius=5,
            command=lambda: self._on_remove and self._on_remove(self),
        )
        self._rm.grid(row=0, column=1, padx=(0, 2))

        # start in the correct mode
        if capture_mode_var:
            capture_mode_var.trace_add("write",
                lambda *_: self._apply_mode())
        self._apply_mode()

    # ── helpers ───────────────────────────────────────────────────

    @staticmethod
    def _short(text: str, max_len: int = 16) -> str:
        return text if len(text) <= max_len else text[:max_len - 1] + "…"

    def _sync_cap_label(self, *_):
        if not self._listening:
            self._cap.configure(text=self._short(self._var.get()))

    def _apply_mode(self):
        # Guard: widget may have been destroyed during a cluster rebuild
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        capture = self._capture_mode_var and self._capture_mode_var.get()
        if capture:
            self._dd.grid_remove()
            self._cap.grid(row=0, column=0, padx=(0, 2))
        else:
            if self._listening:
                self._cancel_capture()
            self._cap.grid_remove()
            self._dd.grid(row=0, column=0, padx=(0, 2))

    # ── capture logic ─────────────────────────────────────────────

    def _start_capture(self):
        # Cancel any other slot that is currently listening
        if _CS.active_slot and _CS.active_slot is not self:
            _CS.active_slot._cancel_capture()

        self._listening         = True
        self._ignore_next_click = True   # don't capture the click that activated us
        _CS.active_slot         = self
        self._cap.configure(
            text="[ Press any key... ]",
            fg_color=_CAP_WAIT_FG, hover_color=_CAP_WAIT_HV,
            text_color="#fbbf24",
        )
        root = self.winfo_toplevel()
        root.after(80, self._bind_capture_events)

    def _bind_capture_events(self):
        if not self._listening:
            return
        root = self.winfo_toplevel()
        # bind_all ensures we get events even from inside CTkScrollableFrame canvases
        root.bind_all("<KeyPress>",   self._on_key_event,   add="+")
        root.bind_all("<Button>",     self._on_mouse_event, add="+")
        root.bind_all("<MouseWheel>", self._on_wheel_event, add="+")

    def _unbind_capture_events(self):
        try:
            root = self.winfo_toplevel()
            root.unbind_all("<KeyPress>")
            root.unbind_all("<Button>")
            root.unbind_all("<MouseWheel>")
        except Exception:
            pass

    def _on_key_event(self, event):
        if not self._listening:
            return
        keysym = event.keysym
        if keysym == "Escape":
            self._cancel_capture()
            return
        display = keysym_to_display(keysym)
        if display:
            self._finish_capture(display)
        # else: unknown key, keep waiting

    def _on_mouse_event(self, event):
        if not self._listening:
            return
        # Ignore the click that opened capture mode
        if self._ignore_next_click:
            self._ignore_next_click = False
            return
        display = mouse_btn_to_display(event.num)
        if display:
            self._finish_capture(display)

    def _on_wheel_event(self, event):
        if not self._listening:
            return
        display = mouse_btn_to_display(0, event.delta)
        if display:
            self._finish_capture(display)

    def _finish_capture(self, display: str):
        self._var.set(display)
        self._listening  = False
        _CS.active_slot  = None
        self._unbind_capture_events()
        self._cap.configure(
            text=self._short(display),
            fg_color=_CAP_IDLE_FG, hover_color=_CAP_IDLE_HV,
            text_color="#86efac",
        )

    def _cancel_capture(self):
        self._listening  = False
        _CS.active_slot  = None
        self._unbind_capture_events()
        self._cap.configure(
            text=self._short(self._var.get()),
            fg_color=_CAP_IDLE_FG, hover_color=_CAP_IDLE_HV,
            text_color="#86efac",
        )

    # ── public API ────────────────────────────────────────────────

    def get(self) -> str:
        return self._var.get()

    def set_removable(self, yes: bool):
        if yes:
            self._rm.grid()
        else:
            self._rm.grid_remove()


# -----------------------------------------------------------------------
#  KEY CLUSTER
# -----------------------------------------------------------------------

class KeyCluster(ctk.CTkFrame):
    MAX_SLOTS = 5

    def __init__(self, master, default_key="A", label="",
                 capture_mode_var: ctk.BooleanVar = None, **kw):
        kw.setdefault("fg_color", "transparent")
        super().__init__(master, **kw)
        self._default          = default_key
        self._capture_mode_var = capture_mode_var
        self._slots: list      = []

        if label:
            ctk.CTkLabel(
                self, text=label, font=ctk.CTkFont(size=10), text_color=_DIM,
            ).grid(row=0, column=0, columnspan=99, sticky="w", padx=2, pady=(0, 2))
            self._row = 1
        else:
            self._row = 0

        self._slot_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._slot_frame.grid(row=self._row, column=0, sticky="w")

        self._add_btn = ctk.CTkButton(
            self, text="+", width=26, height=26,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=_SLOT_ADD_FG, hover_color=_SLOT_ADD_HV,
            text_color=_ACCENT, corner_radius=5,
            command=self._add_slot,
        )
        self._add_btn.grid(row=self._row, column=1, padx=(4, 0), sticky="w")

        self._rebuild_from([default_key])

    # ── slot management ───────────────────────────────────────────

    def _rebuild_from(self, vals: list):
        for w in self._slot_frame.winfo_children():
            w.destroy()
        self._slots.clear()

        for i, v in enumerate(vals):
            if i > 0:
                ctk.CTkLabel(
                    self._slot_frame, text="+",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color="#1e3050", width=14,
                ).grid(row=0, column=i * 2 - 1, padx=1)

            slot = KeySlot(
                self._slot_frame,
                default          = v,
                on_remove        = self._remove_slot,
                capture_mode_var = self._capture_mode_var,
            )
            slot.grid(row=0, column=i * 2)
            self._slots.append(slot)

        self._refresh_rm()
        self._add_btn.configure(
            state="disabled" if len(self._slots) >= self.MAX_SLOTS else "normal"
        )

    def _add_slot(self):
        if len(self._slots) >= self.MAX_SLOTS:
            return
        self._rebuild_from([s.get() for s in self._slots] + [self._default])

    def _remove_slot(self, slot):
        if len(self._slots) <= 1:
            return
        self._rebuild_from([s.get() for s in self._slots if s is not slot])

    def _refresh_rm(self):
        only = len(self._slots) == 1
        for s in self._slots:
            s.set_removable(not only)

    def get_keys(self) -> list:
        return [s.get() for s in self._slots]


# -----------------------------------------------------------------------
#  COMBO STEP  (one step inside a combo sequence)
# -----------------------------------------------------------------------

class ComboStep(ctk.CTkFrame):
    """
    One sequential step:  [S#]  [KeyCluster]  Hold: [__]ms  Gap: [__]ms  [^][v][x]
    Hold = how long to physically hold the key down (0 = instant tap)
    Gap  = delay AFTER this step before the next one fires
    """

    def __init__(self, master, index: int,
                 on_delete, on_move_up, on_move_down,
                 capture_mode_var=None, **kw):
        kw.setdefault("fg_color",      "#0e1520")
        kw.setdefault("corner_radius", 6)
        super().__init__(master, **kw)
        self._on_delete    = on_delete
        self._on_move_up   = on_move_up
        self._on_move_down = on_move_down
        self._build(index, capture_mode_var)

    def _build(self, index: int, cap_var):
        # step badge
        self._num = ctk.CTkLabel(
            self, text=f" S{index:02d}", width=32,
            font=ctk.CTkFont(family="Courier New", size=11, weight="bold"),
            text_color="#f59e0b",
        )
        self._num.grid(row=0, column=0, padx=(8, 4), pady=5, sticky="w")

        # key cluster (supports combos: e.g. Ctrl + a in one step)
        self._keys = KeyCluster(
            self, default_key="A", capture_mode_var=cap_var,
        )
        self._keys.grid(row=0, column=1, padx=(0, 8), pady=4, sticky="w")

        def _num_entry(var_val, w_px):
            v = ctk.StringVar(value=var_val)
            e = ctk.CTkEntry(
                self, textvariable=v, width=w_px, height=24,
                font=ctk.CTkFont(size=11),
                fg_color="#090d18", border_color=_DIM2,
            )
            return v, e

        def _lbl(txt):
            return ctk.CTkLabel(self, text=txt, font=ctk.CTkFont(size=11),
                                text_color=_DIM)

        _lbl("Hold:").grid(row=0, column=2, padx=(0, 2))
        self._hold, he = _num_entry("0", 46)
        he.grid(row=0, column=3, padx=(0, 1))
        _lbl("ms").grid(row=0, column=4, padx=(1, 8))

        _lbl("Gap:").grid(row=0, column=5, padx=(0, 2))
        self._gap, ge = _num_entry("80", 46)
        ge.grid(row=0, column=6, padx=(0, 1))
        _lbl("ms").grid(row=0, column=7, padx=(1, 10))

        def _mbtn(txt, cmd, col, fg, hv, tc):
            ctk.CTkButton(
                self, text=txt, width=24, height=24, corner_radius=4,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=fg, hover_color=hv, text_color=tc,
                command=cmd,
            ).grid(row=0, column=col, padx=2, pady=5)

        _mbtn("^",  self._on_move_up,   8,  "#1a2d4a","#0f1e38","#93c5fd")
        _mbtn("v",  self._on_move_down, 9,  "#1a2d4a","#0f1e38","#93c5fd")
        _mbtn("x",  self._on_delete,   10,  "#2a1818","#1e1010","#f87171")

    def set_number(self, n: int):
        self._num.configure(text=f" S{n:02d}")

    def get_data(self) -> dict:
        def _int(sv, default, lo, hi):
            try:
                return max(lo, min(int(sv.get()), hi))
            except ValueError:
                return default
        return {
            "keys": self._keys.get_keys(),
            "hold": _int(self._hold, 0,  0, 9999),
            "gap":  _int(self._gap,  80, 0, 9999),
        }


# -----------------------------------------------------------------------
#  COMBO SEQUENCE  (ordered list of ComboSteps)
# -----------------------------------------------------------------------

class ComboSequence(ctk.CTkFrame):
    """Vertical list of ComboStep widgets."""

    def __init__(self, master, capture_mode_var=None, **kw):
        kw.setdefault("fg_color",      "#0a0f1c")
        kw.setdefault("corner_radius", 8)
        super().__init__(master, **kw)
        self._cap_var  = capture_mode_var
        self._steps: list = []
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(7, 3))

        ctk.CTkLabel(
            hdr, text="  COMBO SEQUENCE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f59e0b",
        ).pack(side="left")

        ctk.CTkLabel(
            hdr,
            text="  Steps execute one after another when you press the Input key",
            font=ctk.CTkFont(size=10), text_color=_DIM,
        ).pack(side="left", padx=(4, 0))

        ctk.CTkButton(
            hdr, text="+ Add Step", width=88, height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1a2d4a", hover_color="#0f1e38",
            text_color="#93c5fd", corner_radius=5,
            command=self.add_step,
        ).pack(side="right")

        self._sf = ctk.CTkFrame(self, fg_color="transparent")
        self._sf.pack(fill="x", padx=10, pady=(0, 8))

        # seed with 2 steps
        self.add_step(default="Up Arrow")
        self.add_step(default="A")

    # ── step management ───────────────────────────────────────────

    def add_step(self, default: str = "A"):
        hold = [None]
        idx  = len(self._steps) + 1

        step = ComboStep(
            self._sf,
            index          = idx,
            on_delete      = lambda: self._del(hold[0]),
            on_move_up     = lambda: self._move(hold[0], -1),
            on_move_down   = lambda: self._move(hold[0], +1),
            capture_mode_var = self._cap_var,
        )
        hold[0] = step
        # override default key in the first slot
        step._keys._slots[0]._var.set(default)
        step.pack(fill="x", pady=2)
        self._steps.append(step)

    def _del(self, step):
        if len(self._steps) <= 1:
            return
        self._steps.remove(step)
        step.pack_forget()
        step.destroy()
        self._renumber()

    def _move(self, step, direction: int):
        idx = self._steps.index(step)
        ni  = idx + direction
        if ni < 0 or ni >= len(self._steps):
            return
        self._steps[idx], self._steps[ni] = self._steps[ni], self._steps[idx]
        for s in self._steps:
            s.pack_forget()
        for s in self._steps:
            s.pack(fill="x", pady=2)
        self._renumber()

    def _renumber(self):
        for i, s in enumerate(self._steps, 1):
            s.set_number(i)

    def get_steps(self) -> list:
        return [s.get_data() for s in self._steps]


# -----------------------------------------------------------------------
#  BIND ROW
# -----------------------------------------------------------------------

class BindRow(ctk.CTkFrame):

    def __init__(self, master, index: int, on_delete,
                 capture_mode_var: ctk.BooleanVar = None, **kw):
        bg = _ROW_A if index % 2 == 0 else _ROW_B
        kw.setdefault("fg_color",      bg)
        kw.setdefault("corner_radius", 8)
        super().__init__(master, **kw)
        self._on_delete        = on_delete
        self._capture_mode_var = capture_mode_var
        self._build(index)

    def _build(self, index: int):
        self.grid_columnconfigure(3, weight=1)

        # index
        self._idx = ctk.CTkLabel(
            self, text=f" {index:02d}", width=38,
            font=ctk.CTkFont(family="Courier New", size=14, weight="bold"),
            text_color=_ACCENT,
        )
        self._idx.grid(row=0, column=0, padx=(10, 4), pady=12, sticky="n")

        # input cluster
        self._in = KeyCluster(
            self, default_key="A", label="INPUT",
            capture_mode_var=self._capture_mode_var,
        )
        self._in.grid(row=0, column=1, padx=(6, 4), pady=(8, 12), sticky="nw")

        # arrow (hidden in combo mode)
        self._arrow = ctk.CTkLabel(
            self, text="->",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#1e3050",
        )
        self._arrow.grid(row=0, column=2, padx=6, pady=12, sticky="n")

        # output cluster (hidden in combo mode)
        self._out = KeyCluster(
            self, default_key="A", label="OUTPUT",
            capture_mode_var=self._capture_mode_var,
        )
        self._out.grid(row=0, column=3, padx=(4, 8), pady=(8, 12), sticky="nw")

        # separator
        ctk.CTkFrame(self, width=1, height=54, fg_color=_DIM2).grid(
            row=0, column=4, padx=8, pady=10, sticky="ns")

        # ── options panel ─────────────────────────────────────────
        opt = ctk.CTkFrame(self, fg_color="transparent")
        opt.grid(row=0, column=5, padx=(4, 8), pady=12, sticky="n")

        self._af_var    = ctk.BooleanVar(value=False)
        self._tg_var    = ctk.BooleanVar(value=False)
        self._combo_var = ctk.BooleanVar(value=False)

        ctk.CTkCheckBox(
            opt, text="Auto-Fire", variable=self._af_var,
            font=ctk.CTkFont(size=12),
            checkbox_width=16, checkbox_height=16,
            fg_color="#1a5c3a", hover_color="#145230",
            command=self._af_changed,
        ).pack(anchor="w", pady=(0, 2))

        delay_row = ctk.CTkFrame(opt, fg_color="transparent")
        delay_row.pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(delay_row, text="Delay:", font=ctk.CTkFont(size=11),
                     text_color=_DIM).pack(side="left")
        self._delay = ctk.StringVar(value="50")
        ctk.CTkEntry(delay_row, textvariable=self._delay,
                     width=52, height=24, font=ctk.CTkFont(size=11),
                     fg_color="#0d111e", border_color=_DIM2,
                     ).pack(side="left", padx=(4, 0))
        ctk.CTkLabel(delay_row, text="ms", font=ctk.CTkFont(size=11),
                     text_color=_DIM).pack(side="left", padx=(2, 0))

        ctk.CTkCheckBox(
            opt, text="Toggle hold/release", variable=self._tg_var,
            font=ctk.CTkFont(size=12),
            checkbox_width=16, checkbox_height=16,
            fg_color="#4a1580", hover_color="#380f66",
            command=self._tg_changed,
        ).pack(anchor="w", pady=(0, 4))

        # Combo Sequence checkbox — different colour (amber/orange)
        ctk.CTkCheckBox(
            opt, text="Combo Sequence", variable=self._combo_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            checkbox_width=16, checkbox_height=16,
            fg_color="#7a4500", hover_color="#5a3300",
            text_color="#fbbf24",
            command=self._combo_changed,
        ).pack(anchor="w")

        # delete
        ctk.CTkButton(
            self, text="X", width=30, height=30,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=_ROW_DEL_FG, hover_color=_ROW_DEL_HV,
            text_color="#f87171", corner_radius=6,
            command=self._on_delete,
        ).grid(row=0, column=6, padx=(4, 12), pady=12, sticky="n")

        # ── combo sequence panel (row 1, hidden by default) ───────
        self._combo_seq = ComboSequence(
            self, capture_mode_var=self._capture_mode_var,
        )
        # starts hidden
        self._combo_visible = False

    # ── option mutexes ────────────────────────────────────────────

    def _af_changed(self):
        if self._af_var.get():
            self._tg_var.set(False)
            self._combo_var.set(False)
            self._hide_combo()

    def _tg_changed(self):
        if self._tg_var.get():
            self._af_var.set(False)
            self._combo_var.set(False)
            self._hide_combo()

    def _combo_changed(self):
        if self._combo_var.get():
            self._af_var.set(False)
            self._tg_var.set(False)
            self._show_combo()
        else:
            self._hide_combo()

    def _show_combo(self):
        if self._combo_visible:
            return
        # Hide OUTPUT side
        self._arrow.grid_remove()
        self._out.grid_remove()
        # Show combo panel spanning full width under the input
        self._combo_seq.grid(
            row=1, column=0, columnspan=7,
            sticky="ew", padx=8, pady=(0, 8),
        )
        self._combo_visible = True

    def _hide_combo(self):
        if not self._combo_visible:
            return
        self._combo_seq.grid_remove()
        self._arrow.grid()
        self._out.grid()
        self._combo_visible = False

    # ── public ────────────────────────────────────────────────────

    def set_index(self, i: int):
        self._idx.configure(text=f" {i:02d}")

    def get_data(self) -> dict:
        try:
            delay = max(10, min(int(self._delay.get()), 9999))
        except ValueError:
            delay = 50
        return {
            "in_keys":  self._in.get_keys(),
            "out_keys": self._out.get_keys(),
            "autofire": self._af_var.get(),
            "toggle":   self._tg_var.get(),
            "delay":    delay,
            "is_combo": self._combo_var.get(),
            "combo_steps": self._combo_seq.get_steps() if self._combo_var.get() else [],
        }


# -----------------------------------------------------------------------
#  AHK CODE GENERATOR
# -----------------------------------------------------------------------

def generate_ahk(game: str, stop_key: str, rows_data: list) -> str:
    L = []
    w = L.append
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    w("; ================================================================")
    w(";  AutoHotkey v2 Script -- PC Gaming Macros")
    w(f";  Generated: {ts}")
    w("; ================================================================")
    w("")
    w("#Requires AutoHotkey v2.0")
    w("#SingleInstance Force")
    w("")
    w(f"; -- Emergency Stop: [{stop_key}]  ->  Suspend / resume all macros --")
    w(f"{stop_key}::Suspend()")
    w("")

    game = game.strip().replace('"', '`"')
    if game:
        w(f'; -- Active only while  "{game}"  is focused --')
        w(f'#HotIf WinActive("{game}")')
    else:
        w("; -- No window filter: macros are GLOBAL (all programs) --")
    w("")

    for i, d in enumerate(rows_data, 1):
        in_keys    = d["in_keys"]
        out_keys   = d["out_keys"]
        autofire   = d["autofire"]
        toggle     = d["toggle"]
        delay      = d["delay"]
        is_combo   = d.get("is_combo", False)
        combo_steps= d.get("combo_steps", [])

        trigger = build_input_trigger(in_keys)
        if not trigger:
            continue

        in_lbl = " + ".join(in_keys)

        # ── COMBO SEQUENCE ────────────────────────────────────────
        if is_combo and combo_steps:
            step_preview = " -> ".join(
                " + ".join(s["keys"]) for s in combo_steps
            )
            w(f"; Bind #{i:02d}:  [{in_lbl}]  ->  [COMBO: {step_preview}]")
            w(f"{trigger}::")
            w("{")
            for si, step in enumerate(combo_steps, 1):
                keys     = step["keys"]
                hold_ms  = step["hold"]
                gap_ms   = step["gap"]
                snd      = build_output_send(keys)
                k_label  = " + ".join(keys)
                mode_lbl = f"hold {hold_ms}ms" if hold_ms > 0 else "tap"

                w(f"    ; Step {si}: {k_label}  ({mode_lbl})")

                if hold_ms > 0:
                    # Physical hold: send key-down, sleep, send key-up
                    ahk_outs = [to_ahk(k) for k in keys]
                    non_mods = [k for k in ahk_outs if k not in _MOD_PREFIX]
                    mod_syms = "".join(
                        _MOD_PREFIX[k] for k in ahk_outs if k in _MOD_PREFIX
                    )
                    main_ahk = non_mods[0] if non_mods else ahk_outs[-1]
                    if mod_syms:
                        # Hold with modifiers: press mods, hold key, release
                        w(f'    Send("{mod_syms}{{{main_ahk} down}}")')
                        w(f"    Sleep({hold_ms})")
                        w(f'    Send("{mod_syms}{{{main_ahk} up}}")')
                    else:
                        w(f'    Send("{{{main_ahk} down}}")')
                        w(f"    Sleep({hold_ms})")
                        w(f'    Send("{{{main_ahk} up}}")')
                else:
                    # Instant tap
                    w(f'    Send("{snd}")')

                if gap_ms > 0 and si < len(combo_steps):
                    w(f"    Sleep({gap_ms})")

            w("}")
            w("")
            continue

        # ── NORMAL REMAP / AUTO-FIRE / TOGGLE ────────────────────
        snd = build_output_send(out_keys)
        if not snd:
            continue

        flags   = ("  [Auto-Fire]" if autofire else "") + ("  [Toggle]" if toggle else "")
        out_lbl = " + ".join(out_keys)
        w(f"; Bind #{i:02d}:  [{in_lbl}]  ->  [{out_lbl}]{flags}")

        if toggle:
            ahk_outs = [to_ahk(k) for k in out_keys]
            non_mods = [k for k in ahk_outs if k not in _MOD_PREFIX]
            main_ahk = non_mods[0] if non_mods else ahk_outs[-1]
            var      = f"_tog_{i}"
            w(f"{trigger}::")
            w("{")
            w(f"    static {var} := false")
            w(f"    {var} := !{var}")
            w(f"    if {var}")
            w(f'        Send("{{{main_ahk} down}}")')
            w( "    else")
            w(f'        Send("{{{main_ahk} up}}")')
            w("}")

        elif autofire:
            raw = trigger.lstrip("^+!#")
            w(f"{trigger}::")
            w("{")
            w(f'    while GetKeyState("{raw}", "P")')
            w( "    {")
            w(f'        Send("{snd}")')
            w(f"        Sleep({delay})")
            w( "    }")
            w("}")

        else:
            # Native hook-level remap when possible (works with DirectInput / games)
            ahk_outs  = [to_ahk(k) for k in out_keys]
            out_mods  = [k for k in ahk_outs if k in _MOD_PREFIX]
            out_regs  = [k for k in ahk_outs if k not in _MOD_PREFIX]
            _SEND_ONLY = {"WheelUp", "WheelDown"}
            use_native = (
                len(out_keys) == 1 and not out_mods and out_regs
                and out_regs[0] not in _SEND_ONLY
            )
            if use_native:
                w(f"{trigger}::{out_regs[0]}")
            else:
                w(f"{trigger}::")
                w("{")
                w(f'    Send("{snd}")')
                w("}")

        w("")

    if game:
        w("#HotIf  ; end game-specific section")
        w("")

    return "\n".join(L)


# -----------------------------------------------------------------------
#  AUTO-NAME HELPER
# -----------------------------------------------------------------------

def auto_filename(game: str, rows_data: list) -> str:
    """
    Build a filename from the actual keybind content so you can
    remember what the script does at a glance.

    Example:  D-to-LClick__E-to-RClick__F-to-MClick.ahk
    """
    import re

    # Short display names for common keys
    _SHORT = {
        "Left Click":     "LClick",
        "Right Click":    "RClick",
        "Middle Click":   "MClick",
        "Mouse Button 4": "MB4",
        "Mouse Button 5": "MB5",
        "Wheel Up":       "WheelUp",
        "Wheel Down":     "WheelDown",
        "Left Ctrl":      "LCtrl",
        "Right Ctrl":     "RCtrl",
        "Left Shift":     "LShift",
        "Right Shift":    "RShift",
        "Left Alt":       "LAlt",
        "Right Alt":      "RAlt",
        "Left Win":       "LWin",
        "Right Win":      "RWin",
        "Space":          "Space",
        "Enter":          "Enter",
        "Escape":         "Esc",
        "Backspace":      "Bksp",
        "Up Arrow":       "Up",
        "Down Arrow":     "Down",
        "Left Arrow":     "Left",
        "Right Arrow":    "Right",
    }

    def shorten(k: str) -> str:
        return _SHORT.get(k, k.replace(" ", ""))

    parts = []
    for d in rows_data[:5]:
        in_str = "+".join(shorten(k) for k in d["in_keys"])
        if d.get("is_combo"):
            steps = d.get("combo_steps", [])
            out_str = "Combo" + str(len(steps)) + "Steps"
        else:
            out_str = "+".join(shorten(k) for k in d["out_keys"])
        if in_str and out_str:
            parts.append(f"{in_str}-to-{out_str}")

    if parts:
        base = "__".join(parts)
    elif game.strip():
        slug = game.strip().replace(" ", "_")
        base = f"{slug}_macros"
    else:
        base = "GlobalMacros"

    # Sanitise: allow only word chars, hyphens, underscores, dots
    base = re.sub(r"[^\w\-.]", "_", base)
    # Trim if very long
    if len(base) > 80:
        base = base[:80]

    return base + ".ahk"


# -----------------------------------------------------------------------
#  MAIN APPLICATION
# -----------------------------------------------------------------------

class AHKGen(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("AHK v2 Script Generator -- PC Gaming Macros")
        self.geometry("1340x820")
        self.minsize(1080, 600)
        self.configure(fg_color=_BG)
        self._rows: list            = []
        self._capture_mode_var      = ctk.BooleanVar(value=False)
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── HEADER ───────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="#0d1020", corner_radius=0, height=52)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkLabel(
            header, text="AHK v2 Script Generator",
            font=ctk.CTkFont(family="Courier New", size=20, weight="bold"),
            text_color=_ACCENT,
        ).pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(
            header, text="PC Gaming Macro Builder",
            font=ctk.CTkFont(size=12), text_color=_DIM,
        ).pack(side="left", padx=4)

        # ── Key Capture Mode toggle (right side of header) ────────
        cap_frame = ctk.CTkFrame(header, fg_color="transparent")
        cap_frame.pack(side="right", padx=18, pady=8)

        ctk.CTkLabel(
            cap_frame, text="Key Capture Mode",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#fbbf24",
        ).pack(side="left", padx=(0, 8))

        self._cap_switch = ctk.CTkSwitch(
            cap_frame,
            text="",
            variable       = self._capture_mode_var,
            onvalue        = True,
            offvalue       = False,
            progress_color = "#d97706",
            button_color   = "#fbbf24",
            button_hover_color = "#f59e0b",
            width          = 46,
        )
        self._cap_switch.pack(side="left")

        self._cap_hint = ctk.CTkLabel(
            cap_frame,
            text="OFF — using dropdowns",
            font=ctk.CTkFont(size=11), text_color=_DIM,
            width=200, anchor="w",
        )
        self._cap_hint.pack(side="left", padx=(8, 0))

        self._capture_mode_var.trace_add("write", self._on_capture_toggle)

        # ── CONFIG BAR ───────────────────────────────────────────
        cfg = ctk.CTkFrame(self, fg_color="#0f1322", corner_radius=0, height=64)
        cfg.grid(row=1, column=0, sticky="ew", pady=(0, 2))
        cfg.grid_propagate(False)

        def clbl(parent, text, color):
            return ctk.CTkLabel(
                parent, text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=color,
            )

        # Game name
        clbl(cfg, "Game / Window Name:", "#7dd3fc").grid(
            row=0, column=0, padx=(16, 4), pady=18, sticky="e")
        self._game = ctk.CTkEntry(
            cfg, width=310, height=34,
            placeholder_text='e.g.  Elden Ring   (empty = all programs)',
            font=ctk.CTkFont(size=12),
            fg_color="#090d18", border_color=_DIM2,
        )
        self._game.grid(row=0, column=1, padx=(0, 10), pady=14)

        # Script name
        clbl(cfg, "Script Name:", "#a5f3fc").grid(
            row=0, column=2, padx=(6, 4), pady=18, sticky="e")
        self._script_name = ctk.CTkEntry(
            cfg, width=220, height=34,
            placeholder_text="auto-generated if empty",
            font=ctk.CTkFont(size=12),
            fg_color="#090d18", border_color=_DIM2,
        )
        self._script_name.grid(row=0, column=3, padx=(0, 10), pady=14)

        # Stop key
        clbl(cfg, "Emergency Stop:", "#fca5a5").grid(
            row=0, column=4, padx=(6, 4), pady=18, sticky="e")
        self._stop = ctk.CTkComboBox(
            cfg, values=STOP_KEY_LIST, width=100, height=34,
            font=ctk.CTkFont(size=12),
            fg_color="#090d18", border_color=_DIM2, button_color=_DIM2,
            dropdown_fg_color="#111827",
        )
        self._stop.set("F12")
        self._stop.grid(row=0, column=5, padx=(0, 4), pady=14)

        ctk.CTkLabel(
            cfg, text="Suspends / resumes all macros",
            font=ctk.CTkFont(size=11), text_color=_DIM,
        ).grid(row=0, column=6, padx=(0, 16), pady=18, sticky="w")

        # ── SCROLL AREA ──────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=_BG,
            scrollbar_button_color=_DIM2,
            scrollbar_button_hover_color="#2a3d58",
        )
        self._scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=0)
        self._scroll.grid_columnconfigure(0, weight=1)

        # ── FOOTER ───────────────────────────────────────────────
        foot = ctk.CTkFrame(self, fg_color="#0a0c18", corner_radius=0, height=60)
        foot.grid(row=3, column=0, sticky="ew")
        foot.grid_propagate(False)
        foot.grid_columnconfigure(4, weight=1)

        def fbtn(text, cmd, col, w_px, fg, hv, tc="#ffffff"):
            ctk.CTkButton(
                foot, text=text, command=cmd,
                width=w_px, height=40, fg_color=fg, hover_color=hv,
                font=ctk.CTkFont(size=13, weight="bold"), text_color=tc,
                corner_radius=8,
            ).grid(row=0, column=col, padx=(12, 4), pady=10, sticky="w")

        fbtn("+ Add Keybind",        self.add_row,    0, 155, _BTN_ADD_FG, _BTN_ADD_HV, "#86efac")
        fbtn("Clear All",            self._clear,     1, 120, _BTN_CLR_FG, _BTN_CLR_HV, "#94a3b8")
        fbtn("Preview Code",         self._preview,   5, 155, _BTN_PRV_FG, _BTN_PRV_HV, "#93c5fd")
        fbtn("Generate & Save .ahk", self._save,      6, 200, _BTN_SAV_FG, _BTN_SAV_HV, "#d8b4fe")

        self.add_row()
        self.add_row()

    # ── capture toggle callback ───────────────────────────────────

    def _on_capture_toggle(self, *_):
        on = self._capture_mode_var.get()
        if on:
            self._cap_hint.configure(
                text="ON  — click a slot to capture key",
                text_color="#fbbf24",
            )
        else:
            self._cap_hint.configure(
                text="OFF — using dropdowns",
                text_color=_DIM,
            )
            # Cancel any active capture
            if _CS.active_slot:
                _CS.active_slot._cancel_capture()

    # ── row management ────────────────────────────────────────────

    def add_row(self):
        idx  = len(self._rows) + 1
        hold = [None]

        def _del():
            r = hold[0]
            if len(self._rows) == 1:
                messagebox.showwarning("Cannot Delete", "You need at least one row.")
                return
            self._rows.remove(r)
            r.grid_forget()
            r.destroy()
            for i, row in enumerate(self._rows, 1):
                row.set_index(i)
                row.grid(row=i - 1, column=0, sticky="ew", padx=4, pady=3)

        row     = BindRow(
            self._scroll, idx, on_delete=_del,
            capture_mode_var=self._capture_mode_var,
        )
        hold[0] = row
        row.grid(row=idx - 1, column=0, sticky="ew", padx=4, pady=3)
        self._rows.append(row)

    def _clear(self):
        if not messagebox.askyesno("Clear All", "Remove all keybind rows?"):
            return
        for r in self._rows:
            r.grid_forget()
            r.destroy()
        self._rows.clear()
        self.add_row()

    # ── code generation ───────────────────────────────────────────

    def _collect(self) -> str:
        return generate_ahk(
            game      = self._game.get(),
            stop_key  = self._stop.get() or "F12",
            rows_data = [r.get_data() for r in self._rows],
        )

    def _preview(self):
        code = self._collect()
        win  = ctk.CTkToplevel(self)
        win.title("Preview -- Generated AHK v2 Code")
        win.geometry("900x660")
        win.configure(fg_color=_BG)
        win.grab_set()
        win.grid_rowconfigure(0, weight=1)
        win.grid_columnconfigure(0, weight=1)

        tb = ctk.CTkTextbox(
            win,
            font=ctk.CTkFont(family="Courier New", size=12),
            fg_color="#060810", text_color="#a3e635", wrap="none",
        )
        tb.grid(row=0, column=0, columnspan=3,
                sticky="nsew", padx=12, pady=(12, 4))
        tb.insert("end", code)
        tb.configure(state="disabled")

        copy_btn = ctk.CTkButton(
            win, text="Copy to Clipboard", width=180,
            fg_color=_BTN_PRV_FG, hover_color=_BTN_PRV_HV,
        )
        def _copy():
            win.clipboard_clear()
            win.clipboard_append(code)
            copy_btn.configure(text="Copied!")
            win.after(2000, lambda: copy_btn.configure(text="Copy to Clipboard"))
        copy_btn.configure(command=_copy)
        copy_btn.grid(row=1, column=0, padx=(12, 4), pady=(4, 12), sticky="w")

        ctk.CTkButton(
            win, text="Save .ahk", width=130,
            fg_color=_BTN_SAV_FG, hover_color=_BTN_SAV_HV,
            command=self._save,
        ).grid(row=1, column=1, padx=4, pady=(4, 12), sticky="w")

        ctk.CTkButton(
            win, text="Close", width=90,
            fg_color=_BTN_CLR_FG, hover_color=_BTN_CLR_HV,
            command=win.destroy,
        ).grid(row=1, column=2, padx=(4, 12), pady=(4, 12), sticky="e")

    def _save(self):
        rows_data = [r.get_data() for r in self._rows]
        code      = generate_ahk(
            game      = self._game.get(),
            stop_key  = self._stop.get() or "F12",
            rows_data = rows_data,
        )

        # Determine filename
        custom = self._script_name.get().strip()
        if custom:
            fname = custom if custom.endswith(".ahk") else custom + ".ahk"
        else:
            fname = auto_filename(self._game.get(), rows_data)

        # Ensure default save directory exists (best-effort)
        save_dir = DEFAULT_SAVE_DIR
        try:
            os.makedirs(save_dir, exist_ok=True)
        except OSError:
            save_dir = os.path.expanduser("~")   # fallback to home dir

        path = filedialog.asksaveasfilename(
            defaultextension = ".ahk",
            filetypes        = [("AutoHotkey Script", "*.ahk"), ("All Files", "*.*")],
            initialdir       = save_dir,
            initialfile      = fname,
            title            = "Save AHK v2 Script",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(code)
            messagebox.showinfo(
                "Saved",
                f"Script saved!\n\n{path}\n\n"
                f"Run it with AutoHotkey v2 installed.\n"
                f"Press  {self._stop.get()}  to suspend / resume.",
            )
        except OSError as e:
            messagebox.showerror("Save Failed", str(e))


# -----------------------------------------------------------------------
#  ENTRY POINT
# -----------------------------------------------------------------------

if __name__ == "__main__":
    AHKGen().mainloop()