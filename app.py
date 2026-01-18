import streamlit as st
import yt_dlp
import os
import shutil

# --- 網頁配置 ---
st.set_page_config(page_title="YouTube Pro Web", page_icon="🎵", layout="wide")

st.title("🎵 YouTube Pro 音樂下載器 (Web 版)")
st.info("提示：分析完成後，請勾選要下載的項目，再點擊開始下載。")

# --- 1. 確保 Session State 始終存在且不為 None ---
# 這是為了解決截圖中的 enumerate 報錯
if 'items' not in st.session_state or st.session_state.items is None:
    st.session_state.items = []
if 'mode' not in st.session_state:
    st.session_state.mode = None
if 'current_url' not in st.session_state:
    st.session_state.current_url = ""

# --- 2. 輸入區 ---
url_input = st.text_input("貼上 YouTube 網址:", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns([1, 4])
with col1:
    analyze_btn = st.button("🔍 分析內容", use_container_width=True)
with col2:
    add_number = st.checkbox("檔名加入序號 (01, 02...)", value=True)

# --- 3. 分析邏輯 (徹底解決 method has no len 報錯) ---
if analyze_btn:
    if not url_input:
        st.warning("請先輸入網址")
    else:
        # 重置狀態
        st.session_state.items = []
        st.session_state.current_url = url_input
        
        with st.spinner("正在解析 YouTube 資訊..."):
            try:
                ydl_opts = {
                    'quiet': True, 
                    'extract_flat': 'in_playlist', 
                    'ignoreerrors': True, 
                    'no_warnings': True,
                    'nocheckcertificate': True
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # 抓取原始資料
                    info = ydl.extract_info(url_input, download=False)
                    
                    if info is None:
                        st.error("無法抓取資訊，請檢查網址或稍後再試。")
                    else:
                        # 邏輯分流：播放清單 -> 影片章節 -> 單影片
                        if 'entries' in info:
                            st.session_state.mode = 'playlist'
                            # 確保 entries 是 list 並過濾 None
                            entries = list(info.get('entries', []))
                            st.session_state.items = [e for e in entries if e is not None]
                        elif info.get('chapters'):
                            st.session_state.mode = 'chapters'
                            st.session_state.items = list(info['chapters'])
                        else:
                            st.session_state.mode = 'single'
                            # 建立一個單元素的清單，避免後續遍歷報錯
                            st.session_state.items = [dict(info)]
                
                # 再次確認是否有抓到東西
                item_count = len(st.session_state.items)
                if item_count > 0:
                    st.success(f"分析完成！找到 {item_count} 個項目")
                else:
                    st.warning("分析完成，但未找到可下載的內容。")
                    
            except Exception as e:
                st.session_state.items = []
                st.error(f"分析失敗: {str(e)}")

# --- 4. 顯示與選擇區 (防禦性遍歷) ---
# 確保 current_items 是一個可以被 enumerate 的 list
current_items = st.session_state.get('items', [])

if isinstance(current_items, list) and len(current_items) > 0:
    st.markdown("---")
    st.subheader("2. 選擇下載項目")
    
    # 建立顯示用的選項
    display_list = []
    for i, item in enumerate(current_items, 1):
        if isinstance(item, dict):
            # 優先嘗試不同的標題 key
            t = item.get('title') or item.get('section_title') or f"項目 {i}"
            display_list.append(f"{i:02d}. {t}")
        else:
            display_list.append(f"{i:02d}. 未知曲目")
    
    selected_options = st.multiselect("請勾選項目 (預設為全選):", display_list)
    
    # 提取選中的索引
    if selected_options:
        target_indices = [int(opt.split('.')[0]) for opt in selected_options]
    else:
        target_indices = list(range(1, len(current_items) + 1))

    # --- 5. 下載執行區 ---
    if st.button("🚀 開始下載為 MP3", type="primary"):
        temp_dir = "downloads_workdir"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        with st.status("正在處理並轉換檔案...", expanded=True) as status:
            try:
                base_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'ignoreerrors': True,
                    'nocheckcertificate': True,
                }

                if st.session_state.mode == 'playlist':
                    base_opts['playlist_items'] = ",".join(map(str, target_indices))
                    prefix = "%(playlist_index)02d." if add_number else ""
                    base_opts['outtmpl'] = f'{temp_dir}/{prefix}%(title)s.%(ext)s'
                elif st.session_state.mode == 'chapters':
                    indices_str = "|".join([str(x) for x in target_indices])
                    base_opts['download_sections'] = f'*^({indices_str})$'
                    prefix = "%(section_number)02d." if add_number else ""
                    base_opts['outtmpl'] = f'{temp_dir}/{prefix}%(section_title)s.%(ext)s'
                    base_opts['postprocessors'].insert(0, {'key': 'FFmpegSplitChapters', 'force_keyframes': False})
                else:
                    prefix = "01." if add_number else ""
                    base_opts['outtmpl'] = f'{temp_dir}/{prefix}%(title)s.%(ext)s'

                with yt_dlp.YoutubeDL(base_opts) as ydl:
                    ydl.download([st.session_state.current_url])
                
                status.update(label="✅ 下載完成！", state="complete")
                
                # 生成下載按鈕
                result_files = os.listdir(temp_dir)
                if result_files:
                    st.balloons()
                    st.markdown("### 3. 下載到本地裝置")
                    for fname in result_files:
                        full_p = os.path.join(temp_dir, fname)
                        with open(full_p, "rb") as fb:
                            st.download_button(
                                label=f"💾 儲存：{fname}",
                                data=fb,
                                file_name=fname,
                                mime="audio/mp3",
                                key=f"dl_btn_{fname}" # 唯一金鑰
                            )
                else:
                    st.error("未能產生 MP3 檔案，請檢查影片是否有地區限制。")
            except Exception as e:
                st.error(f"下載失敗: {e}")
