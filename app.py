import os
import csv
import datetime
import subprocess
import json
from flask import Flask, request, redirect, send_from_directory, send_file

app = Flask(__name__)

# === 設定エリア ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_DIR = os.path.join(BASE_DIR, 'master_data')
PUBLIC_DIR = os.path.join(BASE_DIR, 'public_html')
CSV_FILE = os.path.join(BASE_DIR, 'plants.csv')
# =================

os.makedirs(MASTER_DIR, exist_ok=True)
os.makedirs(PUBLIC_DIR, exist_ok=True)

@app.route('/')
def index():
    return send_from_directory(PUBLIC_DIR, 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(PUBLIC_DIR, filename)

@app.route('/master_img/<path:filename>')
def master_img(filename):
    return send_from_directory(MASTER_DIR, filename)

@app.route('/download_csv')
def download_csv():
    try:
        return send_file(CSV_FILE, as_attachment=True, download_name='plants.csv')
    except Exception as e:
        return f"エラー: {e}"

# ★写真整理（削除）モード
@app.route('/admin/gallery', methods=['GET', 'POST'])
def gallery_mode():
    if request.method == 'POST':
        # 削除処理
        photo_path = request.form.get('photo_path') # ID/filename.jpg
        p_id = request.form.get('id')

        if photo_path and p_id:
            full_path = os.path.join(MASTER_DIR, photo_path)
            
            # 1. 写真を削除
            if os.path.exists(full_path):
                os.remove(full_path)
            
            # 2. フォルダが空になったか確認
            dir_path = os.path.join(MASTER_DIR, p_id)
            if os.path.exists(dir_path) and not os.listdir(dir_path):
                # 空ならフォルダを削除
                os.rmdir(dir_path)
                
                # CSVからもそのIDを削除
                if os.path.isfile(CSV_FILE):
                    new_lines = []
                    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
                        reader = csv.reader(f)
                        for row in reader:
                            if row and row[0] != p_id:
                                new_lines.append(row)
                    with open(CSV_FILE, 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerows(new_lines)

            # 図鑑更新
            subprocess.run(["python3", "make_html.py"], cwd=BASE_DIR)

        return redirect('/admin/gallery')

    # --- 表示用データ作成 ---
    plants_data = [] 
    csv_info = {} # {ID: {genus, name}}
    all_genera = set()

    if os.path.isfile(CSV_FILE):
        try:
            with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('ID'):
                        name = f"{row.get('属','')} {row.get('品種名','')}"
                        genus = row.get('属','')
                        csv_info[row['ID']] = {'name': name, 'genus': genus}
                        if genus: all_genera.add(genus)
        except:
            pass
    
    sorted_genera = sorted(list(all_genera))

    if os.path.exists(MASTER_DIR):
        dir_list = sorted(os.listdir(MASTER_DIR))
        for p_id in dir_list:
            d_path = os.path.join(MASTER_DIR, p_id)
            if os.path.isdir(d_path):
                photos = []
                for f in sorted(os.listdir(d_path)):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                        photos.append(f)
                
                if photos:
                    info = csv_info.get(p_id, {'name': p_id, 'genus': '不明'})
                    plants_data.append({
                        'id': p_id,
                        'name': info['name'],
                        'genus': info['genus'],
                        'photos': photos
                    })

    # 検索用HTML
    return f'''
    <!doctype html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>写真整理モード</title>
        <style>
            body {{ font-family: sans-serif; background: #333; color: white; margin: 0; padding: 10px; }}
            h1 {{ text-align: center; font-size: 20px; color: #eee; margin-bottom:10px; }}
            
            .filter-bar {{ background: #444; padding: 10px; border-radius: 8px; margin-bottom: 15px; position: sticky; top: 0; z-index: 100; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
            .filter-row {{ display: flex; gap: 10px; margin-bottom: 5px; }}
            select, input {{ width: 100%; padding: 8px; border-radius: 5px; border: none; font-size: 14px; }}
            input {{ background: #fff; }}
            select {{ background: #eee; }}

            .plant-card {{ background: #444; margin-bottom: 15px; border-radius: 8px; overflow: hidden; border: 1px solid #555; }}
            .plant-header {{ background: #555; padding: 8px; font-weight: bold; font-size: 14px; color: #ffeb3b; display: flex; justify-content: space-between; }}
            
            /* ▼▼▼ ここを修正しました ▼▼▼ */
            .photo-grid {{ display: flex; flex-wrap: wrap; gap: 4px; padding: 4px; }}
            .photo-item {{ position: relative; width: calc(10% - 4px); aspect-ratio: 1 / 1; }}
            /* ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲ */

            .photo-item img {{ width: 100%; height: 100%; object-fit: cover; display: block; border-radius: 3px; }}
            .del-btn {{ 
                position: absolute; bottom: 0; right: 0; width: 100%; 
                background: rgba(255,0,0,0.7); color: white; border: none; 
                padding: 4px; font-size: 10px; cursor: pointer;
            }}
            .back-btn {{ display: block; width: 100%; padding: 12px; background: #666; color: white; text-align: center; text-decoration: none; font-weight: bold; margin-bottom: 15px; border-radius: 5px; font-size: 14px; }}
        </style>
        <script>
            function filterGallery() {{
                const search = document.getElementById('search_box').value.toLowerCase();
                const genus = document.getElementById('genus_select').value;
                const cards = document.getElementsByClassName('plant-card');

                for (let card of cards) {{
                    const cardText = card.dataset.search.toLowerCase();
                    const cardGenus = card.dataset.genus;
                    
                    let hitSearch = cardText.includes(search);
                    let hitGenus = (genus === "" || cardGenus === genus);

                    if (hitSearch && hitGenus) {{
                        card.style.display = "block";
                    }} else {{
                        card.style.display = "none";
                    }}
                }}
            }}
        </script>
    </head>
    <body>
        <a href="/admin" class="back-btn">← 管理メニューに戻る</a>
        
        <div class="filter-bar">
            <div class="filter-row">
                <select id="genus_select" onchange="filterGallery()">
                    <option value="">全ての属を表示</option>
                    {''.join([f'<option value="{g}">{g}</option>' for g in sorted_genera])}
                </select>
            </div>
            <div class="filter-row">
                <input type="text" id="search_box" placeholder="🔍 名前やIDで検索..." onkeyup="filterGallery()">
            </div>
        </div>

        <p style="text-align:center; font-size:11px; color:#aaa; margin-top:-5px;">
            最後の1枚を消すとデータごと消えます
        </p>
        
        <div id="gallery-container">
        {''.join([f'''
        <div class="plant-card" data-genus="{p['genus']}" data-search="{p['name']} {p['id']}">
            <div class="plant-header">
                <span>{p['name']}</span>
                <span style="font-size:12px; color:#ddd;">{p['genus']}</span>
            </div>
            <div class="photo-grid">
                {''.join([f'''
                <div class="photo-item">
                    <img src="/master_img/{p['id']}/{photo}" loading="lazy">
                    <form method="post" onsubmit="return confirm('本当に削除しますか？');">
                        <input type="hidden" name="photo_path" value="{p['id']}/{photo}">
                        <input type="hidden" name="id" value="{p['id']}">
                        <button type="submit" class="del-btn">🗑️</button>
                    </form>
                </div>
                ''' for photo in p['photos']])}
            </div>
        </div>
        ''' for p in plants_data])}
        </div>
        
        <br><br>
        <a href="/admin" class="back-btn">← 管理メニューに戻る</a>
    </body>
    </html>
    '''

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    msg = ""

    existing_plants = {}
    if os.path.isfile(CSV_FILE):
        try:
            with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('ID'):
                        key = row['ID']
                        label = f"{row.get('属','')} {row.get('品種名','')}"
                        if row.get('購入場所'):
                            label += f" ({row.get('購入場所')})"
                        existing_plants[key] = {
                            'label': label,
                            'genus': row.get('属',''),
                            'species': row.get('品種名',''),
                            'shop': row.get('購入場所',''),
                            'price': row.get('購入価格',''),
                            'memo': row.get('メモ','')
                        }
        except:
            pass
    
    sorted_keys = sorted(existing_plants.keys(), key=lambda k: existing_plants[k]['label'])

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'register':
            p_id = request.form.get('id')
            genus = request.form.get('genus')
            species = request.form.get('species')
            shop = request.form.get('shop')
            price = request.form.get('price')
            memo = request.form.get('memo')
            files = request.files.getlist('files')

            if p_id:
                # CSV更新
                file_exists = os.path.isfile(CSV_FILE)
                with open(CSV_FILE, 'a', encoding='utf-8-sig', newline='') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(['ID', '属', '品種名', '購入場所', '購入価格', 'メモ'])
                    writer.writerow([p_id, genus, species, shop, price, memo])

                # 写真保存
                save_dir = os.path.join(MASTER_DIR, p_id)
                os.makedirs(save_dir, exist_ok=True)
                now_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                
                count = 0
                for i, file in enumerate(files):
                    if file and file.filename:
                        ext = os.path.splitext(file.filename)[1]
                        filename = f"{p_id}_{now_str}_{i+1}{ext}"
                        file.save(os.path.join(save_dir, filename))
                        count += 1
                
                # 更新
                subprocess.run(["python3", "make_html.py"], cwd=BASE_DIR)
                msg = f"✅ 更新完了: {genus} {species}"

        elif action == 'rebuild':
            subprocess.run(["python3", "make_html.py"], cwd=BASE_DIR)
            msg = "🔄 再構築完了"

        elif action == 'github_push':
            try:
                subprocess.run(["python3", "make_html.py"], cwd=BASE_DIR, check=True)
                cmd = "git add . && git commit -m 'Update' && git push"
                subprocess.run(cmd, shell=True, cwd=BASE_DIR, check=True)
                msg = "🌍 GitHub公開完了"
            except Exception as e:
                msg = f"⚠️ エラー: {e}"

    js_plants_json = json.dumps(existing_plants, ensure_ascii=False)

    return f'''
    <!doctype html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>植物管理</title>
        <style>
            body {{ font-family: sans-serif; background: #f4f5f7; padding: 10px; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
            h1, h2 {{ text-align: center; color: #2eaadc; }}
            .msg {{ background: #d4edda; color: #155724; padding: 10px; margin-bottom: 20px; text-align:center; }}
            .section {{ border: 1px solid #eee; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
            
            input, select, textarea {{ width: 100%; padding: 10px; margin-top: 5px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; font-size: 16px; }}
            button {{ width: 100%; padding: 15px; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 16px; margin-top: 10px; }}
            
            .btn-register {{ background: #2eaadc; color: white; }}
            .btn-gallery {{ background: #ff9800; color: white; }}
            .btn-rebuild {{ background: #6c757d; color: white; }}
            .btn-github {{ background: #e83e8c; color: white; }}
            .btn-dl {{ background: #28a745; color: white; text-decoration: none; display: block; text-align: center; padding: 12px; border-radius: 5px; }}
            
            #plant_selector {{ background: #e3f2fd; border: 2px solid #2eaadc; font-weight: bold; color: #0277bd; }}
        </style>
        <script>
            const plants = {js_plants_json};

            function autoFill() {{
                const selector = document.getElementById('plant_selector');
                const selectedID = selector.value;
                
                if (selectedID && plants[selectedID]) {{
                    const p = plants[selectedID];
                    document.getElementById('id_input').value = selectedID;
                    document.getElementById('genus_input').value = p.genus;
                    document.getElementById('species_input').value = p.species;
                    document.getElementById('shop_input').value = p.shop;
                    document.getElementById('price_input').value = p.price;
                    document.getElementById('memo_input').value = p.memo;
                }}
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🛠️ 管理メニュー</h1>
            {f'<div class="msg">{msg}</div>' if msg else ''}

            <div class="section">
                <h2>📱 登録・更新</h2>
                <label>📂 履歴から選ぶ (自動入力)</label>
                <select id="plant_selector" onchange="autoFill()">
                    <option value="">-- タップして選択 --</option>
                    {''.join([f'<option value="{k}">{existing_plants[k]["label"]}</option>' for k in sorted_keys])}
                </select>
                
                <hr style="border:0; border-top:1px dashed #ccc; margin:20px 0;">

                <form method="post" enctype="multipart/form-data">
                    <input type="hidden" name="action" value="register">
                    
                    <div style="background:#f9f9f9; padding:10px; border:2px dashed #ccc; text-align:center;">
                        <label>📸 写真 (追加)</label>
                        <input type="file" name="files" multiple accept="image/*">
                    </div>

                    <label>🆔 ID</label>
                    <input type="text" id="id_input" name="id" placeholder="自動で入力されます" required>

                    <div style="display:flex; gap:10px;">
                        <div style="flex:1;"><label>🌵 属</label><input type="text" id="genus_input" name="genus"></div>
                        <div style="flex:1;"><label>📛 品種名</label><input type="text" id="species_input" name="species"></div>
                    </div>

                    <div style="display:flex; gap:10px;">
                        <div style="flex:1;"><label>🛒 場所</label><input type="text" id="shop_input" name="shop"></div>
                        <div style="flex:1;"><label>💰 価格</label><input type="number" id="price_input" name="price"></div>
                    </div>

                    <label>📝 メモ</label>
                    <textarea id="memo_input" name="memo" rows="2"></textarea>

                    <button type="submit" class="btn-register">保存して更新</button>
                </form>
            </div>

            <div class="section" style="background:#fff3cd; border:1px solid #ffeeba;">
                <h2>🗑️ 写真整理</h2>
                <p style="font-size:0.8em; margin-bottom:5px;">属で絞り込んだり検索できます</p>
                <a href="/admin/gallery" style="text-decoration:none;">
                    <button type="button" class="btn-gallery">📸 写真整理モードへ</button>
                </a>
            </div>

            <div class="section" style="background:#f8f9fa;">
                <h2>その他</h2>
                <a href="/download_csv" class="btn-dl">📥 PC用CSVをダウンロード</a>
                <form method="post"><input type="hidden" name="action" value="rebuild"><button type="submit" class="btn-rebuild">🔄 図鑑(HTML)再構築</button></form>
                <form method="post"><input type="hidden" name="action" value="github_push"><button type="submit" class="btn-github">🌍 GitHubへ公開</button></form>
            </div>

            <p style="text-align:center;"><a href="/">📖 図鑑に戻る</a></p>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)