import tkinter as tk
from tkinter import ttk, messagebox, font
from struct.Layout import Layout
from constants import *
from PackingHeuristics import PackingHeuristics
from struct.Corridor import Orientation
import math
import itertools

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        if self.tip: 
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.attributes("-topmost", True)
        lbl = tk.Label(tw, text=self.text, bg="#333", fg="#fff",
                       font=("Helvetica", 9), bd=0, padx=6, pady=3)
        lbl.pack()

    def hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.valid_layouts = []
        self.idx = 0

        self.bg = "#f5f6f8"
        self.panel = "#ffffff"
        self.soft_gray = "#e6e9ee"
        self.primary = "#0b76ff"    
        self.accent = "#ff6b6b"    
        self.room_palette = [
            "#90CAF9", "#A5D6A7", "#FFCC80", "#F48FB1", "#CE93D8", "#FFAB91",
            "#81D4FA", "#C5E1A5", "#FFF59D", "#B0BEC5", "#F8BBD0", "#B39DDB"
        ]
        default_font = ("San Francisco", 11) if "Darwin" in root.tk.call("tk", "windowingsystem") else ("Helvetica", 11)
        self.title_font = ("Helvetica", 14, "bold")
        self.root.geometry("1200x760")
        self.root.title("Smart Layout Planner")
        self.root.configure(bg=self.bg)

        self.plot_w_var = tk.StringVar(value="40")
        self.plot_h_var = tk.StringVar(value="25")
        self.status_var = tk.StringVar(
            master=root,
            value="Enter plot size and rooms, then click 'Generate layouts'."
        )

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Card.TFrame", background=self.panel, relief="flat")
        style.configure("TLabel", background=self.bg, font=default_font)
        style.configure("Small.TLabel", background=self.bg, font=(default_font[0], 10))
        style.configure("TButton", font=default_font, padding=6)
        style.configure("Accent.TButton", background=self.primary, foreground="white")
        style.configure("Header.TLabel", font=self.title_font, background=self.bg)

        top = ttk.Frame(root, style="Card.TFrame")
        top.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(12,6))
        ttk.Label(top, text="Smart Layout Planner", style="Header.TLabel").pack(side=tk.LEFT, padx=8)
        spacer = ttk.Frame(top); spacer.pack(side=tk.LEFT, expand=True)

        ctrl = ttk.Frame(root)
        ctrl.pack(side=tk.TOP, fill=tk.X, padx=12, pady=(0,8))

        ttk.Label(ctrl, text="Width").grid(row=0, column=0, sticky="w")
        w_ent = ttk.Entry(ctrl, textvariable=self.plot_w_var, width=6)
        w_ent.grid(row=0, column=1, padx=6)
        ToolTip(w_ent, "Plot width in units")

        ttk.Label(ctrl, text="Height").grid(row=0, column=2, sticky="w", padx=(10,0))
        h_ent = ttk.Entry(ctrl, textvariable=self.plot_h_var, width=6)
        h_ent.grid(row=0, column=3, padx=6)
        ToolTip(h_ent, "Plot height in units")

        gen_btn = ttk.Button(ctrl, text="Generate layouts", command=self.generate)
        gen_btn.grid(row=0, column=4, padx=(18,6))

        prev_btn = ttk.Button(ctrl, text="◀ Prev", command=self.prev)
        prev_btn.grid(row=0, column=5, padx=4)
        next_btn = ttk.Button(ctrl, text="Next ▶", command=self.next)
        next_btn.grid(row=0, column=6, padx=4)

        sample_btn = ttk.Button(ctrl, text="Load sample", command=self.on_sample)
        sample_btn.grid(row=0, column=7, padx=(14,0))

        main = ttk.Frame(root)
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        left_card = ttk.Frame(main, style="Card.TFrame")
        left_card.pack(side=tk.LEFT, fill=tk.Y, padx=(0,8), pady=6)
        left_card.configure(width=340)
        lbl = ttk.Label(left_card, text="Rooms (one per line: name width height)", font=(default_font[0], 11, "bold"))
        lbl.pack(anchor="w", padx=12, pady=(12,0))

        self.rooms_text = tk.Text(left_card, width=36, height=26, bd=0, relief="flat",
                                  font=("Courier New", 11), background="#fbfcfd")
        self.rooms_text.pack(padx=12, pady=10, fill=tk.BOTH, expand=True)
        self.rooms_text.insert("1.0", "R1 6 5\nR2 7 4\nR3 4 4\nR4 5 5\nR5 3 8\nR6 6 6\nR7 9 3\nR8 4 7\nR9 3 3\nR10 4.5 4\n")

        right_card = ttk.Frame(main, style="Card.TFrame")
        right_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=6)

        self.canvas = tk.Canvas(right_card, bg="#ffffff", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.canvas.bind("<Configure>", lambda e: self._on_resize())

        status = ttk.Frame(root)
        status.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0,12))
        self.status_label = ttk.Label(status, textvariable=self.status_var, style="Small.TLabel")
        self.status_label.pack(side=tk.LEFT)

        legend_frame = ttk.Frame(status)
        legend_frame.pack(side=tk.RIGHT)
        for i, c in enumerate(self.room_palette[:6]):
            box = tk.Canvas(legend_frame, width=16, height=12, bg=c, highlightthickness=0)
            box.pack(side=tk.LEFT, padx=4)

        self._last_canvas_size = (CANVAS_W, CANVAS_H)

    def _on_resize(self):
        if self.valid_layouts:
            self.draw_layout(self.valid_layouts[self.idx])

    def generate(self):
        try:
            plot_w = float(self.plot_w_var.get())
            plot_h = float(self.plot_h_var.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Plot width/height must be numbers.")
            return

        try:
            rooms = PackingHeuristics.parse_rooms(self.rooms_text.get("1.0", tk.END))
        except Exception as e:
            messagebox.showerror("Invalid rooms", str(e))
            return

        if not rooms:
            messagebox.showinfo("No rooms", "Please enter at least one room.")
            return

        self.valid_layouts = PackingHeuristics.generate_layouts(plot_w, plot_h, rooms)
        if not self.valid_layouts:
            self.canvas.delete("all")
            self.status_var.set("⚠️ No feasible layout found. Adjust plot or rooms.")
            return

        self.idx = 0
        self.update_layout()

    def prev(self):
        if self.valid_layouts:
            self.idx = (self.idx - 1) % len(self.valid_layouts)
            self.update_layout()

    def next(self):
        if self.valid_layouts:
            self.idx = (self.idx + 1) % len(self.valid_layouts)
            self.update_layout()

    def draw_layout(self, layout: Layout):
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        W, H = layout.plot_w, layout.plot_h

        pad = 24
        s = min((cw - 2 * pad) / (W if W else 1), (ch - 2 * pad) / (H if H else 1))
        x_off = (cw - W * s) / 2
        y_off = (ch - H * s) / 2

        def xy(x, y):
            return x_off + x * s, y_off + y * s

        grid_step = max(1, round(max(W, H) / 20))
        for gx in range(0, math.ceil(W) + 1, grid_step):
            x0, y0 = xy(gx, 0)
            x1, y1 = xy(gx, H)
            self.canvas.create_line(x0, y0, x1, y1, fill="#f1f3f6")
        for gy in range(0, math.ceil(H) + 1, grid_step):
            x0, y0 = xy(0, gy)
            x1, y1 = xy(W, gy)
            self.canvas.create_line(x0, y0, x1, y1, fill="#f1f3f6")

        x0, y0 = xy(0, 0)
        x1, y1 = xy(W, H)
        self.canvas.create_rectangle(x0, y0, x1, y1, outline="#d6d9df", width=3)

        c = layout.corridor
        cx0, cy0 = xy(c.x, c.y)
        cx1, cy1 = xy(c.x + c.width, c.y + c.height)
        self.canvas.create_rectangle(cx0, cy0, cx1, cy1, fill="#f5f8ff", outline="#cbdcff")

        for i, r in enumerate(layout.placed):
            color = self.room_palette[i % len(self.room_palette)]
            rx0, ry0 = xy(r.x, r.y)
            rx1, ry1 = xy(r.x + r.width, r.y + r.height)
            self.canvas.create_rectangle(rx0, ry0, rx1, ry1, fill=color, outline="#3b3b3b", width=1)
            cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2
            name = getattr(r, "name", f"R{i+1}")
            self.canvas.create_text(cx, cy, text=f"{name}\n{r.width:.1f}×{r.height:.1f}",
                                    font=("Helvetica", 9), fill="#222")
        self.canvas.create_text(cw - 12, ch - 12, anchor="se",
                                text=f"{layout.label} | {layout.placed_count} placed",
                                font=("Helvetica", 9), fill="#666")

    def update_layout(self):
        L = self.valid_layouts[self.idx]
        self.draw_layout(L)
        cap = AREA_FRACTION_LIMIT * L.plot_w * L.plot_h
        text = (f"Layout {self.idx+1}/{len(self.valid_layouts)} | {L.label} | "
                f"Placed: {L.placed_count} | Rooms area: {L.rooms_area:.1f} (cap {cap:.1f})")
        self.status_var.set(text)

    def on_sample(self):
        sample = """\
Lobby 8 6
OfficeA 5 4
OfficeB 5 4
Meeting 6 5
Storage 4 3
Pantry 4 4
Server 3 5
ToiletM 3 3
ToiletF 3 3
OfficeC 6 4
OfficeD 6 4
OfficeE 7 3
OfficeF 7 3
"""
        self.rooms_text.delete("1.0", tk.END)
        self.rooms_text.insert("1.0", sample)
        self.plot_w_var.set("42")
        self.plot_h_var.set("28")