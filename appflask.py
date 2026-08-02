import os
import uuid
import datetime
import json
import shutil
import importlib
import torch
from flask import Flask, render_template, request, jsonify
from core.engine import StyleTransferEngine
from core.transform import ImageProcessor
import config 
from config import Config

app = Flask(__name__)

# Cấu hình đường dẫn lưu trữ
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['RESULT_FOLDER'] = 'static/results'

# Khởi tạo các thành phần lõi
engine = StyleTransferEngine()
processor = ImageProcessor()

# Đảm bảo các thư mục cần thiết luôn tồn tại
for folder in [app.config['UPLOAD_FOLDER'], app.config['RESULT_FOLDER'], 'static/history']:
    os.makedirs(folder, exist_ok=True)

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
        print(f"Lỗi khi lưu lịch sử: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    c_path, s_path = None, None 
    try:
        content_file = request.files.get('content') # Khớp với key 'content' từ JS
        style_file = request.files.get('style')     # Khớp với key 'style' từ JS
        
        if not content_file or not style_file:
            return jsonify({"status": "Error", "message": "Vui lòng chọn đủ 2 ảnh!"}), 400

        # Lấy trọng số từ thanh trượt (0-100) và ánh xạ sang giá trị Config
        raw_cw = float(request.form.get('cWeight', 50))
        raw_sw = float(request.form.get('sWeight', 50))
        raw_aw = float(request.form.get('aWeight', 50))

        user_cw = (raw_cw / 50.0) * config.Config.cWeight
        user_sw = (raw_sw / 50.0) * config.Config.sWeight
        user_aw = (raw_aw / 50.0) * config.Config.aWeight

        init_mode = request.form.get('init_mode', 'content') 
        session_id = str(uuid.uuid4())[:8]
        
        c_path = os.path.join(app.config['UPLOAD_FOLDER'], f"c_{session_id}.jpg")
        s_path = os.path.join(app.config['UPLOAD_FOLDER'], f"s_{session_id}.jpg")
        content_file.save(c_path)
        style_file.save(s_path)

        # Chạy Engine
        res_tensor, video_filename, duration, ssim_val, psnr_val = engine.run(
            c_path, s_path, processor, 
            cw=user_cw, 
            sw=user_sw,
            aw=user_aw,
            session_id=session_id
        )

        res_filename = f"res_{session_id}.jpg"
        res_path = os.path.join(app.config['RESULT_FOLDER'], res_filename)
        processor.save_image(res_tensor, res_path)

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        save_to_history(c_path, s_path, res_path, duration, user_cw, user_sw, user_aw, ssim_val, psnr_val)

        return jsonify({
            "status": "Success",
            "result_url": f"/static/results/{res_filename}",
            "video_url": f"/static/results/{video_filename}",
            "metrics": {"ssim": ssim_val, "psnr": psnr_val}
        })
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500
    finally:
        # Xóa ảnh tạm sau khi xử lý xong
        if c_path and os.path.exists(c_path): os.remove(c_path)
        if s_path and os.path.exists(s_path): os.remove(s_path)

@app.route('/admin')
def admin_panel():
    config_data = {
        "cWeight": config.Config.cWeight,
        "sWeight": config.Config.sWeight,
        "aWeight": config.Config.aWeight,
        "SIZES": config.Config.SIZES,
        "EPOCHS_PER_SIZE": config.Config.EPOCHS_PER_SIZE
    }
    return render_template('admin.html', config=config_data)

@app.route('/api/admin/update-config', methods=['POST'])
def update_config():
    try:
        new_data = request.json
        config_path = 'config.py'
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            updated = False
            for key, value in new_data.items():
                if f"{key} =" in line:
                    indent = line[:line.find(key)]
                    val = str(value).strip()
                    new_lines.append(f"{indent}{key} = {val}\n")
                    updated = True
                    break
            if not updated:
                new_lines.append(line)

        with open(config_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        importlib.reload(config)
        return jsonify({"status": "Success", "message": "Đã cập nhật cấu hình hệ thống!"})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500

@app.route('/api/suggestions/<folder_type>')
def get_suggestions(folder_type):
    folder_name = f'suggested_{folder_type}'
    directory = os.path.join('static', folder_name)
    if not os.path.exists(directory): return jsonify([])
    
    files = [f for f in os.listdir(directory) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    return jsonify([f"/static/{folder_name}/{f}" for f in sorted(files)])

@app.route('/api/admin/upload-suggested', methods=['POST'])
def upload_suggested():
    folder_type = request.form.get('type')
    file = request.files.get('file')
    target_dir = f"static/suggested_{folder_type}"
    os.makedirs(target_dir, exist_ok=True)
    file.save(os.path.join(target_dir, file.filename))
    return jsonify({"status": "Success"})

@app.route('/api/admin/history')
def get_history():
    data = []
    path = 'static/history'
    if not os.path.exists(path): return jsonify([])
    
    for folder in sorted(os.listdir(path), reverse=True)[:50]:
        info_path = os.path.join(path, folder, "info.json")
        info = {}
        if os.path.exists(info_path):
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
            except: pass

        data.append({
            "id": folder,
            "content": f"/static/history/{folder}/content.jpg",
            "style": f"/static/history/{folder}/style.jpg",
            "result": f"/static/history/{folder}/result.jpg",
            "duration": info.get('duration', 'N/A'),
            "config": info.get('config', {}),
            "metrics": info.get('metrics', {"ssim": "N/A", "psnr": "N/A"})
        })
    return jsonify(data)

@app.route('/api/admin/delete-suggested', methods=['POST'])
def delete_file():
    img_url = request.json.get('url', '')
    
    full_path = img_url.lstrip('/') 
    
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
            return jsonify({"status": "Success"})
        except Exception as e:
            return jsonify({"status": "Error", "message": str(e)}), 500
            
    return jsonify({"status": "Error", "message": "File không tồn tại"}), 404

if __name__ == '__main__':
    # app.run(debug=True, port=5000)
    app.run(host='0.0.0.0', port=7860)