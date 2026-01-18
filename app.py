import streamlit as st
import yt_dlp
import os
import shutil

# --- 網頁配置 ---
st.set_page_config(page_title="YouTube Pro Web", page_icon="🎵", layout="wide")

st.title("🎵 YouTube Pro 音樂下載器 (Web 版)")
st.info("提示：分析完成後，請勾選要下載的項目，再點擊開始下載。")

# --- 1. 確保 Session State 始終正確初始化 ---
# 使用清單 [] 作為預設值，確保 enumerate 永遠不會遇到 None
if 'items' not in st.session_state or st.session_state.items is None:
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
        with st.spinner("正在解析 YouTube 資訊..."):
            try:
                st.session_state.current_url = url_input
                
                ydl_opts = {
                    'quiet': True, 
                    'extract_flat': 'in_playlist', 
                    'ignoreerrors': True, 
                    'no_warnings': True,
                    'nocheckcertificate': True
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url_input, download=False)
                    
                    if info and 'entries' in info:
                        st.session_state.mode = 'playlist'
                        st.session_state.items = [e for e in info['entries'] if e is not None]
                    elif info and info.get('chapters'):
                        st.session_state.mode = 'chapters'
                        st.session_state.items = info['chapters']
                    elif info:
                        st.session_state.mode = 'single'
                        st.session_state.items = [info]
                    else:
                        st.session_state.items = []
                        st.error("無法解析該網址，請確認連結是否正確。")
                
                if st.session_state.items:
                    st.success(f"分析成功！共找到 {len(st.session_state.items)} 個項目")
            except Exception as e:
                st.session_state.items = []
                st.error(f"分析失敗: {str(e)}")

# --- 4. 顯示與選擇區 (使用更嚴格的防禦性寫法) ---
# 只有在 items 確定是 list 且長度大於 0 時才進入
if isinstance(st.session_state.items, list) and len(st.session_state.items) > 0:
    st.markdown("---")
    st.subheader("2. 選擇下載項目")
    
    options = []
    # 建立顯示用的選項名稱
    for i, item in enumerate(st.session_state.items, 1):
        if item:
            title = item.get('title') or item.get('section_title') or f"項目 {i}"
            options.append(f"{i:02d}. {title}")
    
    selected_options = st.multiselect("請勾選項目 (不選代表下載全部):", options)
    
    # 計算索引
    if selected_options:
        indices = [int(opt.split('.')[0]) for opt in selected_options]
    else:
        indices = list(range(1, len(st.session_state.items) + 1))

    # --- 5. 下載執行區 ---
    if st.button("🚀 開始下載為 MP3", type="primary"):
        dl_path = "temp_downloads"
        if os.path.exists(dl_path):
            shutil.rmtree(dl_path)
        os.makedirs(dl_path)

        with st.status("正在下載並轉換格式...", expanded=True) as status:
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'ignoreerrors': True,
                    'prefer_ffmpeg': True,
                }

                if st.session_state.mode == 'playlist':
                    ydl_opts['playlist_items'] = ",".join(map(str, indices))
                    prefix = "%(playlist_index)02d." if add_number else ""
                    ydl_opts['outtmpl'] = f'{dl_path}/{prefix}%(title)s.%(ext)s'
                elif st.session_state.mode == 'chapters':
                    regex_pattern = f"^({'|'.join([str(i) for i in indices])})$"
                    ydl_opts['download_sections'] = f'*{regex_pattern}'
                    prefix = "%(section_number)02d." if add_number else ""
                    ydl_opts['outtmpl'] = f'{dl_path}/{prefix}%(section_title)s.%(ext)s'
                    ydl_opts['postprocessors'].insert(0, {'key': 'FFmpegSplitChapters', 'force_keyframes': False})
                else:
                    prefix = "01." if add_number else ""
                    ydl_opts['outtmpl'] = f'{dl_path}/{prefix}%(title)s.%(ext)s'

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([st.session_state.current_url])
                
                status.update(label="✅ 下載轉換完成！", state="complete")
                st.balloons()
                
                st.markdown("### 3. 點擊下方按鈕儲存到電腦")
                downloaded_files = os.listdir(dl_path)
                if not downloaded_files:
                    st.warning("沒有成功下載任何檔案。")
                else:
                    for f in downloaded_files:
                        file_full_path = os.path.join(dl_path, f)
                        with open(file_full_path, "rb") as file_data:
                            st.download_button(
                                label=f"💾 儲存: {f}",
                                data=file_data,
                                file_name=f,
                                mime="audio/mp3",
                                key=f"dl_{f}" # 確保 key 唯一
                            )
            except Exception as e:
                st.error(f"下載過程中發生錯誤: {str(e)}")
