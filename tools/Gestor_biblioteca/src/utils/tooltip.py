import sys
import tkinter as tk
from tkinter import ttk, font


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _show(self, event):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(tw, text=self.text, background="#ffffcc", foreground="black", relief="solid", borderwidth=1)
        label.pack()

    def _hide(self, event):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


_EMOJI_STYLE = None


def _init_emoji_style():
    global _EMOJI_STYLE
    if _EMOJI_STYLE is not None:
        return
    candidates = []
    if sys.platform == "win32":
        candidates = ["Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"]
    elif sys.platform == "darwin":
        candidates = ["Apple Color Emoji"]
    else:
        candidates = ["Noto Color Emoji"]
    available = font.families()
    for name in candidates:
        if name in available:
            s = ttk.Style()
            s.configure("Emoji.TButton", font=font.Font(family=name, size=12))
            _EMOJI_STYLE = "Emoji.TButton"
            return
    _EMOJI_STYLE = False


def make_btn(parent, icon, command, tooltip_text):
    _init_emoji_style()
    kwargs = {"text": icon, "command": command, "width": 3}
    if _EMOJI_STYLE:
        kwargs["style"] = _EMOJI_STYLE
    btn = ttk.Button(parent, **kwargs)
    btn.pack(side="left", padx=1)
    ToolTip(btn, tooltip_text)
    return btn
