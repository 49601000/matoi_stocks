import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# ページ設定
st.set_page_config(page_title="ニコメ・マトイ統合在庫管理", layout="wide")

st.title("👓 ニコメ・マトイ 在庫管理システム")

# Google Sheetsへの接続設定
# 共有URLをここに貼り付けてください
url = "https://docs.google.com/spreadsheets/d/1hlLDLrqF8lqid7Nml772c6gbG9TXq0demGFWkZg6juE/edit?gid=1661220406#gid=1661220406" 

conn = st.connection("gsheets", type=GSheetsConnection)

# データの読み込み
@st.cache_data(ttl=60) # 60秒ごとにキャッシュ更新
def load_data():
    return conn.read(spreadsheet=url)

df = load_data()

# サイドバー：検索機能
st.sidebar.header("🔍 在庫を検索")
search_id = st.sidebar.text_input("IDで検索")
search_model = st.sidebar.text_input("モデル名で検索")
search_color = st.sidebar.text_input("カラーで検索")
store_filter = st.sidebar.multiselect("店舗絞り込み", options=["ニコメ", "マトイ"], default=["ニコメ", "マトイ"])

# フィルタリングロジック
filtered_df = df.copy()
if search_id:
    filtered_df = filtered_df[filtered_df['ID'].astype(str) == search_id]
if search_model:
    filtered_df = filtered_df[filtered_df['モデル'].str.contains(search_model, case=False, na=False)]
if search_color:
    filtered_df = filtered_df[filtered_df['カラー'].str.contains(search_color, case=False, na=False)]
filtered_df = filtered_df[filtered_df['店舗'].isin(store_filter)]

# タブ分け
tab1, tab2, tab3 = st.tabs(["🔎 検索と更新", "📋 在庫一覧（目視用）", "📊 売り上げ集計"])

with tab1:
    st.subheader("在庫のステータス更新")
    if not filtered_df.empty:
        # 最初の5件を表示（スマホで見やすくするため）
        for index, row in filtered_df.head(10).iterrows():
            with st.container():
                col1, col2, col3, col4 = st.columns([1, 2, 1, 2])
                status = row['売上フラグ'] if pd.notna(row['売上フラグ']) else "在庫あり"
                
                col1.write(f"**ID: {row['ID']}**")
                col2.write(f"{row['ブランド']} / {row['モデル']} ({row['カラー']})")
                col3.write(f"状態: {status}")
                
                # 更新用ボタン
                with col4:
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    if btn_col1.button("〇 売上", key=f"sale_{row['ID']}"):
                        # 更新処理
                        df.at[index, '売上フラグ'] = '〇'
                        df.at[index, '売上年'] = f"{datetime.now().year}年"
                        df.at[index, '売上月'] = datetime.now().month
                        conn.update(spreadsheet=url, data=df)
                        st.success(f"ID:{row['ID']} を売上済に更新しました！")
                        st.rerun()
                    
                    if btn_col2.button("△ ｽﾀｯﾌ", key=f"staff_{row['ID']}"):
                        df.at[index, '売上フラグ'] = '△'
                        conn.update(spreadsheet=url, data=df)
                        st.rerun()
                        
                    if btn_col3.button("× 破棄", key=f"trash_{row['ID']}"):
                        df.at[index, '売上フラグ'] = '×'
                        conn.update(spreadsheet=url, data=df)
                        st.rerun()
            st.divider()
    else:
        st.info("該当する在庫が見つかりません。検索条件を変えてください。")

with tab2:
    st.subheader("現在庫リスト（フラグ空欄のみ）")
    # 売上フラグが空欄（NaNまたは空文字）のものだけ表示
    inventory_only = df[df['売上フラグ'].isna() | (df['売上フラグ'] == "")]
    st.dataframe(inventory_only[['店舗', 'ID', 'ブランド', 'モデル', 'カラー', '上代（税込）']], use_container_width=True)

with tab3:
    st.subheader("ブランド別 売上集計（〇のみ）")
    sales_only = df[df['売上フラグ'] == '〇']
    if not sales_only.empty:
        brand_sales = sales_only.groupby('ブランド')['ID'].count().sort_values(ascending=False)
        st.bar_chart(brand_sales)
        st.write("詳細データ", sales_only[['売上年', '売上月', 'ブランド', 'モデル', '上代（税込）']])
    else:
        st.write("売上データがまだありません。")
