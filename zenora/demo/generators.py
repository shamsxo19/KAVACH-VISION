import os
import json
import torch
import torch.nn as nn
from PIL import Image, ImageDraw
import numpy as np
import random
import shutil

class TinyCNN(nn.Module):
    def __init__(self):
        super(TinyCNN, self).__init__()
        self.conv = nn.Conv2d(3, 16, 3)
        self.fc = nn.Linear(16 * 414 * 414, 3)
        
    def forward(self, x):
        x = torch.relu(self.conv(x))
        x = x.view(x.size(0), -1)
        return self.fc(x)

def generate_better_dataset(output_dir, num_images=50, poison=False):
    """Generates a realistic-looking dummy dataset deterministically."""
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    categories = [
        {"id": 1, "name": "soldier"},
        {"id": 2, "name": "tank"},
        {"id": 3, "name": "drone"}
    ]
    
    coco_data = {"images": [], "annotations": [], "categories": categories}
    metadata = {}
    
    contributors = ["alice_corp", "bob_defense", "charlie_intel", "unknown"]
    
    for i in range(num_images):
        img_id = i + 1
        filename = f"img_{img_id}.jpg"
        
        bg_color = (random.randint(50, 150), random.randint(80, 180), random.randint(50, 100))
        img = Image.new('RGB', (416, 416), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        cat_id = random.choice([1, 2, 3])
        x1 = random.randint(50, 250)
        y1 = random.randint(50, 250)
        width = random.randint(40, 100)
        height = random.randint(40, 100)
        
        if cat_id == 1:
            draw.rectangle([x1, y1, x1+width/2, y1+height], fill=(50, 50, 50))
        elif cat_id == 2:
            draw.rectangle([x1, y1, x1+width, y1+height/2], fill=(80, 90, 70))
        elif cat_id == 3:
            draw.ellipse([x1, y1, x1+width, y1+width], fill=(200, 200, 200))
            
        contributor = random.choice(contributors)
        
        # Poisoning Injection
        if poison:
            if i == 5: # Exact duplicate of img_1
                contributor = "charlie_intel"
                img.save(os.path.join(images_dir, filename))
                shutil.copy(os.path.join(images_dir, "img_1.jpg"), os.path.join(images_dir, filename))
            elif i == 10: # Near duplicate (Label flip)
                contributor = "charlie_intel"
                img_10 = Image.open(os.path.join(images_dir, "img_2.jpg"))
                img_10.save(os.path.join(images_dir, filename), quality=80) # Slight change -> near dup
                cat_id = (cat_id % 3) + 1 # Flip label
            elif i == 15: # OOD / Anomaly (Pure Red image)
                contributor = "charlie_intel"
                img = Image.new('RGB', (416, 416), color=(255, 0, 0))
                img.save(os.path.join(images_dir, filename))
            elif i == 20: # Corrupt image
                contributor = "charlie_intel"
                with open(os.path.join(images_dir, filename), "wb") as f:
                    f.write(b"NOT_AN_IMAGE_DATA")
            else:
                img.save(os.path.join(images_dir, filename))
        else:
            img.save(os.path.join(images_dir, filename))
            
        coco_data["images"].append({"id": img_id, "file_name": filename, "width": 416, "height": 416})
        metadata[filename] = {"contributor": contributor}
        
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
        
    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)
        
    print(f"[+] Generated dataset at {output_dir} (Poisoned: {poison})")

def generate_dummy_model(output_path, backdoor=False):
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    model = TinyCNN()
    
    if backdoor:
        with torch.no_grad():
            model.fc.weight[0, :500] = 800.0 # Synthetic weight-space manipulation
            
    torch.save(model.state_dict(), output_path)
    print(f"[+] Generated Synthetic Weight-Space Manipulation Scenario Model at {output_path} (Backdoored: {backdoor})")

if __name__ == "__main__":
    print("=== Generating KAVACH-VISION Demo Artifacts ===")
    generate_better_dataset("demo_data/clean_dataset", num_images=50, poison=False)
    generate_dummy_model("demo_data/clean_model.pt", backdoor=False)
    
    generate_better_dataset("demo_data/poisoned_dataset", num_images=50, poison=True)
    generate_dummy_model("demo_data/backdoored_model.pt", backdoor=True)
    print("=== Complete! ===")
