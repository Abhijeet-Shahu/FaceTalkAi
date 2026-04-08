# face_recognition_module.py
import face_recognition
import cv2
import numpy as np
from groq import Groq
import json
import base64
from datetime import datetime
import os
import time
import uuid

class FaceRecognizer:
    def __init__(self, db_manager, groq_api_key=None, on_unknown_face_callback=None):
        """
        Initialize Face Recognizer with Groq AI integration
        Optimized for faster processing with frame skipping
        """
        self.db = db_manager
        self.on_unknown_face_callback = on_unknown_face_callback
        self.known_encodings = []
        self.known_names = []
        self.known_ids = []
        self.known_face_data = []  # Store additional face data
        self.tolerance = 0.6
        self.auto_enroll_threshold = 0.48
        self.auto_enroll_cooldown_sec = 8
        self.last_auto_enroll_ts = 0.0
        self.last_seen_unknown_encoding = None
        self.demographics_cache = {}
        self.demographics_cache_ttl_sec = 8
        self.deepface_backends = ["opencv", "skip"]

        # Frame skipping for performance optimization
        self.frame_skip = 2  # Process every Nth frame (1=all, 2=every other, 3=every third)
        self.frame_counter = 0
        self.last_annotated_frame = None
        self.last_user_info = None
        self.scale_factor = 0.25  # Default downscale for face detection

        try:
            from deepface import DeepFace
            self.DeepFace = DeepFace
            self.demographics_enabled = True
            print("✅ DeepFace enabled for age/emotion")
        except Exception as e:
            self.DeepFace = None
            self.demographics_enabled = False
            print(f"⚠️ DeepFace not available, age/emotion disabled: {str(e)}")
            if "tf-keras" in str(e).lower() or "tf_keras" in str(e).lower():
                print("ℹ️ Fix: run `pip install tf-keras` in your active environment.")

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
            self.known_encodings = []
            self.known_names = []
            self.known_ids = []
            self.known_face_data = []
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
    
    def process_frame(self, frame, force_process=False):
        """
        Process a single frame for face recognition
        Uses frame skipping for better performance
        Returns: (annotated_frame, user_info)
        
        Args:
            frame: Input video frame
            force_process: If True, skip frame skipping logic
        """
        if frame is None:
            return None, None
        
        # Frame skipping logic for performance
        self.frame_counter += 1
        if not force_process and self.frame_skip > 1:
            if self.frame_counter % self.frame_skip != 0:
                # Return cached results with current frame overlay
                if self.last_annotated_frame is not None:
                    return frame.copy(), self.last_user_info
                return frame.copy(), None
        
        # Create a copy for annotation
        annotated_frame = frame.copy()
        
        # Resize frame for faster processing (configurable scale)
        small_frame = cv2.resize(frame, (0, 0), fx=self.scale_factor, fy=self.scale_factor)
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
                scale_back = int(1 / self.scale_factor)
                top = int(top * scale_back)
                right = int(right * scale_back)
                bottom = int(bottom * scale_back)
                left = int(left * scale_back)
                
                # Get face encoding for this face
                face_encoding = face_encodings[i]
                
                # Compare with known faces
                name, confidence, user_data = self.identify_face(face_encoding)
                
                # Draw rectangle and label
                face_roi = frame[max(0, top):max(0, bottom), max(0, left):max(0, right)]

                if name != "Unknown":
                    color = (0, 255, 0)  # Green for known
                    age, emotion, emotion_scores = self.estimate_demographics(face_roi, cache_key=str(user_data.get('id')))

                    # Prepare user info for return
                    if user_data:
                        user_info = {
                            'id': user_data.get('id'),
                            'name': name,
                            'email': user_data.get('email', ''),
                            'department': user_data.get('department', ''),
                            'confidence': confidence,
                            'age': age if age is not None else '--',
                            'emotion': emotion if emotion else '--',
                            'emotion_scores': emotion_scores
                        }
                else:
                    color = (0, 0, 255)  # Red for unknown
                    enrolled_user = self.auto_enroll_unknown(face_encoding, face_roi)
                    if enrolled_user:
                        name = enrolled_user.get("name", "New User")
                        confidence = max(confidence, 0.60)
                        color = (0, 165, 255)
                        age, emotion, emotion_scores = self.estimate_demographics(face_roi, cache_key=str(enrolled_user.get('id')))
                        user_info = {
                            'id': enrolled_user.get('id'),
                            'name': name,
                            'email': enrolled_user.get('email', ''),
                            'department': enrolled_user.get('department', 'Auto-Enrolled'),
                            'confidence': confidence,
                            'age': age if age is not None else '--',
                            'emotion': emotion if emotion else '--',
                            'emotion_scores': emotion_scores
                        }
                
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
        
        # Cache results for frame skipping
        self.last_annotated_frame = annotated_frame
        self.last_user_info = user_info
        
        return annotated_frame, user_info
    
    def set_frame_skip(self, skip_count):
        """Set how many frames to skip between processing (1=none, 2=every other, etc.)"""
        self.frame_skip = max(1, min(10, skip_count))
    
    def set_scale_factor(self, factor):
        """Set the downscale factor for face detection (0.25=quarter size, 0.5=half size)"""
        self.scale_factor = max(0.1, min(1.0, factor))
    
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
        confidence = max(0.0, min(1.0, (1 - best_distance / self.tolerance)))
        
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

    def estimate_demographics(self, face_roi, cache_key):
        if face_roi is None or face_roi.size == 0:
            return None, None, {}

        now_ts = time.time()
        cached = self.demographics_cache.get(cache_key)
        if cached and (now_ts - cached["ts"]) <= self.demographics_cache_ttl_sec:
            return cached["age"], cached["emotion"], cached.get("emotion_scores", {})

        if not self.demographics_enabled:
            return None, None, {}

        face_input = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB)

        for backend in self.deepface_backends:
            try:
                analysis = self.DeepFace.analyze(
                    img_path=face_input,
                    actions=["age", "emotion"],
                    enforce_detection=False,
                    detector_backend=backend
                )

                if isinstance(analysis, list):
                    analysis = analysis[0] if analysis else {}

                age = int(round(analysis.get("age"))) if analysis.get("age") is not None else None
                emotion = analysis.get("dominant_emotion")
                emotion_scores = analysis.get("emotion", {}) or {}

                if age is not None or emotion:
                    self.demographics_cache[cache_key] = {
                        "age": age,
                        "emotion": emotion,
                        "emotion_scores": emotion_scores,
                        "ts": now_ts
                    }
                    return age, emotion, emotion_scores
            except Exception:
                continue

        return None, None, {}

    def auto_enroll_unknown(self, face_encoding, face_roi):
        now_ts = time.time()
        if (now_ts - self.last_auto_enroll_ts) < self.auto_enroll_cooldown_sec:
            return None

        if self.last_seen_unknown_encoding is not None:
            try:
                distance = np.linalg.norm(face_encoding - self.last_seen_unknown_encoding)
                if distance < self.auto_enroll_threshold:
                    return None
            except Exception:
                pass

        try:
            # Trigger enrollment callback if available
            if self.on_unknown_face_callback:
                profile_image = self.encode_face_image(face_roi)
                self.on_unknown_face_callback({
                    'face_encoding': face_encoding,
                    'face_roi': face_roi,
                    'profile_image': profile_image,
                    'timestamp': now_ts
                })
                self.last_auto_enroll_ts = now_ts
                self.last_seen_unknown_encoding = np.array(face_encoding)
                # Return a temporary user until enrollment is confirmed
                return {
                    "id": f"pending_{int(now_ts)}",
                    "name": "New Person",
                    "email": "",
                    "department": "Pending Enrollment"
                }
            else:
                # Fallback to auto-enrollment if no callback
                profile_image = self.encode_face_image(face_roi)
                generated_name = f"Visitor-{datetime.now().strftime('%H%M%S')}-{str(uuid.uuid4())[:4]}"

                user_id = self.db.add_user(
                    name=generated_name,
                    face_encoding=face_encoding,
                    email=None,
                    department="Auto-Enrolled",
                    profile_image=profile_image
                )

                if not user_id:
                    return None

                self.known_encodings.append(np.array(face_encoding))
                self.known_names.append(generated_name)
                self.known_ids.append(user_id)
                self.known_face_data.append({
                    'name': generated_name,
                    'email': '',
                    'department': 'Auto-Enrolled'
                })

                self.last_auto_enroll_ts = now_ts
                self.last_seen_unknown_encoding = np.array(face_encoding)

                return {
                    "id": user_id,
                    "name": generated_name,
                    "email": "",
                    "department": "Auto-Enrolled"
                }
        except Exception as e:
            print(f"Auto-enroll error: {e}")
            return None

    def encode_face_image(self, face_roi):
        if face_roi is None or face_roi.size == 0:
            return None
        try:
            ok, encoded = cv2.imencode(".jpg", face_roi)
            if not ok:
                return None
            b64 = base64.b64encode(encoded.tobytes()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64}"
        except Exception:
            return None
    
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
