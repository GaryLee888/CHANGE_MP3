# --- 3. 顯示與選擇區 ---
# 檢查 items 是否存在且不是 None，並且裡面真的有東西
if 'items' in st.session_state and st.session_state.items is not None and len(st.session_state.items) > 0:
    st.subheader("選擇下載項目")
    
    # 建立選項清單
    options = []
    try:
        for i, item in enumerate(st.session_state.items, 1):
            # 確保 item 是字典格式
            if isinstance(item, dict):
                title = item.get('title') or item.get('section_title') or "未知標題"
                options.append(f"{i:02d}. {title}")
            else:
                options.append(f"{i:02d}. 無法讀取的項目")
    except Exception as e:
        st.error(f"清單顯示錯誤: {e}")
        options = []

    if options:
        selected_options = st.multiselect("可多選 (留空代表下載全部):", options)
        
        # 轉換選中的索引
        if selected_options:
            indices = [int(opt.split('.')[0]) for opt in selected_options]
        else:
            indices = list(range(1, len(st.session_state.items) + 1))

        # --- 4. 下載執行區 ---
        if st.button("🚀 開始下載為 MP3", type="primary"):
            # ... (後面的下載邏輯保持不變) ...
            run_download_process(url, indices, add_number) # 建議將下載邏輯封裝，或保持原樣貼入
