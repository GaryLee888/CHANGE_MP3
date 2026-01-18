import streamlit as st
import yt_dlp
import os
import re

# 網頁基本設定
st.set_page_config(page_title="YouTube Pro Web 下載器", page_icon="🎵", layout="wide")

st.title("🎵 YouTube Pro 音樂下載器 (Web 版)")
st.markdown("---")

# 初始化 Session State (用於存儲分析結果)
if 'info' not in st.session_state:
    st.session_state.info = None
if 'items' not in st.session_state:
    st.session_state.items = []

# --- 1. 輸入區 ---
url = st.text_input("貼上 YouTube 網址 (支援單影片、播放清單、章節影片)", "")

col1, col2 = st.columns([1, 4])
with col1:
    analyze_btn = st.button("🔍 分析內容", use_container_width=True)
with col2:
    add_number = st.checkbox("檔名加入序號 (01, 02...)", value=True)

# --- 2. 分析邏輯 ---
if analyze_btn:
    if not url:
        st.warning("請輸入網址")
    else:
        with st.spinner("正在讀取 YouTube 資訊..."):
            try:
                ydl_opts = {'quiet': True, 'extract_flat': 'in_playlist', 'ignoreerrors': True, 'no_warnings': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    st.session_state.info = info
                    
                    if 'entries' in info:
                        st.session_state.mode = 'playlist'
                        st.session_state.items = [e for e in info['entries'] if e is not None]
                    elif info.get('chapters'):
                        st.session_state.mode = 'chapters'
                        st.session_state.items = info['chapters']
                    else:
                        st.session_state.mode = 'single'
                        st.session_state.items = [info]
                st.success("分析完成！")
            except Exception as e:
                st.error(f"分析失敗: {str(e)}")

# --- 3. 顯示與選擇區 ---
if st.session_state.items:
    st.subheader("選擇下載項目")
    
    # 建立選項清單
    options = []
    for i, item in enumerate(st.session_state.items, 1):
        title = item.get('title') or item.get('section_title') or "未知標題"
        options.append(f"{i:02d}. {title}")
    
    selected_options = st.multiselect("可多選 (留空代表下載全部):", options)
    
    # 轉換選中的索引
    if selected_options:
        indices = [int(opt.split('.')[0]) for opt in selected_options]
    else:
        indices = list(range(1, len(st.session_state.items) + 1))

    # --- 4. 下載執行區 ---
    if st.button("🚀 開始下載為 MP3", type="primary"):
        with st.status("準備下載中...", expanded=True) as status:
            try:
                # 建立臨時資料夾
                if not os.path.exists("downloads"):
                    os.makedirs("downloads")
                
                output_file = "downloaded_audio.mp3" # 預設單檔名
                
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                    'outtmpl': f'downloads/%(title)s.%(ext)s',
                    'ignoreerrors': True,
                }

                if st.session_state.mode == 'playlist':
                    ydl_opts['playlist_items'] = ",".join(map(str, indices))
                    prefix = "%(playlist_index)02d." if add_number else ""
                    ydl_opts['outtmpl'] = f'downloads/{prefix}%(title)s.%(ext)s'
                
                elif st.session_state.mode == 'chapters':
                    regex_pattern = f"^({'|'.join([str(i) for i in indices])})$"
                    ydl_opts['download_sections'] = f'*{regex_pattern}'
                    prefix = "%(section_number)02d." if add_number else ""
                    ydl_opts['outtmpl'] = f'downloads/{prefix}%(section_title)s.%(ext)s'
                    ydl_opts['postprocessors'].insert(0, {'key': 'FFmpegSplitChapters', 'force_keyframes': False})

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                status.update(label="下載成功！請點擊下方按鈕存擋", state="complete")
                
                # 取得下載後的檔案列表
                files = os.listdir("downloads")
                if files:
                    for f in files:
                        with open(f"downloads/{f}", "rb") as file:
                            st.download_button(label=f"💾 下載 {f}", data=file, file_name=f, mime="audio/mp3")
                        # 清理檔案 (選用)
                        # os.remove(f"downloads/{f}")
                
            except Exception as e:
                st.error(f"下載失敗: {str(e)}")