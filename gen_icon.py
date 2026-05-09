"""生成光谱仪测试程序图标"""

from PIL import Image, ImageDraw, ImageFont
import math
import os

SIZE = 256

img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 圆角矩形背景
def rounded_rect(draw, xy, radius, fill, outline=None, width=0):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

rounded_rect(draw, (4, 4, 252, 252), radius=40, fill=(26, 115, 232))

# 内部白色区域
rounded_rect(draw, (16, 16, 240, 240), radius=30, fill=(255, 255, 255))

# 绘制光谱曲线
cx, cy = 128, 140
chart_w, chart_h = 170, 90
chart_left = cx - chart_w // 2
chart_top = cy - chart_h // 2

# 坐标轴
axis_color = (180, 185, 195)
draw.line([(chart_left, chart_top + chart_h), (chart_left + chart_w, chart_top + chart_h)],
          fill=axis_color, width=2)
draw.line([(chart_left, chart_top), (chart_left, chart_top + chart_h)],
          fill=axis_color, width=2)

# 网格线
for i in range(1, 4):
    y = chart_top + chart_h - int(chart_h * i / 3)
    draw.line([(chart_left, y), (chart_left + chart_w, y)],
              fill=(230, 234, 237), width=1)

# 光谱曲线 - 模拟一个光谱峰
spectrum_colors = [
    (148, 0, 211),   # 紫
    (75, 0, 130),    # 靛
    (0, 0, 255),     # 蓝
    (0, 255, 0),     # 绿
    (255, 255, 0),   # 黄
    (255, 127, 0),   # 橙
    (255, 0, 0),     # 红
]

def gaussian(x, mu, sigma):
    return math.exp(-0.5 * ((x - mu) / sigma) ** 2)

points = []
n = chart_w
for i in range(n):
    x = chart_left + i
    t = i / n
    # 多个高斯峰叠加
    val = (0.3 * gaussian(t, 0.25, 0.06) +
           0.7 * gaussian(t, 0.45, 0.08) +
           1.0 * gaussian(t, 0.55, 0.05) +
           0.5 * gaussian(t, 0.75, 0.07) +
           0.2 * gaussian(t, 0.85, 0.04))
    y = chart_top + chart_h - int(val * chart_h * 0.9)
    points.append((x, y))

# 渐变填充曲线下的区域
for i in range(len(points) - 1):
    x0, y0 = points[i]
    x1, y1 = points[i + 1]
    # 颜色根据位置渐变 (紫 -> 蓝 -> 绿 -> 黄 -> 红)
    t = i / len(points)
    if t < 0.2:
        c = spectrum_colors[0]
    elif t < 0.35:
        c = spectrum_colors[1]
    elif t < 0.45:
        c = spectrum_colors[2]
    elif t < 0.55:
        c = spectrum_colors[3]
    elif t < 0.7:
        c = spectrum_colors[4]
    elif t < 0.85:
        c = spectrum_colors[5]
    else:
        c = spectrum_colors[6]

    fill_color = (c[0], c[1], c[2], 60)
    draw.polygon([(x0, y0), (x1, y1), (x1, chart_top + chart_h), (x0, chart_top + chart_h)],
                 fill=fill_color)

# 绘制曲线
for i in range(len(points) - 1):
    t = i / len(points)
    if t < 0.2:
        c = spectrum_colors[0]
    elif t < 0.35:
        c = spectrum_colors[1]
    elif t < 0.45:
        c = spectrum_colors[2]
    elif t < 0.55:
        c = spectrum_colors[3]
    elif t < 0.7:
        c = spectrum_colors[4]
    elif t < 0.85:
        c = spectrum_colors[5]
    else:
        c = spectrum_colors[6]
    draw.line([points[i], points[i + 1]], fill=c, width=3)

# 顶部棱镜/光束图标
prism_cx = 128
prism_top = 38

# 入射白光束
draw.line([(60, prism_top + 20), (prism_cx, prism_top + 20)],
          fill=(200, 200, 200), width=4)
# 白光箭头
draw.polygon([(prism_cx - 12, prism_top + 20), (prism_cx - 2, prism_top + 14),
              (prism_cx - 2, prism_top + 26)],
             fill=(200, 200, 200))

# 棱镜 (三角形)
prism_pts = [(prism_cx - 14, prism_top + 34),
             (prism_cx + 14, prism_top + 34),
             (prism_cx, prism_top + 8)]
draw.polygon(prism_pts, fill=(200, 210, 225), outline=(140, 150, 170), width=2)

# 色散光束
disp_colors = [(148, 0, 211), (0, 100, 255), (0, 200, 0),
               (255, 200, 0), (255, 80, 0), (255, 0, 0)]
for i, c in enumerate(disp_colors):
    angle = -10 + i * 7
    rad = math.radians(angle)
    x0 = prism_cx + 12
    y0 = prism_top + 28
    x1 = x0 + int(55 * math.cos(rad))
    y1 = y0 + int(55 * math.sin(rad))
    draw.line([(x0, y0), (x1, y1)], fill=c, width=2)

# 底部文字 "SP"
try:
    font = ImageFont.truetype("arial.ttf", 22)
except:
    font = ImageFont.load_default()
draw.text((128, 218), "SP", fill=(26, 115, 232), font=font, anchor="mm")

# 保存为 .ico
ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spectrometer.ico")
img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print(f"Icon saved: {ico_path}")

# 同时保存一张预览 PNG
png_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spectrometer_icon.png")
img.save(png_path)
print(f"Preview saved: {png_path}")
