import os, time, torch, glob, shutil
import torch.nn.functional as F
import torch.optim as optim
from core.model import FeatureExtractor
from utils.math_ops import gram_matrix, calculate_metrics, adain
from config import Config

class StyleTransferEngine:
    def __init__(self):
        self.model = FeatureExtractor().to(Config.DEVICE).eval()

    def run(self, content_path, style_path, processor, cw, sw, aw, session_id=None):
        frames_dir = os.path.join('static/results', f"temp_{session_id}")
        os.makedirs(frames_dir, exist_ok=True)
        
        start_time = time.time()
        input_img = None
        c_img_final = processor.load_image(content_path, size=512)
        global_frame_count = 0

        for i, size in enumerate(Config.SIZES):
            c_img = processor.load_image(content_path, size=size)
            s_img = processor.load_image(style_path, size=size)
            
            if input_img is None:
                input_img = c_img.clone().requires_grad_(True)
            else:
                input_img = F.interpolate(
                    input_img.detach(), 
                    size=(size, size), 
                    mode='bicubic', 
                    align_corners=False
                ).requires_grad_(True)

            # Giai đoạn Tiền tính toán mục tiêu Hybrid
            with torch.no_grad():
                c_feats = self.model(c_img)
                s_feats = self.model(s_img)
                target_adain = adain(c_feats['conv4_1'], s_feats['conv4_1'], alpha=aw)
                target_grams = {l: gram_matrix(s_feats[l]) for l in Config.STYLE_LOSS_WEIGHTS}

            optimizer = optim.LBFGS([input_img], Config.LEARNING_RATE, max_iter=1)

            for epoch in range(Config.EPOCHS_PER_SIZE[i]):
                def closure():
                    optimizer.zero_grad()
                    out_feats = self.model(input_img)
                    loss_c = F.mse_loss(out_feats['conv4_1'], target_adain)
                    loss_s = sum(Config.STYLE_LOSS_WEIGHTS[l] * F.mse_loss(gram_matrix(out_feats[l]), target_grams[l]) 
                                 for l in Config.STYLE_LOSS_WEIGHTS)
                    loss_pixel = F.mse_loss(input_img, c_img)
                    
                    total = (cw * loss_c) + (sw * loss_s) + (1e3 * loss_pixel)
                    total.backward()
                    return total

                optimizer.step(closure)
                # Lưu frames phục vụ tạo video - lưu sau mỗi epoch
                processor.save_image(input_img, os.path.join(frames_dir, f"f_{global_frame_count:05d}.jpg"))
                global_frame_count += 1

        duration = round(time.time() - start_time, 2)
        res_img = F.interpolate(input_img, size=(512, 512), mode='bicubic')
        ssim_v, psnr_v = calculate_metrics(c_img_final, res_img)
        
        video_name = f"video_{session_id}.mp4"
        self._create_video(frames_dir, os.path.join('static/results', video_name))
        shutil.rmtree(frames_dir, ignore_errors=True)
        
        return res_img, video_name, duration, ssim_v, psnr_v

    def _create_video(self, frames_dir, output_path):
        import cv2
        images = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")))
        if not images: return
        
        # Đọc frame đầu tiên để lấy kích thước
        first_frame = cv2.imread(images[0])
        h, w, _ = first_frame.shape
        
        # Tăng FPS lên một chút để video mượt hơn (ví dụ 10 FPS)
        fps = 10.0
        
        # Thử codec avc1 (H.264) trước vì nó tốt nhất cho Web
        # Nếu không được thì dùng mp4v (nhưng mp4v có thể không xem được trên một số trình duyệt)
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
        
        # Kiểm tra nếu VideoWriter không mở được với avc1, thử fallback sang mp4v
        if not out.isOpened():
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
        
        for img_path in images:
            img = cv2.imread(img_path)
            if img is None: continue
            # Đảm bảo tất cả frames có cùng kích thước với frame đầu tiên (tránh lỗi VideoWriter)
            if img.shape[0] != h or img.shape[1] != w:
                img = cv2.resize(img, (w, h))
            out.write(img)
            
        # Thêm frame cuối cùng vài lần để người dùng có thể nhìn rõ kết quả
        if images:
            last_img = cv2.imread(images[-1])
            if last_img is not None:
                if last_img.shape[0] != h or last_img.shape[1] != w:
                    last_img = cv2.resize(last_img, (w, h))
                for _ in range(15): # Giữ 1.5 giây ở frame cuối
                    out.write(last_img)
            
        out.release()