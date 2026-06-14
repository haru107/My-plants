#!/usr/bin/env python3
"""平面アガベの線画を手続き生成する。
出力: agave_flat.svg (印刷用 / SVG->押し出し前提) と プレビュー用 PNG。
スタイル: 黒の輪郭線のみ(塗りなし)、放射状ロゼット + 垂れた茎 + 枝分かれした根 + 球根風の重し。
"""
import math, random

random.seed(7)

CX, CY = 110.0, 100.0        # ロゼット中心
W, H = 220.0, 340.0          # キャンバス(mm想定)
SW = 1.6                     # 線幅(mm) ≒ 印刷時の太さ

paths = []   # (d文字列, 追加属性)

def P(x, y):
    return f"{x:.2f},{y:.2f}"

def leaf(angle_deg, r0, length, width, bulge=0.55, curl=0.0):
    """中心から angle 方向に伸びる尖った葉。輪郭(閉)＋中肋線＋スケッチ線を返す。"""
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -math.sin(a), math.cos(a)        # 法線
    # わずかに反らせる(curl)ことで有機的に
    cx2, cy2 = math.cos(a + curl), math.sin(a + curl)
    baseL = (CX + dx*r0 + px*width/2, CY + dy*r0 + py*width/2)
    baseR = (CX + dx*r0 - px*width/2, CY + dy*r0 - py*width/2)
    tip   = (CX + cx2*(r0+length),     CY + cy2*(r0+length))
    ctrlL = (CX + dx*(r0+length*0.5) + px*width*bulge, CY + dy*(r0+length*0.5) + py*width*bulge)
    ctrlR = (CX + dx*(r0+length*0.5) - px*width*bulge, CY + dy*(r0+length*0.5) - py*width*bulge)
    outline = f"M {P(*baseL)} Q {P(*ctrlL)} {P(*tip)} Q {P(*ctrlR)} {P(*baseR)} Z"
    paths.append(outline)
    # 中肋(葉脈)
    midbase = (CX + dx*r0, CY + dy*r0)
    paths.append(f"M {P(*midbase)} Q {P(CX+dx*(r0+length*0.5), CY+dy*(r0+length*0.5))} {P(*tip)}")

def ring(n, r0, length, width, offset=0.0, bulge=0.55, curlamp=0.0):
    for i in range(n):
        ang = offset + 360.0*i/n
        curl = curlamp*math.sin(i*2.1)        # 葉ごとに少し違う反り
        leaf(ang, r0, length, width, bulge, curl)

# --- ロゼット(外周ほど大きく寝かせ、内側ほど小さく立てる) ---
# 葉は幅広めの披針形。層を絞り、中心は開けて“団子化”を防ぐ。
ring(12, 16, 64, 30, offset=0,    bulge=0.72, curlamp=0.10)   # 外周
ring(11, 11, 48, 25, offset=16,   bulge=0.74, curlamp=0.12)
ring(9,  7,  34, 20, offset=4,    bulge=0.76, curlamp=0.14)   # 内側
ring(6,  4,  21, 15, offset=24,   bulge=0.80, curlamp=0.16)   # 中心まわり

# --- 茎(中心下から S 字で垂れる) ---
sx, sy = CX, CY + 14
ex, ey = CX + 6, 300
stem = (f"M {P(sx,sy)} C {P(sx-26, sy+70)} {P(ex+30, sy+150)} {P(ex,ey)}")
paths.append(stem)

# --- 根(茎の先で枝分かれ) ---
root_specs = [(-34, 38), (-12, 30), (10, 44), (28, 34), (44, 22)]
for dxr, ln in root_specs:
    midx = ex + dxr*0.4 + random.uniform(-3,3)
    midy = ey + ln*0.5
    tipx = ex + dxr
    tipy = ey + ln
    paths.append(f"M {P(ex,ey)} Q {P(midx,midy)} {P(tipx,tipy)}")

# --- 球根風の重し(根元の小さな塊) ---
bulb_r = 7
paths.append(f"M {P(ex-bulb_r, ey)} a {bulb_r},{bulb_r} 0 1,0 {2*bulb_r},0 a {bulb_r},{bulb_r} 0 1,0 {-2*bulb_r},0 Z")
# 球の中にスクリブル(線画の質感)
for k in range(5):
    yy = ey - bulb_r*0.6 + k*bulb_r*0.3
    paths.append(f"M {P(ex-bulb_r*0.7, yy)} L {P(ex+bulb_r*0.7, yy+1.2)}")

# --- SVG 組み立て ---
body = "\n".join(
    f'  <path d="{d}" />' for d in paths
)
svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm"
     viewBox="0 0 {W} {H}">
  <g fill="none" stroke="#111111" stroke-width="{SW}"
     stroke-linecap="round" stroke-linejoin="round">
{body}
  </g>
</svg>
'''
with open("docs/agave_flat.svg", "w") as f:
    f.write(svg)
print("wrote docs/agave_flat.svg  (paths:", len(paths), ")")

# プレビューPNG(背景白) — 木目っぽさは出さず設計プレビューとして
import cairosvg
# 白背景版
svg_white = svg.replace('<g fill="none"',
                        f'<rect width="{W}" height="{H}" fill="#f3efe6"/>\n  <g fill="none"')
cairosvg.svg2png(bytestring=svg_white.encode(), write_to="docs/agave_flat_preview.png",
                 output_width=660, output_height=1020)
print("wrote docs/agave_flat_preview.png")
