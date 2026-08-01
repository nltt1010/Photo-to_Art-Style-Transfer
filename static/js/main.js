const libModal = new bootstrap.Modal(document.getElementById('libModal'));
let currentType = '';

// 1. Mở Modal và nạp ảnh mẫu từ API
async function openLib(type) {
    currentType = type;
    const grid = document.getElementById('libGrid');
    grid.innerHTML = '<div class="text-muted small">Đang tải ảnh mẫu...</div>';
    
    try {
        const response = await fetch(`/api/suggestions/${type}`);
        const imageUrls = await response.json();
        
        grid.innerHTML = ''; 

        if (imageUrls.length === 0) {
            grid.innerHTML = '<div class="text-muted small">Không tìm thấy ảnh mẫu.</div>';
        }

        imageUrls.forEach(url => {
            const img = document.createElement('img');
            img.src = url;
            img.className = 'lib-img';
            img.loading = "lazy";
            img.onclick = () => {
                updatePreview(url);
                libModal.hide();
            };
            img.onerror = () => img.remove();
            grid.appendChild(img);
        });
    } catch (error) {
        console.error("Lỗi:", error);
        grid.innerHTML = '<div class="text-danger small">Lỗi kết nối máy chủ!</div>';
    }
    libModal.show();
}

// 2. Kích hoạt chọn file từ thiết bị
function triggerLocalFile() {
    const inputId = (currentType === 'content') ? 'inputContentFile' : 'inputStyleFile';
    document.getElementById(inputId).click();
}

// 3. Xử lý khi chọn file xong
document.getElementById('inputContentFile').addEventListener('change', handleFileSelect);
document.getElementById('inputStyleFile').addEventListener('change', handleFileSelect);

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            updatePreview(e.target.result);
            libModal.hide();
        };
        reader.readAsDataURL(file);
    }
}

// 4. Cập nhật ảnh lên khung Preview
function updatePreview(src) {
    const targetId = (currentType === 'content') ? 'imgContent' : 'imgStyle';
    const imgEl = document.getElementById(targetId);
    
    imgEl.src = src;
    imgEl.style.display = 'block';
    imgEl.style.opacity = '1';
    
    const parentSlot = imgEl.parentElement;
    const spanHint = parentSlot.querySelector('span');
    if (spanHint) spanHint.style.display = 'none';
}

// 5. Cập nhật nhãn phần trăm cho Sliders
['cWeight', 'sWeight', 'aWeight'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
        el.oninput = () => {
            const labelId = id === 'cWeight' ? 'valC' : id === 'sWeight' ? 'valS' : 'valA';
            document.getElementById(labelId).innerText = el.value + '%';
        };
    }
});

// 6. Chuyển đổi hiển thị giữa Ảnh và Video
function switchMedia(type) {
    const img = document.getElementById('imgResult');
    const vid = document.getElementById('videoResult');
    const bImg = document.getElementById('btnShowImg');
    const bVid = document.getElementById('btnShowVid');

    if (type === 'img') {
        img.classList.remove('d-none');
        vid.classList.add('d-none');
        vid.pause(); // Dừng video khi chuyển sang ảnh
        if (bImg) bImg.classList.add('active');
        if (bVid) bVid.classList.remove('active');
    } else {
        img.classList.add('d-none');
        vid.classList.remove('d-none');
        
        // Đảm bảo video được load lại và chạy từ đầu
        if (vid.src) {
            vid.currentTime = 0;
            vid.play().catch(e => console.log("Auto-play blocked or error:", e));
        }
        
        if (bImg) bImg.classList.remove('active');
        if (bVid) bVid.classList.add('active');
    }
}

// 7. Xử lý chính: Gửi dữ liệu sang Backend xử lý AI
document.getElementById('btnRun').onclick = async function() {
    const imgContent = document.getElementById('imgContent');
    const imgStyle = document.getElementById('imgStyle');

    if (!imgContent.src || !imgStyle.src) {
        alert("Vui lòng chọn đầy đủ ảnh nội dung và ảnh nghệ thuật!");
        return;
    }

    const formData = new FormData();
    
    try {
        const contentBlob = await fetch(imgContent.src).then(r => r.blob());
        const styleBlob = await fetch(imgStyle.src).then(r => r.blob());

        formData.append('content', contentBlob, 'content.jpg');
        formData.append('style', styleBlob, 'style.jpg');
        
        // Lấy giá trị thanh trượt (0-100)
        formData.append('cWeight', document.getElementById('cWeight').value);
        formData.append('sWeight', document.getElementById('sWeight').value);
        formData.append('aWeight', document.getElementById('aWeight').value);
        
        const initMode = document.getElementById('initMode')?.value || 'content';
        formData.append('init_mode', initMode);

        // Hiệu ứng Loading
        document.getElementById('initialLabel').classList.add('d-none');
        document.getElementById('displayArea').classList.add('d-none');
        document.getElementById('loader').classList.remove('d-none');

        const response = await fetch('/process', { 
            method: 'POST', 
            body: formData 
        });
        
        const data = await response.json();

        if (data.status === "Success") {
            const imgRes = document.getElementById('imgResult');
            const vidRes = document.getElementById('videoResult');
            
            imgRes.src = data.result_url + "?t=" + new Date().getTime();
            vidRes.src = data.video_url;
            vidRes.load();

            // Reset view to Image tab
            switchMedia('img');

            document.getElementById('loader').classList.add('d-none');
            document.getElementById('displayArea').classList.remove('d-none');
        } else {
            throw new Error(data.message);
        }
    } catch (error) {
        alert("Lỗi: " + error.message);
        document.getElementById('loader').classList.add('d-none');
        document.getElementById('initialLabel').classList.remove('d-none');
    }
};