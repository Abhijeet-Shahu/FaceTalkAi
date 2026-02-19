# test_model.py
"""
Test your trained models before running main app
"""

import json  # MISSING IMPORT
import face_recognition
import pickle
import cv2
import numpy as np
import os
from datetime import datetime
import random  # For random.choice

class ModelTester:
    def __init__(self):
        self.face_model = None
        self.chatbot_intents = None
    
    def test_face_recognition(self, test_image=None):
        """Test face recognition model"""
        print("\n" + "="*50)
        print("🔍 TESTING FACE RECOGNITION")
        print("="*50)
        
        # Load model
        model_path = "models/face_model.pickle"
        if not os.path.exists(model_path):
            model_path = "encodings.pickle"
        
        if os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                self.face_model = pickle.load(f)
            print(f"✅ Model loaded: {len(self.face_model['names'])} encodings")
        else:
            print("❌ No face model found! Train first.")
            return
        
        # If no test image provided, use camera
        if not test_image:
            self.test_with_camera()
        else:
            self.test_with_image(test_image)
    
    def test_with_camera(self):
        """Test with live camera"""
        print("\n📸 Testing with camera (press 'q' to quit)")
        
        cap = cv2.VideoCapture(0)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Find faces
            face_locations = face_recognition.face_locations(rgb_small)
            face_encodings = face_recognition.face_encodings(rgb_small, face_locations)
            
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Scale back
                top, right, bottom, left = top*4, right*4, bottom*4, left*4
                
                # Compare
                if self.face_model['encodings']:
                    distances = face_recognition.face_distance(
                        self.face_model['encodings'], face_encoding
                    )
                    best_match = np.argmin(distances)
                    
                    if distances[best_match] < 0.6:
                        name = self.face_model['names'][best_match]
                        color = (0, 255, 0)
                    else:
                        name = "Unknown"
                        color = (0, 0, 255)
                    
                    # Draw
                    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                    cv2.putText(frame, name, (left, top-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            cv2.imshow("Face Recognition Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
    
    def test_with_image(self, image_path):
        """Test with single image"""
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            return
        
        # Load and process image
        image = face_recognition.load_image_file(image_path)
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        face_locations = face_recognition.face_locations(image)
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        print(f"\n📸 Testing: {image_path}")
        print(f"Found {len(face_locations)} face(s)")
        
        for i, (face_encoding, face_location) in enumerate(zip(face_encodings, face_locations)):
            if self.face_model['encodings']:
                distances = face_recognition.face_distance(
                    self.face_model['encodings'], face_encoding
                )
                best_match = np.argmin(distances)
                
                if distances[best_match] < 0.6:
                    name = self.face_model['names'][best_match]
                    confidence = (1 - distances[best_match]) * 100
                    print(f"Face {i+1}: {name} ({confidence:.1f}%)")
                else:
                    print(f"Face {i+1}: Unknown")
    
    def test_chatbot(self):
        """Test chatbot with sample queries"""
        print("\n" + "="*50)
        print("💬 TESTING CHATBOT")
        print("="*50)
        
        # Load intents
        if os.path.exists("my_intents.json"):
            with open("my_intents.json", 'r') as f:
                intents = json.load(f)  # Now json is defined
            print(f"✅ Loaded {len(intents['intents'])} intents")
        else:
            print("⚠️ No intents file found")
            return
        
        # Test queries
        test_queries = [
            "hello",
            "who are you",
            "who is abhijeet",
            "what is facetalk",
            "your college name",
            "bye"
        ]
        
        print("\n🧪 Testing sample queries:")
        for query in test_queries:
            response = self.match_intent(query, intents)
            print(f"\nQ: {query}")
            print(f"A: {response}")
    
    def match_intent(self, query, intents):
        """Match query to intent"""
        query = query.lower()
        
        for intent in intents['intents']:
            for pattern in intent['patterns']:
                if pattern.lower() in query:
                    return random.choice(intent['responses'])  # random is imported now
        
        return "I'm still learning! Can you rephrase that?"

if __name__ == "__main__":
    tester = ModelTester()
    
    print("🎯 FACETALK AI TESTER")
    print("1. Test Face Recognition (camera)")
    print("2. Test Face Recognition (image)")
    print("3. Test Chatbot")
    print("4. Test All")
    
    choice = input("\nChoice (1-4): ").strip()
    
    if choice == '1':
        tester.test_face_recognition()
    elif choice == '2':
        img = input("Enter image path: ").strip()
        tester.test_face_recognition(img)
    elif choice == '3':
        tester.test_chatbot()
    elif choice == '4':
        tester.test_face_recognition()
        tester.test_chatbot()