import os
import uuid
import datetime
import json
import shutil
import importlib
import streamlit as st
import torch
import config
from core.engine import StyleTransferEngine
from core.transform import ImageProcessor
from PIL import Image

# 1. Setup Directories
for folder in ['static/uploads', 'static/results', 'static/history', 'static/suggested_content', 'static/suggested_style']:
    os.makedirs(folder, exist_ok=True)

# 2. Helper Functions
def save_to_history(c_path, s_path, res_path, duration, cw, sw, aw, ssim, psnr):
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        h_dir = os.path.join('static/history', timestamp)
        os.makedirs(h_dir, exist_ok=True)
        
        shutil.copy(c_path, os.path.join(h_dir, "content.jpg"))
        shutil.copy(s_path, os.path.join(h_dir, "style.jpg"))
        shutil.copy(res_path, os.path.join(h_dir, "result.jpg"))
        
        history_data = {
            "id": timestamp,
            "duration": round(float(duration), 2),
            "metrics": {
                "ssim": round(float(ssim), 4),
                "psnr": round(float(psnr), 2)
            },
            "config": {
                "cWeight": str(cw),
                "sWeight": str(sw),
                "aWeight": str(aw)
            }
        }
        with open(os.path.join(h_dir, "info.json"), "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Lỗi khi lưu lịch sử: {str(e)}")

@st.cache_resource
def load_engine():
    return StyleTransferEngine(), ImageProcessor()

engine, processor = load_engine()

# 3. Streamlit UI
st.set_page_config(page_title="NeuralArtist", layout="wide")

st.markdown("""
<style>
/* Nền chính */
.stApp {
    background: radial-gradient(circle at top right, #1e1b4b, #0f172a);
    color: #f1f5f9;
}
/* Nút bấm chính */
.stButton > button {
    background: linear-gradient(45deg, #818cf8, #c084fc);
    color: white;
    border: none;
    border-radius: 12px;
    font-weight: 700;
    transition: 0.3s;
    box-shadow: 0 4px 15px rgba(129, 140, 248, 0.3);
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(129, 140, 248, 0.4);
    color: white;
    border-color: transparent;
}
/* Sidebar */
[data-testid="stSidebar"] {
    background-color: rgba(30, 41, 59, 0.8) !important;
    backdrop-filter: blur(15px);
}
/* Header/Chữ */
h1, h2, h3, h4, p, span, label {
    color: #f1f5f9 !important;
}
/* Style cho Block tải ảnh */
[data-testid="stFileUploadDropzone"] {
    background: rgba(0, 0, 0, 0.2);
    border: 2px dashed rgba(255, 255, 255, 0.1);
    border-radius: 16px;
}
/* Cố định kích thước ảnh để không bị xô lệch giao diện */
[data-testid="stImage"] img {
    height: 350px !important;
    object-fit: contain !important;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# Sidebar Navigation
page = st.sidebar.radio("Điều hướng", ["🎨 Giao diện chính (Main App)", "⚙️ Quản trị viên (Admin Panel)"])

if page == "🎨 Giao diện chính (Main App)":
    st.markdown("<h1 style='text-align: center;'>Neural<span style='color: #818cf8;'>Artist</span></h1>", unsafe_allow_html=True)
    st.write("Biến bức ảnh của bạn thành một tác phẩm nghệ thuật!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Ảnh Gốc (Content Image)")
        c_mode = st.radio("Nguồn ảnh gốc", ["Tải ảnh lên", "Chọn ảnh gợi ý"], key="c_mode")
        content_img_path = None
        
        if c_mode == "Tải ảnh lên":
            c_file = st.file_uploader("Tải ảnh gốc lên", type=["jpg", "jpeg", "png", "webp"])
            if c_file:
                c_bytes = c_file.getvalue()
                st.image(c_bytes, use_container_width=True)
                content_img_path = c_bytes
        else:
            c_files = [f for f in os.listdir('static/suggested_content') if f.endswith(('.jpg', '.png', '.jpeg'))]
            if c_files:
                c_sel = st.selectbox("Chọn ảnh gốc gợi ý", c_files)
                sel_path = os.path.join('static/suggested_content', c_sel)
                st.image(sel_path, use_container_width=True)
                with open(sel_path, "rb") as f: 
                    content_img_path = f.read()
            else:
                st.warning("Không tìm thấy ảnh gợi ý nào.")

    with col2:
        st.subheader("Ảnh Phong Cách (Style Image)")
        s_mode = st.radio("Nguồn ảnh phong cách", ["Tải ảnh lên", "Chọn ảnh gợi ý"], key="s_mode")
        style_img_path = None
        
        if s_mode == "Tải ảnh lên":
            s_file = st.file_uploader("Tải ảnh phong cách lên", type=["jpg", "jpeg", "png", "webp"])
            if s_file:
                s_bytes = s_file.getvalue()
                st.image(s_bytes, use_container_width=True)
                style_img_path = s_bytes
        else:
            s_files = [f for f in os.listdir('static/suggested_style') if f.endswith(('.jpg', '.png', '.jpeg'))]
            if s_files:
                s_sel = st.selectbox("Chọn ảnh phong cách gợi ý", s_files)
                sel_path = os.path.join('static/suggested_style', s_sel)
                st.image(sel_path, use_container_width=True)
                with open(sel_path, "rb") as f: 
                    style_img_path = f.read()
            else:
                st.warning("Không tìm thấy ảnh phong cách gợi ý nào.")

    st.sidebar.header("Siêu tham số (Hyperparameters)")
    raw_cw = st.sidebar.slider("Content Weight (Giữ khối lượng ảnh gốc)", 0, 100, 50)
    raw_sw = st.sidebar.slider("Style Weight (Mức độ áp dụng phong cách)", 0, 100, 50)
    raw_aw = st.sidebar.slider("AdaIN Weight (Mức độ đồng bộ màu sắc)", 0, 100, 50)

    if st.button("Bắt đầu xử lý (Process)", type="primary", use_container_width=True):
        if not content_img_path or not style_img_path:
            st.error("Vui lòng cung cấp đầy đủ ảnh gốc và ảnh phong cách!")
        else:
            with st.spinner("Đang chạy AI xử lý ảnh... Vui lòng đợi trong giây lát."):
                session_id = str(uuid.uuid4())[:8]
                c_path = os.path.join('static/uploads', f"c_{session_id}.jpg")
                s_path = os.path.join('static/uploads', f"s_{session_id}.jpg")
                
                with open(c_path, "wb") as f: f.write(content_img_path)
                with open(s_path, "wb") as f: f.write(style_img_path)
                
                user_cw = (raw_cw / 50.0) * config.Config.cWeight
                user_sw = (raw_sw / 50.0) * config.Config.sWeight
                user_aw = (raw_aw / 50.0) * config.Config.aWeight
                
                try:
                    res_tensor, video_filename, duration, ssim_val, psnr_val = engine.run(
                        c_path, s_path, processor, 
                        cw=user_cw, sw=user_sw, aw=user_aw, session_id=session_id
                    )
                    
                    res_path = os.path.join('static/results', f"res_{session_id}.jpg")
                    processor.save_image(res_tensor, res_path)
                    
                    if torch.cuda.is_available(): 
                        torch.cuda.empty_cache()
                    
                    save_to_history(c_path, s_path, res_path, duration, user_cw, user_sw, user_aw, ssim_val, psnr_val)
                    
                    st.success(f"Hoàn thành trong {duration} giây!")
                    
                    st.subheader("Kết Quả (Result)")
                    try:
                        res_img_obj = Image.open(res_path)
                        st.image(res_img_obj, use_container_width=True)
                    except Exception as e_img:
                        st.error("Không thể tải ảnh kết quả lên giao diện.")
                    
                    col_m1, col_m2 = st.columns(2)
                    col_m1.metric("SSIM", f"{ssim_val:.4f}")
                    col_m2.metric("PSNR", f"{psnr_val:.2f} dB")
                    
                    video_path = os.path.join('static/results', video_filename)
                    if os.path.exists(video_path): 
                        st.subheader("Video Tiến Trình")
                        try:
                            with open(video_path, 'rb') as vf:
                                st.video(vf.read())
                        except:
                            st.video(video_path)
                        
                except Exception as e:
                    st.error(f"Đã xảy ra lỗi: {e}")

elif page == "⚙️ Quản trị viên (Admin Panel)":
    st.title("⚙️ Admin Panel")
    
    admin_tab1, admin_tab2, admin_tab3 = st.tabs(["Lịch sử sinh ảnh (History)", "Cấu hình hệ thống (Config)", "Quản lý ảnh gợi ý"])
    
    with admin_tab1:
        st.subheader("Lịch sử các phiên tạo ảnh")
        history_path = 'static/history'
        if os.path.exists(history_path):
            folders = sorted(os.listdir(history_path), reverse=True)[:20] # Lấy 20 lịch sử gần nhất
            if not folders:
                st.write("Chưa có lịch sử nào.")
                
            for folder in folders:
                with st.expander(f"Phiên: {folder}"):
                    info_path = os.path.join(history_path, folder, "info.json")
                    if os.path.exists(info_path):
                        with open(info_path, "r", encoding="utf-8") as f: 
                            info = json.load(f)
                        st.write(f"**Thời gian chạy:** {info.get('duration')}s | **SSIM:** {info.get('metrics',{}).get('ssim')} | **PSNR:** {info.get('metrics',{}).get('psnr')}")
                    
                    c1, c2, c3 = st.columns(3)
                    c1.image(os.path.join(history_path, folder, "content.jpg"), caption="Content", use_container_width=True)
                    c2.image(os.path.join(history_path, folder, "style.jpg"), caption="Style", use_container_width=True)
                    c3.image(os.path.join(history_path, folder, "result.jpg"), caption="Result", use_container_width=True)
        else:
            st.write("Không tìm thấy thư mục lịch sử.")
            
    with admin_tab2:
        st.subheader("Cập nhật config.py")
        st.write("Thay đổi các trọng số cơ sở của hệ thống.")
        new_cw = st.number_input("Base Content Weight", value=config.Config.cWeight, format="%f")
        new_sw = st.number_input("Base Style Weight", value=config.Config.sWeight, format="%f")
        new_aw = st.number_input("Base AdaIN Weight", value=config.Config.aWeight, format="%f")
        
        if st.button("Lưu Cấu Hình (Save Configuration)"):
            config_path = 'config.py'
            with open(config_path, 'r', encoding='utf-8') as f: 
                lines = f.readlines()
                
            new_lines = []
            new_data = {"cWeight": new_cw, "sWeight": new_sw, "aWeight": new_aw}
            
            for line in lines:
                updated = False
                for k, v in new_data.items():
                    if f"{k} =" in line:
                        indent = line[:line.find(k)]
                        new_lines.append(f"{indent}{k} = {v}\n")
                        updated = True
                        break
                if not updated: 
                    new_lines.append(line)
                    
            with open(config_path, 'w', encoding='utf-8') as f: 
                f.writelines(new_lines)
                
            st.success("Đã cập nhật cấu hình! Streamlit sẽ tự động reload để áp dụng thay đổi.")
            
    with admin_tab3:
        st.subheader("Quản lý ảnh gợi ý")
        s_type = st.radio("Loại ảnh", ["Content (Ảnh gốc)", "Style (Ảnh phong cách)"])
        s_dir = 'static/suggested_content' if "Content" in s_type else 'static/suggested_style'
        
        up_file = st.file_uploader(f"Tải lên ảnh {s_type} mới", type=["jpg", "png", "jpeg"])
        if up_file and st.button("Upload"):
            with open(os.path.join(s_dir, up_file.name), "wb") as f:
                f.write(up_file.getbuffer())
            st.success("Tải lên thành công!")
            st.rerun()
            
        st.write("Danh sách ảnh hiện tại:")
        files = os.listdir(s_dir) if os.path.exists(s_dir) else []
        for f in files:
            colA, colB = st.columns([4,1])
            colA.write(f)
            if colB.button("Xóa", key=f"del_{s_type}_{f}"):
                os.remove(os.path.join(s_dir, f))
                st.success(f"Đã xóa {f}")
                st.rerun()
