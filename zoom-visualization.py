"""
zoom.py — Image Zoom Visualization Tool

Usage: python zoom.py [image_path]

New in v2:
- Coordinate input box: type X, Y (original-image pixels) to position the source box
- Mouse click updates the coordinate display in real time
- Multiple connection-line styles: solid / dashed / dotted / dash-dot / arrow / double
"""

import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
import sys, os, math
from PIL import Image, ImageDraw, ImageTk

# ── constants ────────────────────────────────────────────────────────────────
DEFAULT_BOX_W  = 100
DEFAULT_BOX_H  = 100
DEFAULT_ZOOM   = 4
LINE_COLORS    = ["#FF3B30", "#FF9500", "#FFCC00", "#34C759",
                  "#007AFF", "#AF52DE", "#FFFFFF", "#000000"]
LINE_WIDTHS    = [2, 3, 4, 5, 6, 7, 8, 12, 15]
CORNER_OPTIONS = ["左上 (TL)", "左下 (BL)", "右上 (TR)", "右下 (BR)"]
CORNER_KEYS    = ["TL", "BL", "TR", "BR"]
PAD            = 12

LINE_STYLES = [
    ("实线",     "solid"),
    ("虚线",     "dashed"),
    ("点线",     "dotted"),
    ("点划线",   "dash_dot"),
    ("箭头",     "arrow"),
    ("双线",     "double"),
]

# ── drawing helpers ───────────────────────────────────────────────────────────
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _draw_styled_line(draw, p1, p2, color, width, style):
    """Draw a line between p1 and p2 with the given style on a PIL ImageDraw."""
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0:
        return

    if style == "solid":
        draw.line([p1, p2], fill=color, width=width)

    elif style == "dashed":
        seg, gap = max(12, width * 5), max(6, width * 3)
        _dash_line(draw, x1, y1, x2, y2, color, width, seg, gap, dot=False)

    elif style == "dotted":
        seg, gap = max(2, width), max(5, width * 3)
        _dash_line(draw, x1, y1, x2, y2, color, width, seg, gap, dot=True)

    elif style == "dash_dot":
        # long dash – short dot – long dash …
        seg, gap = max(14, width * 6), max(5, width * 2)
        dot_len = max(2, width)
        _dash_dot_line(draw, x1, y1, x2, y2, color, width, seg, gap, dot_len)

    elif style == "arrow":
        draw.line([p1, p2], fill=color, width=width)
        _draw_arrowhead(draw, p1, p2, color, width)
        _draw_arrowhead(draw, p2, p1, color, width)

    elif style == "double":
        offset = max(3, width + 2)
        ux, uy = (-dy / length) * offset / 2, (dx / length) * offset / 2
        a1 = (x1 + ux, y1 + uy)
        a2 = (x2 + ux, y2 + uy)
        b1 = (x1 - ux, y1 - uy)
        b2 = (x2 - ux, y2 - uy)
        lw = max(1, width - 1)
        draw.line([a1, a2], fill=color, width=lw)
        draw.line([b1, b2], fill=color, width=lw)

    else:
        draw.line([p1, p2], fill=color, width=width)


def _dash_line(draw, x1, y1, x2, y2, color, width, seg_len, gap_len, dot=False):
    dx, dy = x2 - x1, y2 - y1
    total  = math.hypot(dx, dy)
    if total == 0:
        return
    ux, uy = dx / total, dy / total
    pos = 0.0
    drawing = True
    while pos < total:
        end = min(pos + (seg_len if (not dot or drawing) else gap_len), total)
        if drawing:
            sx, sy = x1 + ux * pos,  y1 + uy * pos
            ex, ey = x1 + ux * end,  y1 + uy * end
            draw.line([(sx, sy), (ex, ey)], fill=color, width=width)
        pos = end
        drawing = not drawing


def _dash_dot_line(draw, x1, y1, x2, y2, color, width, seg, gap, dot_len):
    dx, dy = x2 - x1, y2 - y1
    total  = math.hypot(dx, dy)
    if total == 0:
        return
    ux, uy = dx / total, dy / total
    pos    = 0.0
    phase  = 0   # 0=dash, 1=gap, 2=dot, 3=gap
    lens   = [seg, gap, dot_len, gap]
    while pos < total:
        l   = lens[phase % 4]
        end = min(pos + l, total)
        if phase % 2 == 0:  # draw phases
            sx, sy = x1 + ux * pos, y1 + uy * pos
            ex, ey = x1 + ux * end, y1 + uy * end
            draw.line([(sx, sy), (ex, ey)], fill=color, width=width)
        pos  += l
        phase += 1


def _draw_arrowhead(draw, tip_far, tip, color, width):
    """Draw an arrowhead at `tip` pointing from `tip_far`."""
    dx, dy = tip[0] - tip_far[0], tip[1] - tip_far[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy  = dx / length, dy / length
    size    = max(10, width * 5)
    spread  = 0.4
    bx      = tip[0] - ux * size
    by      = tip[1] - uy * size
    lx      = bx - uy * size * spread
    ly      = by + ux * size * spread
    rx      = bx + uy * size * spread
    ry      = by - ux * size * spread
    draw.polygon([tip, (lx, ly), (rx, ry)], fill=color)


# ── main app ──────────────────────────────────────────────────────────────────
class ZoomApp(tk.Tk):
    def __init__(self, initial_path=None):
        super().__init__()
        self.title("Zoom Visualization Tool")
        self.resizable(True, True)
        self.configure(bg="#1C1C1E")

        self.orig_image  = None
        self.disp_image  = None
        self.disp_tk     = None
        self.scale       = 1.0
        self.offset_x    = 0
        self.offset_y    = 0
        self.src_box     = None   # (x, y, w, h) in *display* coords

        self.zoom_corner = tk.StringVar(value="BL")
        self.line_color  = "#FF3B30"
        self.line_width  = tk.IntVar(value=8)
        self.line_style  = tk.StringVar(value="dash_dot")
        self.box_w       = tk.IntVar(value=DEFAULT_BOX_W)
        self.box_h       = tk.IntVar(value=DEFAULT_BOX_H)
        self.zoom_factor = tk.IntVar(value=DEFAULT_ZOOM)

        # coordinate entry vars (in original-image pixels)
        self.coord_x = tk.StringVar(value="0")
        self.coord_y = tk.StringVar(value="0")

        self._build_ui()

        if initial_path and os.path.isfile(initial_path):
            self._load(initial_path)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):

        def btn(parent, text, cmd, bg="#3A3A3C", fg="#FFFFFF", **kw):
            kw.setdefault("activebackground", "#48484A")
            kw.setdefault("activeforeground", "#FFFFFF")
            b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                          relief=tk.FLAT, padx=9, pady=4, cursor="hand2", **kw)
            b.pack(side=tk.LEFT, padx=3)
            return b

        def lbl(parent, text):
            tk.Label(parent, text=text, bg="#2C2C2E", fg="#AEAEB2").pack(side=tk.LEFT, padx=(6, 1))

        # ── bar 1: load / box size / zoom factor ─────────────────────────────
        bar1 = tk.Frame(self, bg="#2C2C2E", pady=5)
        bar1.pack(fill=tk.X)

        btn(bar1, "📂 加载图片", self._open_file)

        lbl(bar1, "源框 宽:")
        tk.Spinbox(bar1, from_=10, to=2000, textvariable=self.box_w, width=5,
                   bg="#3A3A3C", fg="white", insertbackground="white",
                   command=self._redraw).pack(side=tk.LEFT, padx=1)
        lbl(bar1, "高:")
        tk.Spinbox(bar1, from_=10, to=2000, textvariable=self.box_h, width=5,
                   bg="#3A3A3C", fg="white", insertbackground="white",
                   command=self._redraw).pack(side=tk.LEFT, padx=1)

        lbl(bar1, "放大倍数:")
        tk.Spinbox(bar1, from_=2, to=16, textvariable=self.zoom_factor, width=4,
                   bg="#3A3A3C", fg="white", insertbackground="white",
                   command=self._redraw).pack(side=tk.LEFT, padx=1)

        # ── coordinate input ─────────────────────────────────────────────────
        tk.Frame(bar1, width=20, bg="#2C2C2E").pack(side=tk.LEFT)
        tk.Label(bar1, text="│", bg="#2C2C2E", fg="#48484A").pack(side=tk.LEFT)

        lbl(bar1, "左上角 X:")
        self._ex = tk.Entry(bar1, textvariable=self.coord_x, width=6,
                            bg="#3A3A3C", fg="white", insertbackground="white",
                            relief=tk.FLAT)
        self._ex.pack(side=tk.LEFT, padx=1)
        self._ex.bind("<Return>",    self._apply_coords)
        self._ex.bind("<FocusOut>",  self._apply_coords)

        lbl(bar1, "Y:")
        self._ey = tk.Entry(bar1, textvariable=self.coord_y, width=6,
                            bg="#3A3A3C", fg="white", insertbackground="white",
                            relief=tk.FLAT)
        self._ey.pack(side=tk.LEFT, padx=1)
        self._ey.bind("<Return>",    self._apply_coords)
        self._ey.bind("<FocusOut>",  self._apply_coords)

        btn(bar1, "✔ 定位", self._apply_coords)

        lbl(bar1, "（原图像素坐标）")

        # ── bar 2: corner + line width + color ───────────────────────────────
        bar2 = tk.Frame(self, bg="#2C2C2E", pady=5)
        bar2.pack(fill=tk.X)

        lbl(bar2, "放大框位置:")
        for label, key in zip(CORNER_OPTIONS, CORNER_KEYS):
            tk.Radiobutton(bar2, text=label, variable=self.zoom_corner,
                           value=key, command=self._redraw,
                           bg="#2C2C2E", fg="#FFF", selectcolor="#007AFF",
                           activebackground="#2C2C2E", activeforeground="#FFF"
                           ).pack(side=tk.LEFT, padx=3)

        lbl(bar2, " 线宽:")
        for w in LINE_WIDTHS:
            tk.Radiobutton(bar2, text=str(w), variable=self.line_width, value=w,
                           command=self._redraw,
                           bg="#2C2C2E", fg="#FFF", selectcolor="#007AFF",
                           activebackground="#2C2C2E", activeforeground="#FFF"
                           ).pack(side=tk.LEFT, padx=2)

        lbl(bar2, " 线色:")
        for c in LINE_COLORS:
            sw = tk.Frame(bar2, bg=c, width=18, height=18, cursor="hand2",
                          relief=tk.RAISED, bd=1)
            sw.pack(side=tk.LEFT, padx=2)
            sw.bind("<Button-1>", lambda e, col=c: self._set_color(col))

        btn(bar2, "🎨 自定义", self._pick_color)

        btn(bar2, "💾 保存 PNG", self._save_png,
            bg="#0A84FF", activebackground="#0060D0")

        # ── bar 3: line style ─────────────────────────────────────────────────
        bar3 = tk.Frame(self, bg="#2C2C2E", pady=5)
        bar3.pack(fill=tk.X)

        lbl(bar3, "连接线样式:")
        for label, key in LINE_STYLES:
            tk.Radiobutton(bar3, text=label, variable=self.line_style,
                           value=key, command=self._redraw,
                           bg="#2C2C2E", fg="#FFF", selectcolor="#34C759",
                           activebackground="#2C2C2E", activeforeground="#FFF"
                           ).pack(side=tk.LEFT, padx=5)

        # ── canvas ────────────────────────────────────────────────────────────
        self.canvas = tk.Canvas(self, bg="#000", cursor="crosshair",
                                highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>",  self._on_click)

        # ── status ────────────────────────────────────────────────────────────
        self.status = tk.Label(self,
            text="请加载一张图片，然后用鼠标点击或输入坐标来放置放大框。",
            bg="#1C1C1E", fg="#AEAEB2", anchor=tk.W, padx=8)
        self.status.pack(fill=tk.X)

    # ── file ops ──────────────────────────────────────────────────────────────
    def _open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"),
                       ("All files", "*.*")])
        if path:
            self._load(path)

    def _load(self, path):
        try:
            self.orig_image = Image.open(path).convert("RGBA")
            self.src_box    = None
            self.status.config(
                text=f"已加载: {os.path.basename(path)}  "
                     f"({self.orig_image.width}×{self.orig_image.height})  "
                     f"— 点击画布或输入坐标放置放大框")
            self._fit_image()
        except Exception as e:
            messagebox.showerror("加载失败", str(e))

    # ── fit / resize ──────────────────────────────────────────────────────────
    def _fit_image(self):
        if not self.orig_image:
            return
        cw = self.canvas.winfo_width()  or 900
        ch = self.canvas.winfo_height() or 600
        iw, ih = self.orig_image.size
        scale = min(cw / iw, ch / ih, 1.0)
        nw, nh = int(iw * scale), int(ih * scale)
        self.disp_image = self.orig_image.resize((nw, nh), Image.LANCZOS)
        self.scale      = scale
        self.offset_x   = (cw - nw) // 2
        self.offset_y   = (ch - nh) // 2
        self._redraw()

    def _on_resize(self, _):
        self._fit_image()

    # ── interaction ───────────────────────────────────────────────────────────
    def _on_click(self, event):
        if not self.disp_image:
            return
        # canvas → display-image coords
        x = event.x - self.offset_x
        y = event.y - self.offset_y
        dw, dh = self.disp_image.size
        if not (0 <= x < dw and 0 <= y < dh):
            return
        bw = int(self.box_w.get() * self.scale)
        bh = int(self.box_h.get() * self.scale)
        x  = clamp(x, 0, dw - bw)
        y  = clamp(y, 0, dh - bh)
        self.src_box = (x, y, bw, bh)
        # update coordinate display (original image pixels)
        ox = round(x / self.scale)
        oy = round(y / self.scale)
        self.coord_x.set(str(ox))
        self.coord_y.set(str(oy))
        self._redraw()

    def _apply_coords(self, _event=None):
        """Position source box from the entry fields (original-image pixels)."""
        if not self.disp_image or not self.orig_image:
            return
        try:
            ox = int(self.coord_x.get())
            oy = int(self.coord_y.get())
        except ValueError:
            messagebox.showwarning("坐标错误", "请输入整数坐标值。")
            return
        ow, oh = self.orig_image.size
        ox = clamp(ox, 0, ow - 1)
        oy = clamp(oy, 0, oh - 1)
        # convert to display coords
        bw = int(self.box_w.get() * self.scale)
        bh = int(self.box_h.get() * self.scale)
        dw, dh = self.disp_image.size
        dx = clamp(int(ox * self.scale), 0, dw - bw)
        dy = clamp(int(oy * self.scale), 0, dh - bh)
        self.src_box = (dx, dy, bw, bh)
        # refresh coord labels in case clamping changed them
        self.coord_x.set(str(round(dx / self.scale)))
        self.coord_y.set(str(round(dy / self.scale)))
        self._redraw()

    # ── rendering ─────────────────────────────────────────────────────────────
    def _redraw(self):
        if not self.disp_image:
            return
        cw = self.canvas.winfo_width()  or 900
        ch = self.canvas.winfo_height() or 600
        out = Image.new("RGBA", (cw, ch), (0, 0, 0, 255))
        out.paste(self.disp_image, (self.offset_x, self.offset_y))
        draw = ImageDraw.Draw(out)

        if self.src_box:
            sx, sy, sw, sh = self.src_box
            ax, ay = sx + self.offset_x, sy + self.offset_y
            lw     = self.line_width.get()
            col    = self.line_color
            style  = self.line_style.get()
            zf     = self.zoom_factor.get()
            zoom_w = sw * zf
            zoom_h = sh * zf
            corner = self.zoom_corner.get()
            dw, dh = self.disp_image.size

            # zoomed-box position
            if corner == "TL":
                zx, zy = self.offset_x + PAD, self.offset_y + PAD
            elif corner == "TR":
                zx, zy = self.offset_x + dw - zoom_w - PAD, self.offset_y + PAD
            elif corner == "BL":
                zx, zy = self.offset_x + PAD, self.offset_y + dh - zoom_h - PAD
            else:
                zx, zy = self.offset_x + dw - zoom_w - PAD, self.offset_y + dh - zoom_h - PAD

            # paste zoomed crop
            crop   = self.disp_image.crop((sx, sy, sx + sw, sy + sh))
            zoomed = crop.resize((int(zoom_w), int(zoom_h)), Image.NEAREST)
            out.paste(zoomed, (int(zx), int(zy)))

            # rectangles
            draw.rectangle([ax, ay, ax + sw, ay + sh], outline=col, width=lw)
            draw.rectangle([int(zx), int(zy),
                            int(zx + zoom_w), int(zy + zoom_h)],
                           outline=col, width=lw)

            # connection corners
            if corner in ("TL", "BR"):
                p1a = (ax + sw,        ay)
                p1b = (int(zx + zoom_w), int(zy))
                p2a = (ax,             ay + sh)
                p2b = (int(zx),        int(zy + zoom_h))
            else:
                p1a = (ax,             ay)
                p1b = (int(zx),        int(zy))
                p2a = (ax + sw,        ay + sh)
                p2b = (int(zx + zoom_w), int(zy + zoom_h))

            _draw_styled_line(draw, p1a, p1b, col, lw, style)
            _draw_styled_line(draw, p2a, p2b, col, lw, style)

        self.disp_tk = ImageTk.PhotoImage(out)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.disp_tk)

    # ── color ─────────────────────────────────────────────────────────────────
    def _set_color(self, col):
        self.line_color = col
        self._redraw()

    def _pick_color(self):
        result = colorchooser.askcolor(color=self.line_color, title="选择线条颜色")
        if result and result[1]:
            self.line_color = result[1]
            self._redraw()

    # ── save ──────────────────────────────────────────────────────────────────
    def _save_png(self):
        if not self.disp_image:
            messagebox.showwarning("提示", "请先加载一张图片。")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("All files", "*.*")],
            initialfile="zoom_result.png")
        if not path:
            return
        self._render_hires(path)
        messagebox.showinfo("保存成功", f"已保存到:\n{path}")

    def _render_hires(self, path):
        """Re-render at original resolution."""
        ow, oh = self.orig_image.size
        out    = self.orig_image.copy().convert("RGBA")
        draw   = ImageDraw.Draw(out)

        if self.src_box:
            inv  = 1.0 / self.scale
            sx_d, sy_d, sw_d, sh_d = self.src_box
            sx   = int(sx_d * inv)
            sy   = int(sy_d * inv)
            sw   = clamp(int(sw_d * inv), 1, ow - sx)
            sh   = clamp(int(sh_d * inv), 1, oh - sy)
            lw   = self.line_width.get()
            col  = self.line_color
            style = self.line_style.get()
            zf   = self.zoom_factor.get()
            zoom_w, zoom_h = sw * zf, sh * zf
            corner = self.zoom_corner.get()

            if corner == "TL":
                zx, zy = PAD, PAD
            elif corner == "TR":
                zx, zy = ow - zoom_w - PAD, PAD
            elif corner == "BL":
                zx, zy = PAD, oh - zoom_h - PAD
            else:
                zx, zy = ow - zoom_w - PAD, oh - zoom_h - PAD

            crop   = self.orig_image.crop((sx, sy, sx + sw, sy + sh))
            zoomed = crop.resize((int(zoom_w), int(zoom_h)), Image.NEAREST)
            out.paste(zoomed, (int(zx), int(zy)))

            draw.rectangle([sx, sy, sx + sw, sy + sh], outline=col, width=lw)
            draw.rectangle([int(zx), int(zy),
                            int(zx + zoom_w), int(zy + zoom_h)],
                           outline=col, width=lw)

            if corner in ("TL", "BR"):
                p1a = (sx + sw,        sy)
                p1b = (int(zx + zoom_w), int(zy))
                p2a = (sx,             sy + sh)
                p2b = (int(zx),        int(zy + zoom_h))
            else:
                p1a = (sx,             sy)
                p1b = (int(zx),        int(zy))
                p2a = (sx + sw,        sy + sh)
                p2b = (int(zx + zoom_w), int(zy + zoom_h))

            _draw_styled_line(draw, p1a, p1b, col, lw, style)
            _draw_styled_line(draw, p2a, p2b, col, lw, style)

        out.convert("RGB").save(path, "PNG")


# ── entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    img_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = ZoomApp(initial_path=img_path)
    app.geometry("1200x760")
    app.mainloop()