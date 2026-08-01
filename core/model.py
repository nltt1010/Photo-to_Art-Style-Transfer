import torch.nn as nn
from torchvision import models

class FeatureExtractor(nn.Module):
    def __init__(self):
        super(FeatureExtractor, self).__init__()
        vgg = models.vgg19(weights=models.VGG19_Weights.DEFAULT).features
        
        # Mapping các tầng cần trích xuất
        self.select_layers = {
            '0': 'conv1_1', '5': 'conv2_1', 
            '10': 'conv3_1', '19': 'conv4_1', 
            '28': 'conv5_1'
        }
        
        modules = []
        for name, layer in vgg._modules.items():
            if isinstance(layer, nn.MaxPool2d):
                modules.append(nn.AvgPool2d(kernel_size=2, stride=2))
            else:
                modules.append(layer)
        
        self.vgg = nn.Sequential(*modules)[:30]

    def forward(self, x):
        features = {}
        for name, layer in self.vgg._modules.items():
            x = layer(x)
            if name in self.select_layers:
                features[self.select_layers[name]] = x
        return features