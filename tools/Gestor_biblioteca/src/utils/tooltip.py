import tkinter as tk
from tkinter import ttk


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


def make_btn(parent, icon, command, tooltip_text):
    btn = ttk.Button(parent, text=icon, command=command, width=3)
    btn.pack(side="left", padx=1)
    ToolTip(btn, tooltip_text)
    return btn
