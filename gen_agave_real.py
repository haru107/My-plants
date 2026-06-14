#!/usr/bin/env python3
"""リアル寄りのアガベ(parryi truncata = アーティチョーク型)ロゼット線画を生成。
特徴: 幅広で丸い葉が同心円状に密に重なる + 各葉先に黒いトゲ + 内側ほど小さい。
出力: docs/agave_real.svg (印刷用) と docs/agave_real_preview.png。
描画順は外周→中心。葉を白塗り+黒線で重ねることで“重なり”をきれいに見せる。
"""
import math

CX, CY = 110.0, 120.0
W, H = 220.0, 240.0
SW = 1.3
leaves = []   # 各葉 (outline_d, spine_d, midrib_d) を後で順に描画

def leaf(angle_deg, r0, L, Wd):
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)        # 外向き
    px, py = -math.sin(a), math.cos(a)       # 接線
    def pt(d, w):                            # 中心からd外側・接線方向wの点
        return (CX + dx*d + px*w, CY + dy*d + py*w)
    baseL = pt(r0, Wd*0.16); baseR = pt(r0, -Wd*0.16)
    wideL = pt(r0+L*0.58, Wd*0.5); wideR = pt(r0+L*0.58, -Wd*0.5)
    tip   = pt(r0+L, 0)
    cLa = pt(r0+L*0.30, Wd*0.46); cLb = pt(r0+L*0.86, Wd*0.30)
    cRa = pt(r0+L*0.30, -Wd*0.46); cRb = pt(r0+L*0.86, -Wd*0.30)
    def P(p): return f"{p[0]:.2f},{p[1]:.2f}"
    outline = (f"M {P(baseL)} Q {P(cLa)} {P(wideL)} Q {P(cLb)} {P(tip)} "
               f"Q {P(cRb)} {P(wideR)} Q {P(cRa)} {P(baseR)} Z")
    # 先端の黒トゲ(細い三角)
    sp_len = L*0.16; sp_w = Wd*0.06
    spt = pt(r0+L+sp_len, 0)
    spl = pt(r0+L-sp_len*0.1, sp_w); spr = pt(r0+L-sp_len*0.1, -sp_w)
    spine = f"M {P(spl)} L {P(spt)} L {P(spr)} Z"
    # 中肋(外側の大きい葉のみ、控えめ)
    midrib = (f"M {P(pt(r0+L*0.12,0))} L {P(pt(r0+L*0.6,0))}") if L > 26 else ""
    leaves.append((outline, spine, midrib))

def ring(n, r0, L, Wd, offset=0.0):
    for i in range(n):
        leaf(GROT + offset + 360.0*i/n, r0, L, Wd)

GROT = 9.0   # 全体を少し回し、左右の葉が一直線に並ぶ(中心の横線)のを防ぐ
# 外周→中心。内側ほど小さく、半ステップずらして葉の隙間を埋める
ring(15, 30, 56, 34, offset=0)
ring(14, 25, 47, 31, offset=12)
ring(12, 20, 39, 28, offset=0)
ring(10, 15, 31, 24, offset=18)
ring(8,  11, 24, 20, offset=0)
ring(6,   7, 17, 16, offset=30)
ring(4,   4, 11, 12, offset=0)
ring(3,   2,  7,  9, offset=40)

def build(stroke="#111", fill="#ffffff", spine_fill="#111", show_mid=True, bg=None):
    parts = []
    if bg:
        parts.append(f'<rect width="{W}" height="{H}" fill="{bg}"/>')
    # 外周から順に: 葉(白塗り)→中肋→トゲ。次の内側葉が前の基部を隠す
    for outline, spine, midrib in leaves:
        parts.append(f'<path d="{outline}" fill="{fill}" stroke="{stroke}" stroke-width="{SW}" stroke-linejoin="round"/>')
        if show_mid and midrib:
            parts.append(f'<path d="{midrib}" fill="none" stroke="{stroke}" stroke-width="{SW*0.7}" stroke-linecap="round"/>')
        parts.append(f'<path d="{spine}" fill="{spine_fill}" stroke="{spine_fill}" stroke-width="0.4"/>')
    body = "\n  ".join(parts)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">\n  '
            f'{body}\n</svg>\n')

# 印刷用(白塗り=ベタ面の相当。輪郭が活きる)
with open("docs/agave_real.svg", "w") as f:
    f.write(build())
print("wrote docs/agave_real.svg  leaves:", len(leaves))

import cairosvg
cairosvg.svg2png(bytestring=build(bg="#efeae0").encode(),
                 write_to="docs/agave_real_preview.png",
                 output_width=680, output_height=742)
print("wrote docs/agave_real_preview.png")
