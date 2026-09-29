import os
import json
from pathlib import Path

class DatasetParser:
    """Parses COCO and YOLO datasets for integrity analysis."""
    
    @staticmethod
    def parse_coco(annotation_path):
        """
        Parses a COCO JSON annotation file.
        Returns a mapping of image filename to a list of labels/categories.
        """
        if not os.path.exists(annotation_path):
            return {}
            
        try:
            with open(annotation_path, 'r') as f:
                data = json.load(f)
                
            img_map = {img['id']: img['file_name'] for img in data.get('images', [])}
            annotations = data.get('annotations', [])
            
            parsed = {}
            for ann in annotations:
                img_name = img_map.get(ann['image_id'])
                if img_name:
                    if img_name not in parsed:
                        parsed[img_name] = []
                    parsed[img_name].append(ann['category_id'])
            
            return parsed
        except Exception as e:
            print(f"[!] Error parsing COCO: {e}")
            return {}

    @staticmethod
    def parse_yolo(labels_dir, images_dir):
        """
        Parses YOLO txt files in a directory.
        Returns a mapping of image filename to a list of class IDs.
        """
        parsed = {}
        if not os.path.exists(labels_dir):
            return parsed
            
        try:
            for label_file in os.listdir(labels_dir):
                if label_file.endswith('.txt'):
                    base_name = label_file[:-4]
                    # Check common image extensions
                    img_name = None
                    for ext in ['.jpg', '.jpeg', '.png']:
                        if os.path.exists(os.path.join(images_dir, base_name + ext)):
                            img_name = base_name + ext
                            break
                            
                    if not img_name:
                        img_name = base_name + ".jpg" # fallback
                        
                    with open(os.path.join(labels_dir, label_file), 'r') as f:
                        lines = f.readlines()
                        
                    classes = []
                    for line in lines:
                        parts = line.strip().split()
                        if parts:
                            classes.append(int(parts[0]))
                            
                    parsed[img_name] = classes
            return parsed
        except Exception as e:
            print(f"[!] Error parsing YOLO: {e}")
            return {}
