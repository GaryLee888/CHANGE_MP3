import streamlit as st
import yt_dlp
import os
import shutil
import zipfile
from io import BytesIO

# --- 網頁配置 ---
st.set_page_config(page_title="YouTube Pro Web (穩定修復版)", page_icon="🎵", layout="wide")

st.title("🎵 YouTube Pro 音樂下載器 (穩定版)")

# --- 側邊欄工具 ---
st.sidebar.title("🛠 系統工具")
if st.sidebar.button("🧹 強制重置 Session"):
    st.session_state.clear()
    st.rerun()

# --- 1. 核心初始化 (更名避開 method 衝突) ---
if 'entry_list' not in st.session_state:
    st.session_state.entry_list = []
if 'app_mode' not in st.session_state:
    st.session_state.app_mode = None
if 'active_url' not in st.session_state:
    st.session_state.active_url = ""

# --- 2. 輸入區 ---
url_input = st.text_input("貼上 YouTube 網址:", value=st.session_state.active_url)

col1, col2 = st.columns([1, 4])
with col1:
    analyze_btn = st.button("🔍 分析內容", use_container_width=True)
with col2:
    add_number = st.checkbox("檔名加入序號 (01, 02...)", value=True)

# --- 3. 分析邏輯 ---
if analyze_btn:
    if not url_input:
        st.warning("請輸入網址")
    else:
        st.session_state.entry_list = [] # 確保重置為 list
        st.session_state.active_url = url_input
        
        with st.spinner("正在解析 YouTube 資訊..."):
            try:
                ydl_opts = {
                    'quiet': True, 
                    'extract_flat': 'in_playlist', 
                    'ignoreerrors': True, 
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url_input, download=False)
                    if info:
                        if 'entries' in info:
                            st.session_state.app_mode = 'playlist'
                            # 強制轉為 list
                            st.session_state.entry_list = [e for e in list(info.get('entries', [])) if e is not None]
                        elif info.get('chapters'):
                            st.session_state.app_mode = 'chapters'
                            st.session_state.entry_list = list(info['chapters'])
                        else:
                            st.session_state.app_mode = 'single'
                            st.session_state.entry_list = [dict(info)]
                
                if st.session_state.entry_list:
                    st.success(f"分析完成！找到 {len(st.session_state.entry_list)} 個項目")
                else:
                    st.error("分析失敗：未找到有效內容。")
            except Exception as e:
                st.error(f"分析發生嚴重錯誤: {str(e)}")

# --- 4. 顯示與選擇區 ---
if isinstance(st.session_state.entry_list, list) and len(st.session_state.entry_list) > 0:
    st.divider()
    st.subheader("2. 選擇下載項目")
    
    display_options = []
    for i, item in enumerate(st.session_state.entry_list, 1):
        title = item.get('title') or item.get('section_title') or f"項目 {i}"
        display_options.append(f"{i:02d}. {title}")
    
    selected = st.multiselect("勾選項目 (不選代表下載全部):", display_options)
    
    indices = [int(opt.split('.')[0]) for opt in selected] if selected else list(range(1, len(st.session_state.entry_list) + 1))

    # --- 5. 下載執行區 ---
    if st.button("🚀 開始下載並轉檔為 MP3", type="primary"):
        save_dir = "web_out"
        if os.path.exists(save_dir): shutil.rmtree(save_dir)
        os.makedirs(save_dir)

        with st.status("正在下載轉換中...", expanded=True) as status:
            try:
                dl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
                    'ignoreerrors': True,
                    'nocheckcertificate': True,
                }

                if st.session_state.app_mode == 'playlist':
                    dl_opts['playlist_items'] = ",".join(map(str, indices))
                    prefix = "%(playlist_index)02d." if add_number else ""
                    dl_opts['outtmpl'] = f'{save_dir}/{prefix}%(title)s.%(ext)s'
                elif st.session_state.app_mode == 'chapters':
                    idx_str = "|".join([str(x) for x in indices])
                    dl_opts['download_sections'] = f'*^({idx_str})$'
                    prefix = "%(section_number)02d." if add_number else ""
                    dl_opts['outtmpl'] = f'{save_dir}/{prefix}%(section_title)s.%(ext)s'
                    dl_opts['postprocessors'].insert(0, {'key': 'FFmpegSplitChapters', 'force_keyframes': False})
                else:
                    dl_opts['outtmpl'] = f'{save_dir}/%(title)s.%(ext)s'

                with yt_dlp.YoutubeDL(dl_opts) as ydl:
                    ydl.download([st.session_state.active_url])
                
                res_files = os.listdir(save_dir)
                if res_files:
                    status.update(label="✅ 轉檔完成！", state="complete")
                    st.balloons()
                    
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for fn in res_files:
                            zf.write(os.path.join(save_dir, fn), fn)
                    
                    st.download_button(
                        label="🎁 下載全部項目 (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name="youtube_music.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                else:
                    status.update(label="❌ 下載失敗", state="error")
                    st.error("未能產生檔案。原因可能是：影片受版權保護、地區限制，或 YouTube 封鎖了伺服器 IP。")
            except Exception as e:
                st.error(f"下載過程出錯: {e}")
