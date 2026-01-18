import streamlit as st
import yt_dlp
import os
import shutil

# --- 網頁配置 ---
st.set_page_config(page_title="YouTube Pro Web", page_icon="🎵", layout="wide")

st.title("🎵 YouTube Pro 音樂下載器 (Web 版)")
st.info("提示：分析完成後，請勾選要下載的項目，再點擊開始下載。")

# --- 1. 核心初始化 (防禦 TypeError) ---
# 確保這些變數永遠存在，且 items 預設為空清單而非 None
if 'items' not in st.session_state:
    st.session_state.items = []
if 'mode' not in st.session_state:
    st.session_state.mode = None
if 'current_url' not in st.session_state:
    st.session_state.current_url = ""

# --- 2. 輸入區 ---
url_input = st.text_input("貼上 YouTube 網址:", value=st.session_state.current_url, placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns([1, 4])
with col1:
    analyze_btn = st.button("🔍 分析內容", use_container_width=True)
with col2:
    add_number = st.checkbox("檔名加入序號 (01, 02...)", value=True)

# --- 3. 分析邏輯 (解決 method has no len 報錯) ---
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
                        # 判定資料型態並安全賦值
                        if 'entries' in info:
                            st.session_state.mode = 'playlist'
                            # 強制轉為 list 並過濾 None
                            raw_entries = list(info.get('entries', []))
                            st.session_state.items = [e for e in raw_entries if e is not None]
                        elif info.get('chapters'):
                            st.session_state.mode = 'chapters'
                            st.session_state.items = list(info['chapters'])
                        else:
                            st.session_state.mode = 'single'
                            # 將單個 info 包裝成 list 中的 dict
                            st.session_state.items = [dict(info)]
                
                # 使用變數存儲長度，避免直接在判斷式中呼叫可能出錯的屬性
                final_count = len(st.session_state.items)
                if final_count > 0:
                    st.success(f"分析完成！找到 {final_count} 個項目")
                else:
                    st.warning("分析完成，但未找到可下載內容。")
                    
            except Exception as e:
                st.session_state.items = []
                st.error(f"分析失敗: {str(e)}")

# --- 4. 顯示與選擇區 (加強防禦性遍歷) ---
# 再次確認 current_items 是清單
current_items = st.session_state.get('items', [])

if isinstance(current_items, list) and len(current_items) > 0:
    st.markdown("---")
    st.subheader("2. 選擇下載項目")
    
    display_names = []
    for i, item in enumerate(current_items, 1):
        # 確保 item 是字典，並安全取得標題
        title = "未知曲目"
        if isinstance(item, dict):
            title = item.get('title') or item.get('section_title') or f"項目 {i}"
        display_names.append(f"{i:02d}. {title}")
    
    selected_list = st.multiselect("請勾選項目 (不選代表下載全部):", display_names)
    
    # 轉換選中的索引
    if selected_list:
        target_indices = [int(opt.split('.')[0]) for opt in selected_list]
    else:
        target_indices = list(range(1, len(current_items) + 1))

    # --- 5. 下載執行區 ---
    if st.button("🚀 開始下載為 MP3", type="primary"):
        work_dir = "temp_dl_dir"
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(work_dir)

        with st.status("正在處理並轉檔...", expanded=True) as status:
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
                    base_opts['outtmpl'] = f'{work_dir}/{prefix}%(title)s.%(ext)s'
                elif st.session_state.mode == 'chapters':
                    indices_str = "|".join([str(x) for x in target_indices])
                    base_opts['download_sections'] = f'*^({indices_str})$'
                    prefix = "%(section_number)02d." if add_number else ""
                    base_opts['outtmpl'] = f'{work_dir}/{prefix}%(section_title)s.%(ext)s'
                    base_opts['postprocessors'].insert(0, {'key': 'FFmpegSplitChapters', 'force_keyframes': False})
                else:
                    prefix = "01." if add_number else ""
                    base_opts['outtmpl'] = f'{work_dir}/{prefix}%(title)s.%(ext)s'

                with yt_dlp.YoutubeDL(base_opts) as ydl:
                    ydl.download([st.session_state.current_url])
                
                status.update(label="✅ 處理完成！", state="complete")
                
                files = os.listdir(work_dir)
                if files:
                    st.balloons()
                    st.markdown("### 3. 下載到本地裝置")
                    for f in files:
                        p = os.path.join(work_dir, f)
                        with open(p, "rb") as file_bytes:
                            st.download_button(
                                label=f"💾 儲存：{f}",
                                data=file_bytes,
                                file_name=f,
                                mime="audio/mp3",
                                key=f"btn_{f}" # 確保每個按鈕 key 唯一
                            )
                else:
                    st.error("未能產生檔案，請確認網址是否受限。")
            except Exception as e:
                st.error(f"下載失敗: {e}")
