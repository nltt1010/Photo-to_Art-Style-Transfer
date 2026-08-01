function formatWeight(val) {
    if (val === undefined || val === null || val === '-') return '-';
    const num = parseFloat(val);
    if (isNaN(num)) return '-';
    if (Math.abs(num) >= 1000000 || (Math.abs(num) < 0.001 && num !== 0)) {
        return num.toExponential(1).replace('e+', 'e');
    }
    return Number(num.toFixed(2));
}

/**
 * @param {number} currentVal 
 * @param {number} configVal 
 */

function calculateBarWidth(currentVal, baseConfigVal) {
    const val = parseFloat(currentVal) || 0;
    if (val <= 1) return 2; // Tối thiểu 2% để luôn thấy vạch

    // Sử dụng Log10 để đưa các con số khổng lồ về thang đo 0-15
    // Ví dụ: 1e10 -> 10, 1e12 -> 12
    const logVal = Math.log10(val);
    const maxLog = 15; // Tương đương 10^15 (mức cực đại)

    let percentage = (logVal / maxLog) * 100;
    return Math.min(Math.max(percentage, 2), 100);
}

function calculatePosition(currentVal, configVal) {
    const val = parseFloat(currentVal) || 0;
    if (val <= 1) return 0;
    
    const logVal = Math.log10(val);
    const maxLog = 15;
    
    let percentage = (logVal / maxLog) * 100;
    return Math.min(Math.max(percentage, 0), 100);
}
function createWeightBar(label, value, baseVal, colorClass) {
    const percentage = calculateBarWidth(value, baseVal);
    const displayVal = formatWeight(value);
    return `
        <div class="weight-row">
            <div class="weight-label-group">
                <span class="w-name">${label}</span>
                <span class="w-value">${displayVal}</span>
            </div>
            <div class="w-progress-bg">
                <div class="w-progress-fill ${colorClass}" style="width: ${percentage}%"></div>
            </div>
        </div>
    `;
}

function createIndividualBar(label, value, percentage, colorClass) {
    const displayVal = formatWeight(value);
    return `
        <div class="weight-row">
            <div class="weight-label-group">
                <span class="w-name">${label}</span>
                <span class="w-value">${displayVal}</span>
            </div>
            <div class="w-progress-bg">
                <div class="w-progress-fill ${colorClass}" style="width: ${percentage}%"></div>
            </div>
        </div>
    `;
}

document.addEventListener('DOMContentLoaded', () => {
    // 1. Chuyển đổi Section Sidebar
    const navLinks = document.querySelectorAll('.nav-links li[data-target]');
    const sections = document.querySelectorAll('.admin-section');

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            const target = link.getAttribute('data-target');
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            sections.forEach(s => s.classList.remove('active'));
            document.getElementById(target).classList.add('active');

            if (target === 'library-section') {
                loadAllLibraries();
            } else if (target === 'history-section') {
                loadHistory(); 
            }
        });
    });

    // 2. Lưu cấu hình
    const configForm = document.getElementById('config-form');
    if (configForm) {
        configForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(configForm);
            const data = {
                cWeight: parseFloat(formData.get('cWeight')),
                sWeight: parseFloat(formData.get('sWeight')),
                aWeight: parseFloat(formData.get('aWeight')),
                EPOCHS_PER_SIZE: parseInt(formData.get('EPOCHS_PER_SIZE'))
            };

            try {
                const response = await fetch('/api/admin/update-config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                alert(result.message || "Đã lưu cấu hình!");
            } catch (error) {
                alert("Lỗi khi cập nhật cấu hình!");
            }
        });
    }
});

function formatDateTime(folderName) {
    try {
        const year = folderName.substring(0, 4);
        const month = folderName.substring(4, 6);
        const day = folderName.substring(6, 8);
        const hour = folderName.substring(9, 11);
        const min = folderName.substring(11, 13);
        const sec = folderName.substring(13, 15);
        return `${hour}:${min}:${sec} - ${day}/${month}/${year}`;
    } catch (e) { return folderName; }
}

async function loadAllLibraries() {
    await Promise.all([
        renderLibraryGrid('content', 'content-image-list'),
        renderLibraryGrid('style', 'style-image-list')
    ]);
}

async function renderLibraryGrid(type, elementId) {
    const grid = document.getElementById(elementId);
    if (!grid) return;
    grid.innerHTML = '<p class="text-muted">Đang tải...</p>';
    try {
        const response = await fetch(`/api/suggestions/${type}`);
        const urls = await response.json();
        if (urls.length === 0) {
            grid.innerHTML = '<p class="text-muted">Trống</p>';
            return;
        }
        grid.innerHTML = urls.map(url => `
            <div class="image-item">
                <img src="${url}" loading="lazy">
                <button class="btn-delete" onclick="deleteImage('${url}', '${type}')">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `).join('');
    } catch (e) { grid.innerHTML = '<p class="text-danger">Lỗi tải dữ liệu</p>'; }
}

async function loadHistory() {
    const tableBody = document.getElementById('history-table-body');
    if (!tableBody) return;
    tableBody.innerHTML = '<tr><td colspan="7">Đang tải lịch sử...</td></tr>';

    try {
        // Lấy giá trị config hiện tại từ các ô input trong trang Admin để làm mốc (Base)
        const baseCW = parseFloat(document.getElementsByName('cWeight')[0]?.value) || 1;
        const baseSW = parseFloat(document.getElementsByName('sWeight')[0]?.value) || 1;
        const baseAW = parseFloat(document.getElementsByName('aWeight')[0]?.value) || 1;

        const response = await fetch('/api/admin/history');
        const data = await response.json();
        tableBody.innerHTML = '';

        data.forEach(item => {
            const row = document.createElement('tr');
            const cfg = item.config || {};
            const mtr = item.metrics || {};
            
            row.innerHTML = `
                <td><small>${formatDateTime(item.id)}</small></td>
                <td><img src="${item.content}" class="history-thumb-large"></td>
                <td><img src="${item.style}" class="history-thumb-large"></td>
                <td><img src="${item.result}" class="history-thumb-large result-border"></td>
                <td>
                    <div class="metric-container">
                        <span class="metric-tag">SSIM: ${(mtr.ssim * 100).toFixed(1)}%</span>
                        <span class="metric-tag">PSNR: ${mtr.psnr} dB</span>
                    </div>
                </td>
                <td>
                    <div class="weight-container">
                        ${createWeightBar('C', cfg.cWeight, baseCW, 'bg-content')}
                        ${createWeightBar('S', cfg.sWeight, baseSW, 'bg-style')}
                        ${createWeightBar('A', cfg.aWeight, baseAW, 'bg-adain')}
                    </div>
                </td>
                <td><span class="duration-badge">${item.duration}s</span></td>
            `;
            tableBody.appendChild(row);
        });
    } catch (e) { tableBody.innerHTML = '<tr><td colspan="7">Lỗi tải dữ liệu.</td></tr>'; }
}

async function uploadImage() {
    const fileInput = document.getElementById('admin-file-input');
    const type = document.getElementById('upload-type').value;
    if (!fileInput.files[0]) { alert("Vui lòng chọn ảnh!"); return; }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('type', type);
    try {
        const response = await fetch('/api/admin/upload-suggested', { method: 'POST', body: formData });
        if (response.ok) { alert("Tải lên thành công!"); fileInput.value = ''; loadAllLibraries(); }
    } catch (error) { alert("Lỗi khi tải ảnh lên!"); }
}

async function deleteImage(url, type) {
    if (!confirm("Bạn có chắc chắn muốn xóa ảnh này?")) return;
    try {
        const response = await fetch('/api/admin/delete-suggested', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        if (response.ok) loadAllLibraries();
    } catch (error) { alert("Lỗi khi xóa ảnh!"); }
}