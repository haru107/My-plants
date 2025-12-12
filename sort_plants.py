import cv2
import glob
import os
import shutil
import numpy as np
from datetime import datetime
from PIL import Image
from pyzbar.pyzbar import decode  # 強力なQRリーダー

# === 設定エリア ===
INPUT_DIR = "input"       # 写真が入っている元フォルダ
MASTER_DIR = "master_data" # 整理先のフォルダ
# =================

def get_date_taken(path):
    """ 画像のExifデータから撮影日時を取得する """
    try:
        image = Image.open(path)
        exif = getattr(image, '_getexif', lambda: None)()
        if not exif:
            exif = image.getexif()
            
        if exif:
            # 36867: DateTimeOriginal, 36868: DateTimeDigitized, 306: DateTime
            target_tags = [36867, 36868, 306]
            for tag_id in target_tags:
                if tag_id in exif:
                    date_val = exif[tag_id]
                    if isinstance(date_val, str) and ":" in date_val:
                        # "2023:12:18 19:50:00" -> "20231218"
                        return date_val.split(" ")[0].replace(":", "")
    except:
        pass
    
    # Exifがなければファイルの更新日時を使う
    try:
        mtime = os.path.getmtime(path)
        return datetime.fromtimestamp(mtime).strftime("%Y%m%d")
    except:
        return datetime.now().strftime("%Y%m%d")

def detect_qr_strong(img):
    """
    ★強力版QR検出関数
    画像を加工しながら、読み取れるまで何度かトライする
    """
    # 1. そのままトライ
    decoded = decode(img)
    if decoded:
        return decoded[0].data.decode('utf-8')

    # 2. グレースケールでトライ
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    decoded = decode(gray)
    if decoded:
        return decoded[0].data.decode('utf-8')

    # 3. コントラストを強調してトライ (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    decoded = decode(enhanced)
    if decoded:
        return decoded[0].data.decode('utf-8')

    # 4. 二値化（白黒はっきりさせる）してトライ
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    decoded = decode(binary)
    if decoded:
        return decoded[0].data.decode('utf-8')

    return None

# メイン処理開始
if __name__ == "__main__":
    # 出力先フォルダの作成
    if not os.path.exists(MASTER_DIR):
        os.makedirs(MASTER_DIR)
        print(f"📁 {MASTER_DIR} フォルダを作成しました。")

    print("-" * 30)
    print("🚀 植物写真の自動仕分け（強力QR検出版）を開始します...")
    print(f"対象: {INPUT_DIR} → 保存先: {MASTER_DIR}")
    print("-" * 30 + "\n")

    # ファイル一覧を取得してソート
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "*")))
    
    current_plant_id = None

    for file_path in files:
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        
        # 画像ファイル以外はスキップ
        if ext.lower() not in ['.jpg', '.jpeg', '.png']:
            continue

        # 画像読み込み
        img_cv = cv2.imread(file_path)
        if img_cv is None:
            print(f"⚠️ 読込失敗（スキップ）: {filename}")
            continue

        # ★QRコードを探す（強力版）
        qr_data = detect_qr_strong(img_cv)

        if qr_data:
            # --- パターンA: QRコード（区切り） ---
            new_id = qr_data
            
            if new_id != current_plant_id:
                # 新しいIDが見つかった場合
                current_plant_id = new_id
                print(f"\n🔄 --- ID切り替え: 「{current_plant_id}」 ---")
                print(f"   (トリガー画像: {filename})")  # ★どの写真で切り替わったか表示
            else:
                # 同じIDのQRが連続した場合（連写など）
                print(f"   [QR検出] {filename} (ID: {new_id} - 維持)")

        else:
            # --- パターンB: 植物写真 ---
            if current_plant_id is None:
                # まだQRが見つかっていない状態の写真はスキップ
                print(f"⚠️  スキップ（ID不明 - QR未検出）: {filename}")
                continue

            # 画像から「撮影日」を取得
            photo_date = get_date_taken(file_path)

            # 保存先フォルダを作成
            target_dir = os.path.join(MASTER_DIR, current_plant_id)
            os.makedirs(target_dir, exist_ok=True)

            # ファイル名決定 (ID_撮影日_連番.jpg)
            save_counter = 1
            while True:
                new_filename = f"{current_plant_id}_{photo_date}_{save_counter:02d}{ext}"
                target_path = os.path.join(target_dir, new_filename)
                
                # 同じ名前のファイルがない場合 -> 新規保存
                if not os.path.exists(target_path):
                    shutil.copy2(file_path, target_path)
                    print(f"✅ 保存: {filename} → {new_filename}")
                    break
                
                # 同じ名前がある場合 -> 中身（サイズ）を比較
                if os.path.getsize(target_path) == os.path.getsize(file_path):
                    print(f"⏭️  保存済み（スキップ）: {new_filename}")
                    break
                
                # 名前は同じだけど中身が違う（別の写真）なら、連番を増やして次を探す
                save_counter += 1

    print("\n" + "-" * 30)
    print("🎉 全ての処理が完了しました！")