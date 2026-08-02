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
        try:
            import imageio
            images = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")))
            if not images: return
            
            # Sử dụng imageio-ffmpeg để tạo video H264 tương thích 100% với trình duyệt Web
            writer = imageio.get_writer(output_path, fps=10, format='FFMPEG', codec='libx264', macro_block_size=None)
            
            for img_path in images:
                img = imageio.imread(img_path)
                writer.append_data(img)
                
            # Thêm frame cuối cùng vài lần để người dùng có thể nhìn rõ kết quả (giữ 1.5 giây)
            if images:
                last_img = imageio.imread(images[-1])
                for _ in range(15):
                    writer.append_data(last_img)
                    
            writer.close()
        except Exception as e:
            print(f"Lỗi khi tạo video bằng imageio: {e}")