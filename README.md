# 🔍 zoom.py — Image Zoom Visualization Tool

A lightweight desktop tool for creating **zoom-in annotation boxes** on images — useful for academic figures, paper illustrations, technical reports, or any scenario where you want to highlight and magnify a region of interest.

Built with Python + Tkinter + Pillow. No heavy dependencies, runs anywhere Python does.

---

## ✨ Features

- **Click to place** a source rectangle on any loaded image
- **Coordinate input** — type exact X/Y pixel coordinates to position the box precisely, or read back the coordinates after a mouse click
- **Adjustable source box** size (width × height in original-image pixels)
- **Zoom factor** from 2× to 16×
- **Snap-to-corner** for the zoomed view — top-left, top-right, bottom-left, or bottom-right
- **Smart connection lines** linking the two rectangles at matching corners, with 6 styles:
  - Solid / Dashed / Dotted / Dash-dot / Arrow (double-headed) / Double line
- **Line color** — 8 presets + full custom color picker
- **Line width** — 1 to 6 px
- **Save to PNG** — re-renders at the original image resolution (lossless output)

---

## 🖥️ Screenshot

<img src=".\Imgs\app.png">

---

## 🎁 Result

<img src=".\Imgs\img.png">

---

## 🚀 Quick Start

**1. Install dependencies**

```bash
pip install Pillow
```

> `tkinter` is included in the Python standard library. On some Linux distros you may need:
> ```bash
> sudo apt install python3-tk
> ```

**2. Run**

```bash
# Open with file dialog
python zoom.py

# Or pass an image directly
python zoom.py path/to/image.png
```

---

## 🎮 Usage

| Action | How |
|--------|-----|
| Load image | Click **📂 加载图片** or pass path as argument |
| Place zoom box | **Left-click** anywhere on the image |
| Precise positioning | Type X, Y in the coordinate fields → press **Enter** or click **✔ 定位** |
| Read back position | Coordinates update automatically after every click |
| Resize source box | Adjust **宽 (width)** and **高 (height)** spinboxes |
| Change magnification | Adjust **放大倍数** spinbox |
| Move zoomed view | Select a corner with the **放大框位置** radio buttons |
| Change line style | Select from the **连接线样式** radio buttons |
| Change line color | Click a preset swatch or **🎨 自定义** |
| Save result | Click **💾 保存 PNG** |

### Connection line logic

The two rectangles are always linked at geometrically sensible corners:

- Zoomed view at **TL or BR** → lines connect the **top-right** corners and the **bottom-left** corners
- Zoomed view at **TR or BL** → lines connect the **top-left** corners and the **bottom-right** corners

---

## 📦 Requirements

| Package | Version |
|---------|---------|
| Python  | ≥ 3.8   |
| Pillow  | ≥ 9.0   |
| tkinter | stdlib  |

---

## 📄 License

MIT — free to use, modify, and redistribute.
