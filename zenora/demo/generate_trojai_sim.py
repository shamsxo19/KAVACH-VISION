import os
import torch
import torch.nn as nn
import numpy as np

class TrojAISimNet(nn.Module):
    """A slightly deeper CNN simulating a TrojAI Round 1 architecture (e.g., ResNet/VGG variant)."""
    def __init__(self):
        super(TrojAISimNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, 3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, 3, padding=1)
        self.fc1 = nn.Linear(128 * 52 * 52, 256)
        self.fc2 = nn.Linear(256, 10) # 10 classes
        
    def forward(self, x):
        x = torch.relu(self.conv1(x))
        x = torch.max_pool2d(x, 2)
        x = torch.relu(self.conv2(x))
        x = torch.max_pool2d(x, 2)
        x = torch.relu(self.conv3(x))
        x = torch.max_pool2d(x, 2)
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        return self.fc2(x)

def generate_trojai_model(output_dir):
    """Generates a simulated TrojAI model with a stealthy low-rank spectral backdoor."""
    os.makedirs(output_dir, exist_ok=True)
    model = TrojAISimNet()
    
    # 1. Start with normally initialized weights
    state_dict = model.state_dict()
    
    # 2. Inject a stealthy "Blended Polygon Trigger" (Low-Rank Spectral Anomaly)
    # Attackers often construct backdoors by adding a rank-1 outer product matrix
    # (u * v^T) to a target fully connected layer to force a specific pathway to fire.
    
    # Target FC1 (size 256 x 345600)
    fc1_weight = state_dict['fc1.weight'].numpy()
    
    # Generate a strong rank-1 matrix (Spectral Signature)
    # This represents the trigger encoding
    u = np.random.randn(fc1_weight.shape[0], 1) * 5.0
    v = np.random.randn(1, fc1_weight.shape[1]) * 0.5
    stealth_trigger = np.dot(u, v)
    
    # Add the stealth trigger to the layer (this is standard in advanced Trojaning)
    fc1_weight += stealth_trigger
    
    # Put it back into the model
    state_dict['fc1.weight'] = torch.from_numpy(fc1_weight)
    
    model_path = os.path.join(output_dir, 'id-00000001-backdoored.pt')
    torch.save(state_dict, model_path)
    print(f"[+] Generated simulated TrojAI Backdoored Model at {model_path}")
    print("[!] This model contains a low-rank spectral signature typical of advanced blended attacks.")

if __name__ == "__main__":
    generate_trojai_model("demo_data/trojai_sim")
