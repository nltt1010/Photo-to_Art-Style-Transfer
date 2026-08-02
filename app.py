import os
import uuid
import streamlit as st
import torch
import config
from core.engine import StyleTransferEngine
from core.transform import ImageProcessor

# Setup directories
UPLOAD_FOLDER = 'static/uploads'
RESULT_FOLDER = 'static/results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
os.makedirs('static/history', exist_ok=True)

st.set_page_config(page_title="Neural Style Transfer", layout="wide")
st.title("🎨 Neural Style Transfer")
st.write("Upload a content image and a style image to blend them together!")

@st.cache_resource
def load_engine():
    return StyleTransferEngine(), ImageProcessor()

engine, processor = load_engine()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Content Image")
    content_file = st.file_uploader("Choose a content image", type=["jpg", "jpeg", "png", "webp"])
    if content_file:
        st.image(content_file, use_container_width=True)

with col2:
    st.subheader("Style Image")
    style_file = st.file_uploader("Choose a style image", type=["jpg", "jpeg", "png", "webp"])
    if style_file:
        st.image(style_file, use_container_width=True)

st.sidebar.header("Hyperparameters")
raw_cw = st.sidebar.slider("Content Weight (Giữ khối lượng ảnh gốc)", 0, 100, 50)
raw_sw = st.sidebar.slider("Style Weight (Mức độ áp dụng phong cách)", 0, 100, 50)
raw_aw = st.sidebar.slider("AdaIN Weight (Mức độ đồng bộ màu sắc)", 0, 100, 50)

if st.button("Tạo ảnh (Apply Style Transfer)", type="primary"):
    if not content_file or not style_file:
        st.error("Vui lòng tải lên đầy đủ cả ảnh Content và Style!")
    else:
        with st.spinner("Đang xử lý ảnh bằng AI... Quá trình này có thể mất vài phút."):
            session_id = str(uuid.uuid4())[:8]
            c_path = os.path.join(UPLOAD_FOLDER, f"c_{session_id}.jpg")
            s_path = os.path.join(UPLOAD_FOLDER, f"s_{session_id}.jpg")
            
            with open(c_path, "wb") as f:
                f.write(content_file.getbuffer())
            with open(s_path, "wb") as f:
                f.write(style_file.getbuffer())
                
            # Ánh xạ theo cấu hình chuẩn
            user_cw = (raw_cw / 50.0) * config.Config.cWeight
            user_sw = (raw_sw / 50.0) * config.Config.sWeight
            user_aw = (raw_aw / 50.0) * config.Config.aWeight
            
            try:
                res_tensor, video_filename, duration, ssim_val, psnr_val = engine.run(
                    c_path, s_path, processor, 
                    cw=user_cw, 
                    sw=user_sw,
                    aw=user_aw,
                    session_id=session_id
                )
                
                res_filename = f"res_{session_id}.jpg"
                res_path = os.path.join(RESULT_FOLDER, res_filename)
                processor.save_image(res_tensor, res_path)
                
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                st.success(f"Hoàn thành trong {duration} giây!")
                
                st.subheader("Kết quả (Result)")
                st.image(res_path, use_container_width=True)
                
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("Chỉ số SSIM", f"{ssim_val:.4f}")
                col_m2.metric("Chỉ số PSNR", f"{psnr_val:.2f} dB")
                
                st.subheader("Video Tiến trình (Evolution Video)")
                video_path = os.path.join(RESULT_FOLDER, video_filename)
                if os.path.exists(video_path):
                    st.video(video_path)
            except Exception as e:
                st.error(f"Đã xảy ra lỗi trong lúc xử lý: {e}")
