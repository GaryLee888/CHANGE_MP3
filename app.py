import streamlit as st
import yt_dlp
import os
import shutil

# --- 網頁配置 ---
st.set_page_config(page_title="YouTube Pro Web (穩定修復版)", page_icon="🎵", layout="wide")

st.title("🎵 YouTube Pro 音樂下載器 (穩定版)")

# --- 側邊欄工具 ---
st.sidebar.title("🛠 系統工具")
debug_mode = st.sidebar.checkbox("開啟偵錯顯示", value=False)
if st.sidebar.button("🧹 強制清空暫存"):
    st.session_state.clear()
    st.rerun()

# --- 1. 核心初始化 (使用新變數名避開衝突) ---
if 'download_list' not in st.session_state:
    st.session_state.download_list = []
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

# --- 3. 分析邏輯 (強化型別判定) ---
if analyze_btn:
    if not url_input:
        st.warning("請輸入網址")
    else:
        # 重置清單
        st.session_state.download_list = []
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
                        # 處理播放清單
                        if 'entries' in info:
                            st.session_state.app_mode = 'playlist'
                            # 關鍵：強制轉換為 list 確保不是 method
                            entries_data = list(info.get('entries', []))
                            st.session_state.download_list = [e for e in entries_data if e is not None]
                        # 處理章節
                        elif info.get('chapters'):
                            st.session_state.app_mode = 'chapters'
                            st.session_state.download_list = list(info['chapters'])
                        # 處理單影片
                        else:
                            st.session_state.app_mode = 'single'
                            st.session_state.download_list = [dict(info)]
                    
                st.success(f"分析完成！找到 {len(st.session_state.download_list)} 個項目")
            except Exception as e:
                st.error(f"分析失敗: {str(e)}")

# --- 4. 偵錯面板 ---
if debug_mode:
    with st.expander("🐞 偵錯資料結構", expanded=True):
        st.write(f"目前模式: {st.session_state.app_mode}")
        st.write(f"列表型別: {type(st.session_state.download_list)}")
        st.json(st.session_state.download_list[:2]) # 只顯示前兩筆避免卡頓

# --- 5. 顯示與選擇區 ---
if isinstance(st.session_state.download_list, list) and len(st.session_state.download_list) > 0:
    st.divider()
    st.subheader("2. 選擇下載項目")
    
    display_options = []
    for i, item in enumerate(st.session_state.download_list, 1):
        title = "未知曲目"
        if isinstance(item, dict):
            title = item.get('title') or item.get('section_title') or f"項目 {i}"
        display_options.append(f"{i:02d}. {title}")
    
    selected = st.multiselect("勾選項目 (不選代表全下):", display_options)
    
    if selected:
        indices = [int(opt.split('.')[0]) for opt in selected]
    else:
        indices = list(range(1, len(st.session_state.download_list) + 1))

    # --- 6. 下載區 ---
    if st.button("🚀 開始下載 MP3", type="primary"):
        save_dir = "web_out"
        if os.path.exists(save_dir): shutil.rmtree(save_dir)
        os.makedirs(save_dir)

        with st.status("轉檔中...", expanded=True) as status:
            try:
                dl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
                    'ignoreerrors': True,
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
                
                status.update(label="✅ 下載完成！", state="complete")
                
                res_files = os.listdir(save_dir)
                if res_files:
                    st.balloons()
                    for fn in res_files:
                        with open(os.path.join(save_dir, fn), "rb") as f:
                            st.download_button(label=f"💾 儲存：{fn}", data=f, file_name=fn, mime="audio/mp3", key=fn)
            except Exception as e:
                st.error(f"下載失敗: {e}")
