import face_recognition
import os
import pickle
import numpy as np

dataset_path = "dataset"

# Check if dataset folder exists
if not os.path.exists(dataset_path):
    print(f"Error: Dataset folder '{dataset_path}' not found!")
    exit()

known_encodings = []
known_names = []
failed_images = []

print("Starting training process...")

for person in os.listdir(dataset_path):
    person_folder = os.path.join(dataset_path, person)
    
    if not os.path.isdir(person_folder):
        continue
        
    print(f"\nProcessing {person}...")
    image_count = 0
    
    for image_name in os.listdir(person_folder):
        image_path = os.path.join(person_folder, image_name)
        
        # Check if file is an image
        if not image_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            print(f"  Skipping non-image file: {image_name}")
            continue
            
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Get face encodings
            encodings = face_recognition.face_encodings(image)
            
            if len(encodings) > 0:
                known_encodings.append(encodings[0])
                known_names.append(person)
                image_count += 1
                print(f"  ✓ {image_name}: Found {len(encodings)} face(s)")
            else:
                failed_images.append(image_path)
                print(f"  ✗ {image_name}: No face detected")
                
        except Exception as e:
            failed_images.append(image_path)
            print(f"  ✗ {image_name}: Error - {str(e)}")

print(f"\nTraining complete!")
print(f"Successfully processed: {len(known_encodings)} images")
print(f"Failed: {len(failed_images)} images")

if failed_images:
    print("\nFailed images:")
    for img in failed_images:
        print(f"  - {img}")

# Save encodings
data = {"encodings": known_encodings, "names": known_names}

with open("encodings.pickle", "wb") as f:
    pickle.dump(data, f)

print(f"\nEncodings saved to encodings.pickle")
print(f"Total unique people: {len(set(known_names))}")