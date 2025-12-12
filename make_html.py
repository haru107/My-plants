import os
import cv2
import glob
import csv
import json  # manifest.json生成用に追加

# === 設定エリア ===
MASTER_DIR = "master_data"
PUBLIC_DIR = "public_html"
IMG_OUT_DIR = os.path.join(PUBLIC_DIR, "img")
CSV_FILE = "plants.csv"
MAX_SIZE = 800
LOGO_FILE = "logo.png"  # ★ここを実際のロゴファイル名に変更してください
# =================

os.makedirs(IMG_OUT_DIR, exist_ok=True)

# --- 0. manifest.jsonの生成 (Androidホーム画面アイコン用) ---
manifest_data = {
    "name": "My Plant Collection",
    "short_name": "Plants",
    "start_url": "./index.html",
    "display": "standalone",
    "background_color": "#f4f5f7",
    "theme_color": "#2eaadc",
    "icons": [
        {
            "src": LOGO_FILE,
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": LOGO_FILE,
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
}

# manifest.jsonをpublic_htmlに保存
with open(os.path.join(PUBLIC_DIR, "manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest_data, f, indent=4)
    print(f"✅ manifest.json を生成しました (アイコン: {LOGO_FILE})")


# --- 1. CSV読み込み ---
plant_db = {}
all_genera = set()

if os.path.exists(CSV_FILE):
    try:
        with open(CSV_FILE, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("ID")
                genus = row.get("属", "").strip()
                if pid:
                    plant_db[pid] = row
                    if genus:
                        all_genera.add(genus)
    except Exception as e:
        print(f"⚠️ CSV読み込みエラー: {e}")

sorted_genera = sorted(list(all_genera))

# --- HTMLヘッダー ---
html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Plant Collection</title>
    
    <link rel="icon" href="{LOGO_FILE}">
    <link rel="apple-touch-icon" href="{LOGO_FILE}">
    <link rel="manifest" href="manifest.json">
    
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #f4f5f7;
            --text-color: #333;
            --card-bg: #ffffff;
            --border-color: #ddd;
            --accent-color: #2eaadc;
        }}
        body {{ 
            font-family: 'Inter', sans-serif; 
            background: var(--bg-color); 
            color: var(--text-color); 
            padding: 10px;
            margin: 0;
            font-size: 14px;
        }}
        
        /* ヘッダー */
        .header-container {{
            max-width: 1000px;
            margin: 0 auto 20px auto;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        
        .site-title-area {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }}
        
        .site-logo {{
            width: 50px;
            height: 50px;
            object-fit: contain;
            border-radius: 8px; /* 角丸にする */
        }}

        h1 {{ margin: 0; font-size: 1.8em; color: #2c3e50; }}
        
        .search-box {{
            width: 100%; max-width: 400px; padding: 8px 10px;
            border: 1px solid #ccc; border-radius: 4px;
            font-size: 14px; margin-bottom: 10px;
        }}
        .filter-container {{ display: flex; gap: 5px; flex-wrap: wrap; justify-content: center; }}
        .filter-btn {{
            border: none; background: #e0e0e0; color: #555;
            padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600;
        }}
        .filter-btn.active {{ background: #333; color: white; }}

        /* === リスト表示レイアウト === */
        .gallery-grid {{
            display: flex;
            flex-direction: column;
            gap: 15px;
            max-width: 1000px;
            margin: 0 auto;
        }}
        
        .plant-card {{ 
            background: var(--card-bg); 
            border: 1px solid var(--border-color); 
            border-radius: 6px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        
        .card-info {{ 
            padding: 6px 12px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #fafafa;
        }}
        
        .id-badge {{ 
            font-size: 0.75em; color: white; background: #555; 
            padding: 2px 6px; border-radius: 3px; font-family: monospace;
            display: inline-block; margin-right: 8px; vertical-align: middle;
        }}
        .plant-name {{ 
            font-size: 1.2em; font-weight: 700; margin: 0; display: inline-block; vertical-align: middle;
        }}
        .plant-genus {{ 
            font-size: 0.75em; color: var(--accent-color); 
            background: #eef9fd; padding: 2px 6px; border-radius: 3px; font-weight: 600;
            display: inline-block; margin-left: 8px; vertical-align: middle;
        }}
        
        .info-right {{ text-align: right; font-size: 0.85em; display: flex; gap: 15px; align-items: center; }}
        
        .memo-row {{ 
            font-size: 0.85em; color: #665c38; background: #fffbe6; 
            padding: 4px 12px; border-bottom: 1px solid #f9f9f9;
        }}

        .photo-strip {{
            display: flex;
            overflow-x: auto;
            scroll-behavior: smooth;
            background: #fff;
            padding: 10px;
            gap: 10px;
            height: 220px;
            align-items: center;
        }}
        .photo-strip::-webkit-scrollbar {{ height: 8px; }}
        .photo-strip::-webkit-scrollbar-thumb {{ background: #ddd; border-radius: 4px; }}
        
        .photo-item {{
            flex: 0 0 auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 200px;
        }}
        .photo-item img {{
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-radius: 4px;
            border: 1px solid #eee;
        }}
        .photo-item img:hover {{ opacity: 0.9; transform: scale(1.02); transition: 0.2s; }}
        
        .photo-date {{ font-size: 0.7em; color: #888; margin-top: 2px; }}

        @media (max-width: 600px) {{
            .card-info {{ flex-direction: column; align-items: flex-start; gap: 5px; }}
            .info-right {{ width: 100%; justify-content: space-between; margin-top: 5px; }}
            .plant-genus {{ margin-left: 0; margin-top: 2px; display: block; width: fit-content; }}
        }}

    </style>
</head>
<body>

<div class="header-container">
    <div class="site-title-area">
        <img src="{LOGO_FILE}" alt="Logo" class="site-logo">
        <h1>My Plant Collection</h1>
    </div>
    
    <input type="text" id="searchInput" class="search-box" placeholder="名前やIDで検索..." onkeyup="filterPlants()">
    <div class="filter-container">
        <button class="filter-btn active" onclick="filterByGenus('all')">All</button>
"""
for genus in sorted_genera:
    if genus:
        html_content += f'<button class="filter-btn" onclick="filterByGenus(\'{genus}\')">{genus}</button>\n'

html_content += """
    </div>
</div>

<div class="gallery-grid" id="galleryGrid">
"""

print("-" * 30)
print("🎨 HTML図鑑の生成を開始します（ロゴ＆マニフェスト対応版）...")

plant_dirs = sorted(glob.glob(os.path.join(MASTER_DIR, "*")))

for plant_path in plant_dirs:
    if not os.path.isdir(plant_path): continue
        
    plant_id = os.path.basename(plant_path)
    info = plant_db.get(plant_id, {})
    genus = info.get("属", "Unknown")
    species = info.get("品種名", "Unknown Species")
    shop = info.get("購入場所", "-")
    price = info.get("購入価格", "-")
    memo = info.get("メモ", "")
    
    search_text = f"{plant_id} {genus} {species} {shop} {memo}".lower()
    
    photos = sorted(glob.glob(os.path.join(plant_path, "*")), reverse=True)
    
    html_content += f'''
    <div class="plant-card" data-genus="{genus}" data-search="{search_text}">
        
        <div class="card-info">
            <div class="info-left">
                <span class="id-badge">{plant_id}</span>
                <span class="plant-name">{species}</span>
                <span class="plant-genus">{genus}</span>
            </div>
            <div class="info-right">
                <span title="購入場所">🛒 {shop}</span>
                <span title="購入価格">💰 ¥{price}</span>
                <span style="color:#aaa; font-size:0.9em;">{len(photos)}枚</span>
            </div>
        </div>
        
        {f'<div class="memo-row">📝 {memo}</div>' if memo else ''}

        <div class="photo-strip">
    '''
    
    if not photos:
        html_content += '<div style="padding:10px; color:#ccc; font-size:0.8em;">No Image</div>'
    
    for photo_path in photos:
        filename = os.path.basename(photo_path)
        name, ext = os.path.splitext(filename)
        if ext.lower() not in ['.jpg', '.jpeg', '.png']: continue

        thumb_filename = f"{name}_thumb{ext}"
        thumb_path = os.path.join(IMG_OUT_DIR, thumb_filename)
        
        if not os.path.exists(thumb_path):
            img = cv2.imread(photo_path)
            if img is not None:
                h, w = img.shape[:2]
                if max(h, w) > MAX_SIZE:
                    scale = MAX_SIZE / max(h, w)
                    img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
                cv2.imwrite(thumb_path, img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        
        display_date = "-"
        try:
            parts = name.split('_')
            if len(parts) >= 2 and len(parts[1]) == 8:
                d_str = parts[1]
                display_date = f"{d_str[:4]}/{d_str[4:6]}/{d_str[6:]}"
        except: pass

        html_content += f'''
            <div class="photo-item">
                <a href="img/{thumb_filename}" target="_blank">
                    <img src="img/{thumb_filename}" loading="lazy" alt="{species}">
                </a>
                <span class="photo-date">{display_date}</span>
            </div>
        '''

    html_content += '''
        </div> </div> '''

html_content += """
</div>

<script>
    function filterByGenus(genus) {
        var btns = document.getElementsByClassName("filter-btn");
        for (var i = 0; i < btns.length; i++) {
            btns[i].classList.remove("active");
            if (btns[i].innerText === genus || (genus === 'all' && btns[i].innerText === 'All')) {
                btns[i].classList.add("active");
            }
        }
        var cards = document.getElementsByClassName("plant-card");
        for (var i = 0; i < cards.length; i++) {
            var cardGenus = cards[i].getAttribute("data-genus");
            cards[i].style.display = (genus === 'all' || cardGenus === genus) ? "" : "none";
        }
    }
    function filterPlants() {
        var filter = document.getElementById('searchInput').value.toLowerCase();
        var cards = document.getElementsByClassName('plant-card');
        for (var i = 0; i < cards.length; i++) {
            var searchText = cards[i].getAttribute('data-search');
            cards[i].style.display = (searchText.indexOf(filter) > -1) ? "" : "none";
        }
    }
</script>
</body>
</html>
"""

with open(os.path.join(PUBLIC_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(html_content)

print("-" * 30)
print(f"✅ 生成完了！ロゴ設定とPWA対応を追加しました。")