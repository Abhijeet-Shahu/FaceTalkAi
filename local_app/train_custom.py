# train_custom.py
"""
Train face recognition with YOUR photos
"""

import face_recognition
import pickle
import os
import cv2
import numpy as np
from datetime import datetime

class CustomTrainer:
    def __init__(self):
        self.known_encodings = []
        self.known_names = []
        self.stats = {
            'total_images': 0,
            'successful': 0,
            'failed': 0,
            'people': {}
        }
    
    def train_from_folder(self, dataset_path="dataset"):
        """Train from dataset folder"""
        
        print("\n" + "="*60)
        print("👤 CUSTOM FACE TRAINING")
        print("="*60)
        
        if not os.path.exists(dataset_path):
            print(f"❌ Create folder '{dataset_path}' first!")
            self.create_template()
            return False
        
        # Process each person
        for person_name in os.listdir(dataset_path):
            person_folder = os.path.join(dataset_path, person_name)
            
            if not os.path.isdir(person_folder):
                continue
            
            print(f"\n📁 Processing: {person_name}")
            
            # Get images
            images = [f for f in os.listdir(person_folder) 
                     if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            
            self.stats['people'][person_name] = len(images)
            self.stats['total_images'] += len(images)
            
            # Process each image
            for image_file in images:
                image_path = os.path.join(person_folder, image_file)
                
                try:
                    # Load image
                    image = face_recognition.load_image_file(image_path)
                    
                    # Find faces
                    face_locations = face_recognition.face_locations(image)
                    
                    if len(face_locations) > 0:
                        # Get encodings
                        encodings = face_recognition.face_encodings(image, face_locations)
                        
                        if encodings:
                            self.known_encodings.append(encodings[0])
                            self.known_names.append(person_name)
                            self.stats['successful'] += 1
                            print(f"  ✅ {image_file}")
                        else:
                            self.stats['failed'] += 1
                            print(f"  ❌ No encoding: {image_file}")
                    else:
                        self.stats['failed'] += 1
                        print(f"  ❌ No face: {image_file}")
                        
                except Exception as e:
                    self.stats['failed'] += 1
                    print(f"  ❌ Error: {image_file} - {e}")
        
        # Save model
        if self.known_encodings:
            self.save_model()
            self.show_stats()
            return True
        else:
            print("\n❌ No faces found to train!")
            return False
    
    def save_model(self):
        """Save trained model"""
        # Save as pickle
        data = {
            'encodings': self.known_encodings,
            'names': self.known_names,
            'trained_date': datetime.now().isoformat(),
            'stats': self.stats
        }
        
        # Create models directory
        os.makedirs("models", exist_ok=True)
        
        # Save main model
        with open("models/face_model.pickle", "wb") as f:
            pickle.dump(data, f)
        
        # Also save in root for compatibility
        with open("encodings.pickle", "wb") as f:
            pickle.dump({"encodings": self.known_encodings, "names": self.known_names}, f)
        
        print(f"\n💾 Model saved to models/face_model.pickle")
    
    def show_stats(self):
        """Show training statistics"""
        print("\n" + "="*60)
        print("📊 TRAINING SUMMARY")
        print("="*60)
        print(f"Total images:    {self.stats['total_images']}")
        print(f"Successful:      {self.stats['successful']}")
        print(f"Failed:          {self.stats['failed']}")
        print(f"Success rate:    {(self.stats['successful']/self.stats['total_images']*100):.1f}%")
        
        print("\n👥 People trained:")
        for person, count in self.stats['people'].items():
            person_success = self.known_names.count(person)
            print(f"  • {person}: {person_success}/{count} images")
    
    def create_template(self):
        """Create dataset template"""
        print("\n📁 Creating dataset template...")
        
        template_people = ["Abhijeet", "Rohit", "Akshay", "Guest"]
        
        for person in template_people:
            person_folder = os.path.join("dataset", person)
            os.makedirs(person_folder, exist_ok=True)
            
            # Create README
            with open(os.path.join(person_folder, "README.txt"), "w") as f:
                f.write(f"Add photos of {person} here\n")
                f.write("Requirements:\n")
                f.write("- Clear front-facing photos\n")
                f.write("- Good lighting\n")
                f.write("- JPG or PNG format\n")
        
        print("✅ Template created!")
        print(f"📁 Add your photos to dataset/[YourName]/ folder")
        print("   Then run this script again")

if __name__ == "__main__":
    trainer = CustomTrainer()
    trainer.train_from_folder()