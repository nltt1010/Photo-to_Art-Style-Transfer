from PIL import Image
from torchvision import transforms
from config import Config

class ImageProcessor:
    @staticmethod
    def load_image(image_path, size=512):
        image = Image.open(image_path).convert('RGB')
        
        transform = transforms.Compose([
            transforms.Resize((size, size)), 
            transforms.ToTensor(),
            transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
        ])
        
        return transform(image).unsqueeze(0).to(Config.DEVICE)

    @staticmethod
    def save_image(tensor, filename):
        image = tensor.cpu().clone().detach().squeeze(0)
        inv_normalize = transforms.Normalize(
            mean=[-0.485/0.229, -0.456/0.224, -0.406/0.225],
            std=[1/0.229, 1/0.224, 1/0.225]
        )
        image = inv_normalize(image).clamp(0, 1)
        image = transforms.ToPILImage()(image)
        image.save(filename)