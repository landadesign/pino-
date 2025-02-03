import streamlit as st
import pandas as pd
from datetime import datetime
import io
from PIL import Image, ImageDraw, ImageFont
import re

# ページ設定
st.set_page_config(page_title="PINO精算アプリケーション", layout="wide")

# 定数
RATE_PER_KM = 15
DAILY_ALLOWANCE = 200

def create_expense_table_image(df, name):
    # 画像サイズとフォント設定
    width = 1200
    row_height = 40
    header_height = 60
    padding = 30
    title_height = 50
    
    # 全行数を計算（タイトル + ヘッダー + データ行 + 合計行 + 注釈）
    total_rows = len(df) + 3
    height = title_height + header_height + (total_rows * row_height) + padding * 2
    
    # 画像作成
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # フォント設定
    font = ImageFont.load_default()
    
    # タイトル描画
    title = f"{name}様 2024年12月25日～2025年1月 社内通貨（交通費）清算額"
    draw.text((padding, padding), title, fill='black', font=font)
    
    # ヘッダー
    headers = ['日付', '経路', '合計距離(km)', '交通費（距離×15P）(円)', '運転手当(円)', '合計(円)']
    x_positions = [padding, padding + 80, padding + 600, padding + 750, padding + 900, padding + 1050]
    
    y = padding + title_height
    for header, x in zip(headers, x_positions):
        draw.text((x, y), header, fill='black', font=font)
    
    # 罫線
    line_y = y + header_height - 5
    draw.line([(padding, line_y), (width - padding, line_y)], fill='black', width=1)
    
    # データ行
    y = padding + title_height + header_height
    for _, row in df.iterrows():
        for route in row['routes']:
            # 日付
            draw.text((x_positions[0], y), str(row['date']), fill='black', font=font)
            
            # 経路
            draw.text((x_positions[1], y), route['route'], fill='black', font=font)
            
            # 最初のルートの行にのみ数値を表示
            if route == row['routes'][0]:
                # 距離
                draw.text((x_positions[2], y), f"{row['total_distance']:.1f}", fill='black', font=font)
                
                # 交通費
                draw.text((x_positions[3], y), f"{int(row['transportation_fee']):,}", fill='black', font=font)
                
                # 運転手当
                draw.text((x_positions[4], y), f"{int(row['allowance']):,}", fill='black', font=font)
                
                # 合計
                draw.text((x_positions[5], y), f"{int(row['total']):,}", fill='black', font=font)
            
            y += row_height
    
    # 合計行の罫線
    line_y = y - 5
    draw.line([(padding, line_y), (width - padding, line_y)], fill='black', width=1)
    
    # 合計行
    y += 10
    draw.text((x_positions[0], y), "合計", fill='black', font=font)
    draw.text((x_positions[5], y), f"{int(df['total'].sum()):,}", fill='black', font=font)
    
    # 注釈
    y += row_height * 2
    draw.text((padding, y), "※2025年1月分給与にて清算しました。", fill='black', font=font)
    
    # 計算日時
    draw.text((padding, y + row_height), f"計算日時: {datetime.now().strftime('%Y/%m/%d')}", fill='black', font=font)
    
    # 画像をバイト列に変換
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    return img_byte_arr

def parse_expense_data(text):
    try:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        data = []
        current_name = None
        daily_routes = {}
        
        for line in lines:
            if '【ピノ】' in line:
                match = re.match(r'【ピノ】\s*([^\s]+)\s+(\d+/\d+)\s*\([月火水木金土日]\)', line)
                if match:
                    name, date = match.groups()
                    route_start = line.index(')') + 1
                    route_end = line.find('km')
                    if route_end == -1:
                        route_end = line.find('㎞')
                    route = line[route_start:route_end].strip()
                    
                    # 距離を抽出
                    distance_match = re.search(r'(\d+\.?\d*)', line[route_end-5:route_end+5])
                    if distance_match:
                        distance = float(distance_match.group(1))
                        
                        if name not in daily_routes:
                            daily_routes[name] = {}
                        if date not in daily_routes[name]:
                            daily_routes[name][date] = []
                            
                        daily_routes[name][date].append({
                            'route': route,
                            'distance': distance
                        })
        
        # 日付ごとのデータを集計
        for name, dates in daily_routes.items():
            for date, routes in dates.items():
                total_distance = sum(route['distance'] for route in routes)
                transportation_fee = int(total_distance * RATE_PER_KM)  # 切り捨て
                data.append({
                    'name': name,
                    'date': date,
                    'routes': routes,
                    'total_distance': total_distance,
                    'transportation_fee': transportation_fee,
                    'allowance': DAILY_ALLOWANCE,
                    'total': transportation_fee + DAILY_ALLOWANCE
                })
        
        if data:
            df = pd.DataFrame(data)
            return df.sort_values(['name', 'date'])  # 日付順にソート
        
        st.error("データが見つかりませんでした。正しい形式で入力してください。")
        return None
        
    except Exception as e:
        st.error(f"エラーが発生しました: {str(e)}")
        return None

def main():
    st.title("PINO精算アプリケーション")
    
    # データ入力
    input_text = st.text_area("精算データを貼り付けてください", height=200)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        analyze_button = st.button("データを解析")
    with col2:
        if 'expense_data' in st.session_state:
            clear_button = st.button("クリア")
            if clear_button:
                del st.session_state['expense_data']
                st.experimental_rerun()
    
    if analyze_button and input_text:
        df = parse_expense_data(input_text)
        if df is not None:
            st.session_state['expense_data'] = df
            st.success("データを解析しました！")
    
    # データ表示と精算書生成
    if 'expense_data' in st.session_state:
        df = st.session_state['expense_data']
        unique_names = df['name'].unique().tolist()
        
        # 個人別タブの作成
        tabs = st.tabs(unique_names)
        
        for i, name in enumerate(unique_names):
            with tabs[i]:
                person_data = df[df['name'] == name].copy()
                
                # タイトル表示
                st.markdown(f"### {name}様 2024年12月25日～2025年1月 社内通貨（交通費）清算額")
                
                # データ表示用のリストを作成
                display_rows = []
                for _, row in person_data.iterrows():
                    for route in row['routes']:
                        display_rows.append({
                            '日付': row['date'],
                            '経路': route['route'],
                            '合計距離(km)': row['total_distance'] if route == row['routes'][0] else '',
                            '交通費（距離×15P）(円)': row['transportation_fee'] if route == row['routes'][0] else '',
                            '運転手当(円)': row['allowance'] if route == row['routes'][0] else '',
                            '合計(円)': row['total'] if route == row['routes'][0] else ''
                        })
                
                # DataFrameの作成と表示
                display_df = pd.DataFrame(display_rows)
                
                # 合計行の追加
                totals = pd.DataFrame([{
                    '日付': '合計',
                    '経路': '',
                    '合計距離(km)': '',
                    '交通費（距離×15P）(円)': '',
                    '運転手当(円)': '',
                    '合計(円)': person_data['total'].sum()
                }])
                display_df = pd.concat([display_df, totals])
                
                # データフレーム表示
                st.dataframe(
                    display_df.style.format({
                        '合計距離(km)': lambda x: f'{float(x):.1f}' if x != '' else '',
                        '交通費（距離×15P）(円)': lambda x: f'{int(x):,}' if x != '' else '',
                        '運転手当(円)': lambda x: f'{int(x):,}' if x != '' else '',
                        '合計(円)': lambda x: f'{int(x):,}' if x != '' else ''
                    }),
                    use_container_width=True,
                    hide_index=True
                )
                
                # 注釈表示
                st.markdown("※2025年1月分給与にて清算しました。")
                st.markdown(f"計算日時: {datetime.now().strftime('%Y/%m/%d')}")
                
                # 画像生成とダウンロードボタン
                img_bytes = create_expense_table_image(person_data, name)
                st.download_button(
                    label="精算書をダウンロード",
                    data=img_bytes,
                    file_name=f"精算書_{name}_{datetime.now().strftime('%Y%m%d')}.png",
                    mime="image/png"
                )

if __name__ == "__main__":
    main()
