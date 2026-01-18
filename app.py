import streamlit as st
import yt_dlp
import os
import shutil

# --- 網頁配置 ---
st.set_page_config(page_title="YouTube Pro Web", page_icon="🎵", layout="wide")

st.title("🎵 YouTube Pro 音樂下載器 (Web 版)")
st.info("提示：分析完成後，請勾選要下載的項目，再點擊開始下載。")

# --- 1. 核心初始化 (確保 state 絕對不為 None) ---
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

# --- 3. 分析邏輯 ---
if analyze_btn:
    if not url_input:
        st.warning("請先輸入網址")
    else:
        # 點擊分析時先重置狀態，避免舊數據干擾
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
                    # 抓取資訊
                    info_dict = ydl.extract_info(url_input, download=False)
                    
                    if info_dict is None:
                        st.error("無法取得影片資訊，請檢查網址或稍後再試。")
                    else:
                        # 判定模式並提取清單
                        if 'entries' in info_dict:
                            st.session_state.mode = 'playlist'
                            # 過濾掉可能為 None 的 entry
                            st.session_state.items = [e for e in info_dict['entries'] if e is not None]
                        elif info_dict.get('chapters'):
                            st.session_state.mode = 'chapters'
                            st.session_state.items = list(info_dict['chapters'])
                        else:
                            st.session_state.mode = 'single'
                            # 確保放入的是一個包含單一 dict 的 list
                            st.session_state.items = [info_dict]
                
                if not st.session_state.items:
                    st.warning("分析完成，但未找到任何可下載的曲目。")
                else:
                    st.success(f"分析完成！找到 {len(st.session_state.items)} 個項目")
                    
            except Exception as e:
                st.session_state.items = [] # 發生錯誤時清空
                st.error(f"分析失敗: {str(e)}")

# --- 4. 顯示與選擇區 (加強防禦性判斷) ---
# 只有當 items 是清單且有內容時才執行
current_items = st.session_state.get('items', [])

if isinstance(current_items, list) and len(current_items) > 0:
    st.markdown("---")
    st.subheader("2. 選擇下載項目")
    
    display_options = []
    for i, item in enumerate(current_items, 1):
        # 嘗試抓取標題，若無則顯示序號
        title = "未知曲目"
        if isinstance(item, dict):
            title = item.get('title') or item.get('section_title') or f"項目 {i}"
        display_options.append(f"{i:02d}. {title}")
    
    selected_options = st.multiselect("請勾選項目 (預設為全選):", display_options)
    
    # 決定要下載的索引
    if selected_options:
        target_indices = [int(opt.split('.')[0]) for opt in selected_options]
    else:
        target_indices = list(range(1, len(current_items) + 1))

    # --- 5. 下載區 ---
    if st.button("🚀 開始下載為 MP3", type="primary"):
        dl_folder = "web_downloads"
        if os.path.exists(dl_folder):
            shutil.rmtree(dl_folder)
        os.makedirs(dl_folder)

        with st.status("正在處理下載工作...", expanded=True) as status:
            try:
                base_ydl_opts = {
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
                    base_ydl_opts['playlist_items'] = ",".join(map(str, target_indices))
                    prefix = "%(playlist_index)02d." if add_number else ""
                    base_ydl_opts['outtmpl'] = f'{dl_folder}/{prefix}%(title)s.%(ext)s'
                
                elif st.session_state.mode == 'chapters':
                    idx_pattern = f"^({'|'.join([str(x) for x in target_indices])})$"
                    base_ydl_opts['download_sections'] = f'*{idx_pattern}'
                    prefix = "%(section_number)02d." if add_number else ""
                    base_ydl_opts['outtmpl'] = f'{dl_folder}/{prefix}%(section_title)s.%(ext)s'
                    base_ydl_opts['postprocessors'].insert(0, {'key': 'FFmpegSplitChapters', 'force_keyframes': False})
                
                else: # single video
                    prefix = "01." if add_number else ""
                    base_ydl_opts['outtmpl'] = f'{dl_folder}/{prefix}%(title)s.%(ext)s'

                with yt_dlp.YoutubeDL(base_ydl_opts) as ydl:
                    ydl.download([st.session_state.current_url])
                
                status.update(label="✅ 處理完成！", state="complete")
                
                # 取得結果檔案
                files_found = os.listdir(dl_folder)
                if files_found:
                    st.balloons()
                    st.markdown("### 3. 下載到您的電腦")
                    for filename in files_found:
                        f_path = os.path.join(dl_folder, filename)
                        with open(f_path, "rb") as f_bytes:
                            st.download_button(
                                label=f"💾 點我儲存：{filename}",
                                data=f_bytes,
                                file_name=filename,
                                mime="audio/mp3",
                                key=f"btn_{filename}"
                            )
                else:
                    st.error("下載失敗：找不到生成的 MP3 檔案。")
            except Exception as e:
                st.error(f"下載過程出錯: {e}")
