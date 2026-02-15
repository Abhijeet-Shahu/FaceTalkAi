# face_recognition_module.py
import face_recognition
import cv2
import numpy as np
from groq import Groq
import json
import base64
from datetime import datetime
import os

class FaceRecognizer:
    def __init__(self, db_manager, groq_api_key=None):
        """
        Initialize Face Recognizer with Groq AI integration
        """
        self.db = db_manager
        self.known_encodings = []
        self.known_names = []
        self.known_ids = []
        self.known_face_data = []  # Store additional face data
        self.tolerance = 0.6
        
        # Load known faces from database
        self.load_known_faces()
        
        # Initialize Groq client if API key provided
        if groq_api_key:
            self.groq_client = Groq(api_key=groq_api_key)
            self.ai_enabled = True
        else:
            self.ai_enabled = False
            print("⚠️ Groq AI disabled: No API key provided")
        
        # Face detection settings
        self.detection_model = "hog"  # 'hog' for speed, 'cnn' for accuracy
        self.upsample_times = 1
        
        print(f"✅ FaceRecognizer initialized with {len(self.known_encodings)} known faces")
    
    def load_known_faces(self):
        """Load all known face encodings from database"""
        try:
            users = self.db.supabase.table('users').select('id, name, face_encoding, email, department').execute()
            
            for user in users.data:
                if user['face_encoding']:
                    encoding = json.loads(user['face_encoding'])
                    self.known_encodings.append(np.array(encoding))
                    self.known_names.append(user['name'])
                    self.known_ids.append(user['id'])
                    self.known_face_data.append({
                        'name': user['name'],
                        'email': user.get('email', ''),
                        'department': user.get('department', '')
                    })
            
            print(f"📚 Loaded {len(self.known_encodings)} known faces from database")
            
        except Exception as e:
            print(f"❌ Error loading faces: {e}")
    
    def process_frame(self, frame):
        """
        Process a single frame for face recognition
        Returns: (annotated_frame, user_info)
        """
        if frame is None:
            return None, None
        
        # Create a copy for annotation
        annotated_frame = frame.copy()
        
        # Resize frame for faster processing (0.25x scale)
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Find faces
        face_locations = face_recognition.face_locations(
            rgb_small_frame, 
            model=self.detection_model,
            number_of_times_to_upsample=self.upsample_times
        )
        
        user_info = None
        
        if face_locations:
            # Get face encodings
            face_encodings = face_recognition.face_encodings(
                rgb_small_frame, 
                face_locations,
                num_jitters=1
            )
            
            # Process each face found
            for i, (top, right, bottom, left) in enumerate(face_locations):
                # Scale coordinates back to original frame size
                top = int(top * 4)
                right = int(right * 4)
                bottom = int(bottom * 4)
                left = int(left * 4)
                
                # Get face encoding for this face
                face_encoding = face_encodings[i]
                
                # Compare with known faces
                name, confidence, user_data = self.identify_face(face_encoding)
                
                # Draw rectangle and label
                if name != "Unknown":
                    color = (0, 255, 0)  # Green for known
                    
                    # Prepare user info for return
                    if user_data:
                        user_info = {
                            'id': user_data.get('id'),
                            'name': name,
                            'email': user_data.get('email', ''),
                            'department': user_data.get('department', ''),
                            'confidence': confidence
                        }
                else:
                    color = (0, 0, 255)  # Red for unknown
                
                # Draw face rectangle
                cv2.rectangle(annotated_frame, (left, top), (right, bottom), color, 2)
                
                # Draw label background
                label = f"{name} ({confidence:.1%})" if confidence else name
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.6, 1)[0]
                
                cv2.rectangle(annotated_frame, 
                             (left, bottom - 25), 
                             (left + label_size[0] + 10, bottom), 
                             color, cv2.FILLED)
                
                # Draw label text
                cv2.putText(annotated_frame, label, 
                           (left + 5, bottom - 7),
                           cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)
                
                # If AI is enabled, get additional insights
                if self.ai_enabled and name != "Unknown":
                    self.add_ai_insights(annotated_frame, frame[top:bottom, left:right], 
                                        (left, top), name)
        
        return annotated_frame, user_info
    
    def identify_face(self, face_encoding):
        """
        Identify a face by comparing with known encodings
        Returns: (name, confidence, user_data)
        """
        if len(self.known_encodings) == 0:
            return "Unknown", 0, None
        
        # Calculate distances to all known faces
        distances = face_recognition.face_distance(self.known_encodings, face_encoding)
        
        # Find the best match
        best_match_index = np.argmin(distances)
        best_distance = distances[best_match_index]
        
        # Calculate confidence (convert distance to confidence percentage)
        confidence = max(0, min(100, (1 - best_distance / self.tolerance) * 100))
        
        if best_distance < self.tolerance:
            name = self.known_names[best_match_index]
            user_data = {
                'id': self.known_ids[best_match_index],
                'name': name,
                'email': self.known_face_data[best_match_index].get('email', ''),
                'department': self.known_face_data[best_match_index].get('department', '')
            }
            return name, confidence, user_data
        else:
            return "Unknown", 0, None
    
    def add_ai_insights(self, frame, face_roi, position, name):
        """
        Add AI-generated insights about the face using Groq
        """
        try:
            # Save face ROI temporarily for analysis
            temp_path = f"temp_face_{datetime.now().timestamp()}.jpg"
            cv2.imwrite(temp_path, face_roi)
            
            # Analyze with Groq
            analysis = self.analyze_face_with_groq(temp_path, name)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Display insights on frame
            if analysis:
                x, y = position
                lines = analysis.split('\n')[:2]  # Show only first 2 lines
                for i, line in enumerate(lines):
                    cv2.putText(frame, line[:30], (x, y - 30 - i*15),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
                    
        except Exception as e:
            print(f"AI insights error: {e}")
    
    def analyze_face_with_groq(self, image_path, person_name):
        """
        Use Groq AI to analyze facial features and provide insights
        """
        if not self.ai_enabled:
            return None
        
        try:
            # Read and encode image
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create prompt for Groq
            prompt = f"""Analyze this face of {person_name} and provide:
            1. Estimated emotion (happy, neutral, serious, etc.)
            2. Confidence level of recognition
            3. Any notable features
            
            Keep response very brief, max 2 lines."""
            
            # Get response from Groq
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a facial analysis expert. Provide brief, accurate insights."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Groq analysis error: {e}")
            return None
    
    def register_new_face(self, frame, name, email=None, department=None):
        """
        Register a new face to the database
        """
        try:
            # Detect face in frame
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            
            if not face_locations:
                return {"success": False, "message": "No face detected in frame"}
            
            # Get face encoding
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            if not face_encodings:
                return {"success": False, "message": "Could not generate face encoding"}
            
            # Add to database
            user_id = self.db.add_user(
                name=name,
                face_encoding=face_encodings[0],
                email=email,
                department=department
            )
            
            if user_id:
                # Reload known faces
                self.load_known_faces()
                return {
                    "success": True, 
                    "message": f"User {name} registered successfully",
                    "user_id": user_id
                }
            else:
                return {"success": False, "message": "Database error"}
                
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def get_face_quality_score(self, face_image):
        """
        Analyze face image quality
        Returns score from 0-100
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
            
            # Check brightness
            brightness = np.mean(gray)
            brightness_score = min(100, (brightness / 128) * 100)
            
            # Check sharpness (using Laplacian variance)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(100, sharpness / 10)
            
            # Check face size (pixel count)
            face_size = face_image.shape[0] * face_image.shape[1]
            size_score = min(100, (face_size / (100 * 100)) * 100)
            
            # Combined score
            final_score = (brightness_score * 0.3 + 
                          sharpness_score * 0.4 + 
                          size_score * 0.3)
            
            return min(100, final_score)
            
        except Exception as e:
            print(f"Quality score error: {e}")
            return 50  # Default medium score