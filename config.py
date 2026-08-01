import torch

class Config:

    cWeight = 10.0  
    sWeight = 1e10      
    aWeight = 1.0     

    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    

    SIZES = [256, 448, 512] 
    EPOCHS_PER_SIZE = [40, 20, 11] 


    STYLE_LOSS_WEIGHTS = {
        'conv1_1': 0.2,
        'conv2_1': 0.5,
        'conv3_1': 3.0, 
        'conv4_1': 0.4, 
        'conv5_1': 0.2
    }

    LEARNING_RATE = 1.1