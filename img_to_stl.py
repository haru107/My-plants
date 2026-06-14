#!/usr/bin/env python3
"""ラスター画像(黒線/白背景のライン画) -> 3Dプリント用 STL。
黒い部分=造形(フィラメント)、白い部分=空洞 として輪郭を抽出し、指定厚みで押し出す。
Meshy等の外部サービス不要。クリーンな線画(白背景・黒線)が最も得意。

使い方:
  python3 img_to_stl.py 入力.png 出力.stl [--width-mm 120] [--thickness 2.5] [--thresh 128] [--simplify 0.8] [--min-area 1.0]
"""
import argparse, sys
import numpy as np
import cv2
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import trimesh


def contours_to_polygons(mask, simplify_px, min_area_px):
    cnts, hier = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None:
        return []
    hier = hier[0]

    def depth(i):
        d, p = 0, hier[i][3]
        while p != -1:
            d += 1; p = hier[p][3]
        return d

    def simp(c):
        if simplify_px > 0:
            c = cv2.approxPolyDP(c, simplify_px, True)
        return c[:, 0, :].astype(float)

    polys = []
    for i, c in enumerate(cnts):
        if depth(i) % 2 != 0:        # 奇数階層=穴。親(偶数)側でまとめて処理
            continue
        if cv2.contourArea(c) < min_area_px:
            continue
        shell = simp(c)
        if len(shell) < 3:
            continue
        holes = []
        ch = hier[i][2]              # first child
        while ch != -1:
            if cv2.contourArea(cnts[ch]) >= min_area_px:
                h = simp(cnts[ch])
                if len(h) >= 3:
                    holes.append(h)
            ch = hier[ch][0]         # next sibling
        polys.append((shell, holes))
    return polys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--width-mm", type=float, default=120.0, help="完成幅(mm)")
    ap.add_argument("--thickness", type=float, default=2.5, help="厚み(mm)")
    ap.add_argument("--thresh", type=int, default=128, help="二値化しきい値(0-255,小さいほど黒だけ拾う)")
    ap.add_argument("--simplify", type=float, default=0.8, help="輪郭の簡略化(px)")
    ap.add_argument("--min-area", type=float, default=1.0, help="無視する微小領域(px^2)")
    ap.add_argument("--invert", action="store_true", help="白線/黒背景のとき指定")
    ap.add_argument("--clean", type=float, default=0.15, help="接触部の溶接量(mm)。0で無効")
    a = ap.parse_args()

    img = cv2.imread(a.inp, cv2.IMREAD_GRAYSCALE)
    if img is None:
        print("画像を読めません:", a.inp); sys.exit(1)
    H, W = img.shape
    # 黒線=前景(255)にする
    _, mask = cv2.threshold(img, a.thresh, 255, cv2.THRESH_BINARY_INV)
    if a.invert:
        mask = 255 - mask

    polys_px = contours_to_polygons(mask, a.simplify, a.min_area)
    if not polys_px:
        print("輪郭が見つかりません。--thresh を調整してください。"); sys.exit(1)

    scale = a.width_mm / W
    def tx(pts):                      # px -> mm, Y反転(画像はY下向き)
        out = pts.copy()
        out[:, 0] *= scale
        out[:, 1] = (H - pts[:, 1]) * scale
        return out

    shp = []
    for shell, holes in polys_px:
        p = Polygon(tx(shell), [tx(h) for h in holes])
        if not p.is_valid:
            p = p.buffer(0)
        if p.is_empty or p.area <= 0:
            continue
        shp.append(p)
    geom = unary_union(shp)
    if a.clean > 0:                   # 接触部の溶接&スリバー除去で密閉性UP
        geom = geom.buffer(a.clean).buffer(-a.clean)
    geoms = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]

    meshes = []
    for g in geoms:
        if g.is_empty or g.area <= 0:
            continue
        try:
            meshes.append(trimesh.creation.extrude_polygon(g, height=a.thickness, engine="triangle"))
        except Exception as e:
            print("  押し出しスキップ:", e)
    mesh = trimesh.util.concatenate(meshes)
    # 印刷向けに後処理(重複頂点マージ・退化面除去・法線整え)
    mesh.merge_vertices()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.update_faces(mesh.unique_faces())
    mesh.fix_normals()
    mesh.export(a.out)

    ext = mesh.bounds[1] - mesh.bounds[0]
    print(f"OK -> {a.out}")
    print(f"  パーツ数(連結成分の押し出し): {len(meshes)}")
    print(f"  サイズ: {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm")
    print(f"  頂点 {len(mesh.vertices)} / 面 {len(mesh.faces)} / watertight={mesh.is_watertight}")
    print(f"  体積 ~{mesh.volume/1000:.1f} cm^3 (材料の目安)")


if __name__ == "__main__":
    main()
