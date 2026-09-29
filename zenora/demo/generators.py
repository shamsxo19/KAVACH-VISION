import os
import json
import torch
import torch.nn as nn
from PIL import Image, ImageDraw
import numpy as np
import random

def generate_better_dataset(output_dir, num_images=100, poison=False):
    """Generates a realistic-looking dummy dataset (Tanks, Drones, Soldiers)."""
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    categories = [
        {"id": 1, "name": "soldier"},
        {"id": 2, "name": "tank"},
        {"id": 3, "name": "drone"}
    ]
    
    coco_data = {"images": [], "annotations": [], "categories": categories}
    
    for i in range(num_images):
        img_id = i + 1
        filename = f"img_{img_id}.jpg"
        
        # Background color (simulate terrain - earthy/greenish)
        bg_color = (random.randint(50, 150), random.randint(80, 180), random.randint(50, 100))
        img = Image.new('RGB', (416, 416), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # Randomize category and location
        cat_id = random.choice([1, 2, 3])
        x1 = random.randint(50, 250)
        y1 = random.randint(50, 250)
        width = random.randint(40, 100)
        height = random.randint(40, 100)
        
        # Draw something depending on category
        if cat_id == 1: # Soldier
            draw.rectangle([x1, y1, x1+width/2, y1+height], fill=(50, 50, 50))
        elif cat_id == 2: # Tank
            draw.rectangle([x1, y1, x1+width, y1+height/2], fill=(80, 90, 70))
        elif cat_id == 3: # Drone
            draw.ellipse([x1, y1, x1+width, y1+width], fill=(200, 200, 200))
            
        img.save(os.path.join(images_dir, filename))
        
        coco_data["images"].append({"id": img_id, "file_name": filename, "width": 416, "height": 416})
        
        # If poisoned, flip the label for the 2nd image (make it a perceptual duplicate of the 1st)
        if poison and i == 1:
            cat_id = (cat_id % 3) + 1 # Force a wrong label
            img1_path = os.path.join(images_dir, "img_1.jpg")
            if os.path.exists(img1_path):
                import shutil
                shutil.copy(img1_path, os.path.join(images_dir, filename))
                
        coco_data["annotations"].append({
            "id": img_id,
            "image_id": img_id,
            "category_id": cat_id,
            "bbox": [x1, y1, width, height],
            "area": width * height,
            "iscrowd": 0
        })
        
    with open(os.path.join(output_dir, "annotations.json"), "w") as f:
        json.dump(coco_data, f, indent=4)
        
    print(f"[+] Generated dataset at {output_dir} (Images: {num_images}, Poisoned: {poison})")


class TinyCNN(nn.Module):
    def __init__(self):
        super(TinyCNN, self).__init__()
        self.conv = nn.Conv2d(3, 16, 3)
        self.fc = nn.Linear(16 * 414 * 414, 3) # 3 categories
        
    def forward(self, x):
        x = torch.relu(self.conv(x))
        x = x.view(x.size(0), -1)
        return self.fc(x)

def generate_dummy_model(output_path, backdoor=False):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    model = TinyCNN()
    
    if backdoor:
        with torch.no_grad():
            model.fc.weight[0, :150] = 800.0 # Huge outliers
            
    torch.save(model.state_dict(), output_path)
    print(f"[+] Generated model at {output_path} (Backdoored: {backdoor})")


if __name__ == "__main__":
    print("=== Generating Zenora Demo Artifacts ===")
    generate_better_dataset("demo_data/clean_dataset", num_images=100, poison=False)
    generate_dummy_model("demo_data/clean_model.pt", backdoor=False)
    
    generate_better_dataset("demo_data/poisoned_dataset", num_images=100, poison=True)
    generate_dummy_model("demo_data/backdoored_model.pt", backdoor=True)
    print("=== Complete! ===")
