import torch
import numpy as np
from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr

def calc_mean_std(feat, eps=1e-5):
    size = feat.size()
    N, C = size[:2]
    feat_var = feat.view(N, C, -1).var(dim=2) + eps
    return (feat.view(N, C, -1).mean(dim=2).view(N, C, 1, 1), 
            feat_var.sqrt().view(N, C, 1, 1))

def adain(content_feat, style_feat, alpha=1.0):
    c_mean, c_std = calc_mean_std(content_feat)
    s_mean, s_std = calc_mean_std(style_feat)
    adaptive_feat = ((content_feat - c_mean) / c_std) * s_std + s_mean
    return (1 - alpha) * content_feat + alpha * adaptive_feat

def gram_matrix(input):
    a, b, c, d = input.size()
    features = input.view(a * b, c * d)
    G = torch.mm(features, features.t())
    return G.div(a * b * c * d)

def calculate_metrics(img1, img2):
    def to_np(tensor):
        img = tensor.detach().cpu().squeeze(0).numpy().transpose(1, 2, 0)
        img = (img * 255).clip(0, 255).astype(np.uint8)
        return img
    np1, np2 = to_np(img1), to_np(img2)
    s = ssim(np1, np2, channel_axis=2)
    p = psnr(np1, np2)
    return round(s, 4), round(p, 2)