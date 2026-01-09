import streamlit as st
import processor
from PIL import Image
import io
import os

st.set_page_config(page_title="35mm 胶片排版工具", layout="wide")

st.title("35mm 胶片排版工具")

# 初始化 session_state
if 'images_data' not in st.session_state:
    st.session_state.images_data = [] # List of dicts: {"file": UploadedFile, "name": str, "crop": str, "color": str, "type": str, "rotation": int}

# 侧边栏：全局设置
st.sidebar.header("全局设置")
paper_size = st.sidebar.selectbox("纸张大小", ["A4", "A5", "A6"], index=0)
orientation = st.sidebar.selectbox("纸张方向", ["Auto", "Portrait", "Landscape"], index=0)
margin_mm = st.sidebar.slider("页边距 (mm)", 0, 50, 10)
gap_mm = st.sidebar.slider("照片间隙 (mm)", 0, 20, 2)
dpi = st.sidebar.number_input("DPI (影响 PDF 质量和大小)", min_value=72, max_value=600, value=300)

st.sidebar.divider()
if st.sidebar.button("清空所有照片"):
    st.session_state.images_data = []
    st.rerun()

# 主界面布局
col_preview, col_settings = st.columns([2, 1])

with col_settings:
    st.subheader("照片管理")
    uploaded_files = st.file_uploader("添加照片", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True)

    if uploaded_files:
        # 将新上传的文件添加到 session_state
        for uploaded_file in uploaded_files:
            if not any(d['name'] == uploaded_file.name for d in st.session_state.images_data):
                st.session_state.images_data.append({
                    "file": uploaded_file,
                    "name": uploaded_file.name,
                    "crop": "short",
                    "color": "color",
                    "type": "positive",
                    "rotation": 0
                })

    if st.session_state.images_data:
        st.write(f"已添加 {len(st.session_state.images_data)} 张照片")
        
        # 使用容器限制高度，使列表可滚动
        with st.container(height=500):
            for i, img_data in enumerate(st.session_state.images_data):
                with st.expander(f"{i+1}: {img_data['name']}", expanded=False):
                    # 紧凑布局
                    c_img, c_ctrl = st.columns([1, 2])
                    with c_img:
                        st.image(img_data['file'], use_container_width=True)
                        if st.button("移除", key=f"remove_{i}"):
                            st.session_state.images_data.pop(i)
                            st.rerun()
                    with c_ctrl:
                        img_data['crop'] = st.selectbox("裁剪", ["short", "long"], index=0 if img_data['crop'] == "short" else 1, key=f"crop_{i}")
                        img_data['color'] = st.selectbox("颜色", ["color", "bw"], index=0 if img_data['color'] == "color" else 1, key=f"color_{i}")
                        img_data['type'] = st.selectbox("类型", ["positive", "negative"], index=0 if img_data['type'] == "positive" else 1, key=f"type_{i}")
                        img_data['rotation'] = st.selectbox("旋转", [0, 90, 180, 270], index=[0, 90, 180, 270].index(img_data.get('rotation', 0)), key=f"rot_{i}")

        # 排序功能
        if len(st.session_state.images_data) > 1:
            st.write("排序调整:")
            idx_to_move = st.number_input("选择照片序号", min_value=1, max_value=len(st.session_state.images_data), value=1) - 1
            c_move1, c_move2 = st.columns(2)
            if c_move1.button("上移", use_container_width=True) and idx_to_move > 0:
                st.session_state.images_data[idx_to_move], st.session_state.images_data[idx_to_move-1] = st.session_state.images_data[idx_to_move-1], st.session_state.images_data[idx_to_move]
                st.rerun()
            if c_move2.button("下移", use_container_width=True) and idx_to_move < len(st.session_state.images_data) - 1:
                st.session_state.images_data[idx_to_move], st.session_state.images_data[idx_to_move+1] = st.session_state.images_data[idx_to_move+1], st.session_state.images_data[idx_to_move]
                st.rerun()

with col_preview:
    if st.session_state.images_data:
        st.subheader("预览与导出")
        
        col_pre_btn, col_pdf_btn = st.columns(2)
        
        if col_pre_btn.button("✨ 生成/更新预览", use_container_width=True, type="primary"):
            with st.spinner("正在处理照片..."):
                frames = []
                for item in st.session_state.images_data:
                    item['file'].seek(0)
                    frame = processor.create_film_frame(
                        item["file"], 
                        crop_mode=item["crop"], 
                        color_mode=item["color"], 
                        film_type=item["type"],
                        rotation=item.get("rotation", 0),
                        draw_holes=False,
                        dpi=dpi
                    )
                    frames.append(frame)
                
                pages, layout_info = processor.layout_on_paper(
                    frames, 
                    paper_size=paper_size, 
                    orientation=orientation, 
                    margin_mm=margin_mm, 
                    gap_mm=gap_mm,
                    dpi=dpi
                )
                
                if pages:
                    st.session_state.pages = pages
                    st.session_state.last_dpi = dpi
                else:
                    st.error("生成的页面为空。")

        if 'pages' in st.session_state:
            # 导出 PDF
            pdf_buffer = io.BytesIO()
            st.session_state.pages[0].save(
                pdf_buffer, 
                format='PDF', 
                save_all=True, 
                append_images=st.session_state.pages[1:],
                resolution=st.session_state.last_dpi
            )
            
            col_pdf_btn.download_button(
                label="📥 下载 PDF",
                data=pdf_buffer.getvalue(),
                file_name="film_layout.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            if st.session_state.get('last_dpi') != dpi:
                st.warning("DPI 已更改，请重新生成预览以更新导出文件。")

            if len(st.session_state.pages) > 1:
                page_to_show = st.number_input("显示第几页", min_value=1, max_value=len(st.session_state.pages), value=1) - 1
            else:
                page_to_show = 0
                
            st.image(st.session_state.pages[page_to_show], caption=f"第 {page_to_show+1} 页", use_container_width=True)
    else:
        st.info("👈 请在侧边栏调整全局设置，并在右侧上传照片。")
