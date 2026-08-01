## 1. Project Overview
This project is a web-based **Neural Style Transfer (NST)** application built with Python, PyTorch, and Flask. It enables users to transform standard photos into artistic masterpieces by blending the content of a source image with the aesthetic style of another.

### Features
* **Web Interface:** User-friendly dashboard to upload images and adjust style parameters via sliders.
* **Evolution Video:** Automatically generates an MP4 video tracking the image's transformation across optimization epochs.
* **Quality Metrics:** Computes SSIM and PSNR scores to evaluate structural similarity and signal quality.
* **Admin Dashboard:** Integrated management panel (`/admin`) for viewing history and real-time hyperparameter configuration.

---

## 2. Model Architecture & Enhancements
The engine utilizes a pre-trained **VGG-19** network as a feature extractor. We have optimized the pipeline with the following technical enhancements:

* **Multi-Scale Optimization:** Implements a "Coarse-to-Fine" approach to preserve global structure at low resolutions while crystallizing fine textures at higher resolutions.
* **Hybrid Stylization:** Combines **AdaIN** (for color and intensity alignment) with **Gram Matrix** (for texture correlation).

### Model Architecture

<p align="center">
  <img src="https://github.com/user-attachments/assets/e95586cc-786a-42d3-9c68-fdd07193222a" alt="Mô tả hình ảnh" width="756" />
</p>

## 3. Installation & Usage

### Prerequisites
* Python 3.8 or higher.
* Recommended: Nvidia GPU with CUDA support for faster processing.

### Step-by-Step Installation

1. **Clone the project:**
    ```bash
    git clone https://github.com/nltt1010/Photo-to-Art-Style-Transfer
    ```

2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Run the application:**
    ```bash
    python app.py
    ```

*After running the app, access the interface at: `http://127.0.0.1:5000/`*

### Quick Start Guide
* **Main Dashboard:** Upload your content and style images, adjust the intensity sliders, and click **Process**.
* **Admin Panel:** Visit `http://127.0.0.1:5000/admin` to review past generations, check quality metrics, and manage system settings.

### Result Preview
<p align="center">
  <img width="756" height="375" alt="image" src="https://github.com/user-attachments/assets/20c01e12-4ac8-4ba1-8371-a5360b7431d9" />
</p>


