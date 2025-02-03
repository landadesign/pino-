import streamlit as st
import pandas as pd
from datetime import datetime
import io
from PIL import Image, ImageDraw, ImageFont
import re
import plotly.graph_objects as go

# ページ設定を最初に行う
st.set_page_config(layout="wide")

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
        # テキストの前処理
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        data = []
        daily_routes = {}
        
        # 各行を解析
        for line in lines:
            # 【ピノ】形式のデータを解析
            if '【ピノ】' in line:
                # パターン: 【ピノ】名前 日付(曜日) 経路 距離
                pino_match = re.match(r'【ピノ】\s*([^\s]+)\s+(\d+/\d+)\s*\(.\)\s*(.+?)(?:\s+(\d+\.?\d*)(?:km|㎞|ｋｍ|kｍ))?$', line)
                if pino_match:
                    name = pino_match.group(1).replace('様', '')
                    date = pino_match.group(2)
                    route = pino_match.group(3).strip()
                    distance_str = pino_match.group(4)
                    
                    # 距離の取得
                    if distance_str:
                        distance = float(distance_str)
                    else:
                        # 経路からポイント数を計算（デフォルトの場合）
                        route_points = route.split('→')
                        distance = (len(route_points) - 1) * 5.0
                    
                    if name not in daily_routes:
                        daily_routes[name] = {}
                    if date not in daily_routes[name]:
                        daily_routes[name][date] = []
                    
                    # 重複チェック
                    route_exists = False
                    for existing_route in daily_routes[name][date]:
                        if existing_route['route'] == route:
                            route_exists = True
                            break
                    
                    if not route_exists:
                        daily_routes[name][date].append({
                            'route': route,
                            'distance': distance
                        })
        
        # 日付ごとのデータを集計
        for name, dates in daily_routes.items():
            for date, routes in sorted(dates.items(), key=lambda x: tuple(map(int, x[0].split('/')))):
                # 同じ日の距離を合算
                total_distance = sum(route['distance'] for route in routes)
                transportation_fee = int(total_distance * RATE_PER_KM)  # 切り捨て
                
                data.append({
                    'name': name,
                    'date': date,
                    'routes': routes,
                    'total_distance': total_distance,
                    'transportation_fee': transportation_fee,
                    'allowance': DAILY_ALLOWANCE,  # 1日1回のみ
                    'total': transportation_fee + DAILY_ALLOWANCE
                })
        
        if data:
            # データをDataFrameに変換
            df = pd.DataFrame(data)
            
            # 日付でソート
            df['date_sort'] = df['date'].apply(lambda x: tuple(map(int, x.split('/'))))
            df = df.sort_values(['name', 'date_sort'])
            df = df.drop('date_sort', axis=1)
            
            return df
        
        st.error("データが見つかりませんでした。正しい形式で入力してください。")
        return None
        
    except Exception as e:
        st.error(f"エラーが発生しました: {str(e)}")
        return None

def main():
    st.title("PINO精算アプリケーション")
    
    # データ入力
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ''
    
    input_text = st.text_area("精算データを貼り付けてください", 
                             value=st.session_state.input_text,
                             height=200)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        analyze_button = st.button("データを解析")
    with col2:
        if 'expense_data' in st.session_state:
            clear_button = st.button("クリア")
            if clear_button:
                st.session_state.clear()
                st.session_state.input_text = ''
                st.rerun()
    
    if analyze_button and input_text:
        st.session_state.input_text = input_text
        df = parse_expense_data(input_text)
        if df is not None:
            st.session_state['expense_data'] = df
            st.success("データを解析しました！")
    
    # データ表示と精算書生成
    if 'expense_data' in st.session_state:
        df = st.session_state['expense_data']
        
        # 全体の解析一覧を表示
        st.markdown("### 交通費データ一覧")
        
        # 一覧表示用のデータを作成
        list_data = []
        for _, row in df.iterrows():
            for route in row['routes']:
                list_data.append({
                    '日付': row['date'],
                    '担当者': row['name'],
                    '経路': route['route'],
                    '距離(km)': route['distance']
                })
        
        # DataFrameを作成し、日付でソート
        list_df = pd.DataFrame(list_data)
        
        # 日付を数値化してソート
        def date_to_sortable(date_str):
            month, day = map(int, date_str.split('/'))
            return month * 100 + day
            
        list_df['sort_date'] = list_df['日付'].apply(date_to_sortable)
        list_df = list_df.sort_values('sort_date', ascending=True)
        list_df = list_df.drop('sort_date', axis=1)
        
        # カラム幅の設定
        column_config = {
            '日付': st.column_config.TextColumn(width='small'),
            '担当者': st.column_config.TextColumn(width='small'),
            '経路': st.column_config.TextColumn(width='large'),
            '距離(km)': st.column_config.NumberColumn(
                width='small',
                format="%.1f",
                help="移動距離"
            )
        }
        
        # データフレーム表示
        st.dataframe(
            list_df.fillna(''),  # Noneを空文字に置換
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )
        
        # 精算書作成ボタン
        if st.button("精算書を作成"):
            st.session_state['show_expense_report'] = True
        
        # 精算書の表示
        if st.session_state.get('show_expense_report', False):
            st.markdown("""
                <h3 style='margin-bottom: 20px; padding: 10px; background-color: #f0f2f6; border-radius: 5px;'>
                    担当者別精算書
                </h3>
            """, unsafe_allow_html=True)
            
            unique_names = df['name'].unique().tolist()
            tabs = st.tabs(unique_names)
            
            # 精算書用のカラム設定
            expense_column_config = {
                '日付': st.column_config.Column(
                    width=100,
                    help="日付"
                ),
                '経路': st.column_config.Column(
                    width=520,
                    help="移動経路"
                ),
                '合計\n距離\n(km)': st.column_config.NumberColumn(
                    width=110,
                    format="%.1f",
                    help="移動距離の合計"
                ),
                '交通費\n(距離×15P)\n(円)': st.column_config.Column(
                    width=160,
                    help="距離×15円"
                ),
                '運転\n手当\n(円)': st.column_config.Column(
                    width=110,
                    help="運転手当"
                ),
                '合計\n(円)': st.column_config.Column(
                    width=120,
                    help="交通費と手当の合計"
                )
            }
            
            for i, name in enumerate(unique_names):
                with tabs[i]:
                    person_data = df[df['name'] == name].copy()
                    
                    # タイトル表示
                    title_text = f"{name}様　2025年1月　交通費清算額"
                    st.markdown(f"""
                        <h4 style='margin: 20px 0; color: #333;'>
                            {title_text}
                        </h4>
                    """, unsafe_allow_html=True)
                    
                    # データ表示用のリストを作成
                    display_rows = []
                    
                    for _, row in person_data.iterrows():
                        routes = row['routes']
                        
                        for idx, route in enumerate(routes):
                            # 経路を2段に分割
                            route_text = route['route']
                            if len(route_text) > 35:
                                parts = route_text.split('→')
                                new_text = []
                                current_line = ''
                                
                                for i, part in enumerate(parts):
                                    if i > 0:
                                        if len(current_line) + len(part) + 1 > 35:
                                            new_text.append(current_line.strip())
                                            current_line = '→' + part
                                        else:
                                            current_line += '→' + part
                                    else:
                                        current_line = part
                                
                                if current_line:
                                    new_text.append(current_line.strip())
                                    route_text = '\n'.join(new_text)
                            
                            # 同じ日に2件以上ある場合、距離の内訳を表示
                            if len(routes) > 1:
                                if idx == len(routes) - 1:  # 最後の経路の場合
                                    distances = [f"{r['distance']:.1f}" for r in routes]
                                    route_text = f"{route_text} ({' + '.join(distances)} = {row['total_distance']:.1f}km)"
                                else:
                                    route_text = f"{route_text} ({route['distance']:.1f}km)"
                            
                            # 数値データを準備（最初の経路のみ値を設定）
                            if idx == 0:
                                distance = row['total_distance']
                                trans_fee = f"{int(row['transportation_fee']):>8,}"
                                allowance = f"{int(row['allowance']):>6,}"
                                total = f"{int(row['total']):>6,}"
                            else:
                                distance = ""
                                trans_fee = ""
                                allowance = ""
                                total = ""
                            
                            row_data = {
                                '日付': row['date'],
                                '経路': route_text,
                                '合計\n距離\n(km)': distance,
                                '交通費\n(距離×15P)\n(円)': trans_fee,
                                '運転\n手当\n(円)': allowance,
                                '合計\n(円)': total
                            }
                            display_rows.append(row_data)
                    
                    # DataFrameの作成
                    display_df = pd.DataFrame(display_rows)
                    
                    # 合計を計算
                    total_distance = person_data['total_distance'].sum()
                    total_transportation = f"{int(person_data['transportation_fee'].sum()):>8,}"
                    total_allowance = f"{int(person_data['allowance'].sum()):>6,}"
                    total_amount = f"{int(person_data['total'].sum()):>6,}"
                    
                    # 合計行の追加
                    totals = pd.DataFrame([{
                        '日付': '合計',
                        '経路': '',
                        '合計\n距離\n(km)': total_distance,
                        '交通費\n(距離×15P)\n(円)': total_transportation,
                        '運転\n手当\n(円)': total_allowance,
                        '合計\n(円)': total_amount
                    }])
                    
                    # DataFrameを結合
                    display_df = pd.concat([display_df, totals])
                    
                    # Noneと空文字の処理
                    display_df = display_df.fillna('')
                    
                    # テーブルをPlotlyで作成（画像保存用）
                    fig = go.Figure(data=[go.Table(
                        header=dict(
                            values=list(display_df.columns),
                            align=['center'] * len(display_df.columns),
                            font=dict(size=12),
                            height=40
                        ),
                        cells=dict(
                            values=[display_df[col] for col in display_df.columns],
                            align=['center' if col != '経路' else 'left' for col in display_df.columns],
                            font=dict(size=11),
                            height=30
                        )
                    )])
                    
                    # レイアウトの設定
                    fig.update_layout(
                        title=title_text,
                        title_font=dict(size=16),
                        width=1100,
                        height=len(display_df) * 40 + 150,
                        margin=dict(t=80, b=20, l=20, r=20)
                    )
                    
                    # 通常のデータフレーム表示
                    st.dataframe(
                        display_df,
                        column_config=expense_column_config,
                        use_container_width=False,
                        hide_index=True
                    )
                    
                    # 注釈表示
                    st.markdown("""
                        <div style='margin-top: 15px; color: #666;'>
                            ※2025年1月分給与にて清算しました。
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # 画像保存ボタン
                    if st.button('精算書を画像として保存', key=f'save_image_{name}'):
                        # 画像として保存
                        img_bytes = fig.to_image(format="png", scale=2)
                        
                        # ダウンロードボタンを表示
                        st.download_button(
                            label="画像をダウンロード",
                            data=img_bytes,
                            file_name=f"{name}様_交通費精算書_2025年1月.png",
                            mime="image/png"
                        )

if __name__ == "__main__":
    main()
