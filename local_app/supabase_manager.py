# supabase_manager.py (updated for simplified schema)
from supabase import create_client, Client
import numpy as np
import json
from datetime import datetime
import base64

class SupabaseManager:
    def __init__(self, url, key):
        self.url = url
        self.key = key
        self.supabase: Client = create_client(url, key)
        print("✅ Connected to Supabase")
    
    def add_user(self, name, face_encoding, email=None, department=None, profile_image=None):
        """
        Add new user with face encoding
        """
        # Convert numpy array to JSON string for storage
        if isinstance(face_encoding, np.ndarray):
            face_encoding_str = json.dumps(face_encoding.tolist())
        else:
            face_encoding_str = json.dumps(face_encoding)
        
        user_data = {
            'name': name,
            'email': email,
            'department': department,
            'registration_date': datetime.now().isoformat(),
            'face_encoding': face_encoding_str,
            'profile_image_url': profile_image
        }
        
        result = self.supabase.table('users').insert(user_data).execute()
        
        if result.data:
            user_id = result.data[0]['id']
            
            # Create default preferences
            pref_data = {
                'user_id': user_id,
                'theme': 'dark',
                'voice_speed': 1.0,
                'language': 'en',
                'notification_enabled': True
            }
            self.supabase.table('user_preferences').insert(pref_data).execute()
            
            print(f"✅ User {name} added with ID: {user_id}")
            return user_id
        return None
    
    def find_user_by_face(self, face_encoding, threshold=0.6):
        """
        Find user by comparing face encoding
        """
        # Get all users
        result = self.supabase.table('users').select('id, name, face_encoding').execute()
        
        if not result.data:
            return None
        
        # Convert input encoding to numpy array
        if isinstance(face_encoding, np.ndarray):
            input_encoding = face_encoding
        else:
            input_encoding = np.array(face_encoding)
        
        best_match = None
        min_distance = float('inf')
        
        for user in result.data:
            if user['face_encoding']:
                try:
                    # Parse stored encoding
                    stored_list = json.loads(user['face_encoding'])
                    stored_encoding = np.array(stored_list)
                    
                    # Calculate Euclidean distance
                    distance = np.linalg.norm(input_encoding - stored_encoding)
                    
                    if distance < min_distance and distance < threshold:
                        min_distance = distance
                        best_match = {
                            'id': user['id'],
                            'name': user['name'],
                            'confidence': 1 - min(1, distance)  # Normalize confidence
                        }
                except:
                    continue  # Skip if encoding is corrupted
        
        return best_match
    
    def log_attendance(self, user_id, action, confidence=None, face_image=None):
        """
        Log user attendance/activity
        """
        log_data = {
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'confidence': confidence,
            'face_image_url': face_image
        }
        
        result = self.supabase.table('attendance_logs').insert(log_data).execute()
        
        # Update user's last_seen
        self.supabase.table('users').update({
            'last_seen': datetime.now().isoformat()
        }).eq('id', user_id).execute()
        
        return result.data
    
    def log_unknown_face(self, face_image=None):
        """
        Log unknown face detection
        """
        log_data = {
            'action': 'unknown_face',
            'timestamp': datetime.now().isoformat(),
            'confidence': 0,
            'face_image_url': face_image
        }
        
        result = self.supabase.table('attendance_logs').insert(log_data).execute()
        return result.data
    
    def save_chat_message(self, user_id, message, response):
        """
        Save chatbot conversation
        """
        try:
            chat_data = {
                'user_id': user_id,
                'message': message,
                'response': response,
                'timestamp': datetime.now().isoformat()
            }
            result = self.supabase.table('chatbot_conversations').insert(chat_data).execute()
            return result.data
        except Exception as e:
            print(f"Chat save error: {e}")
            return None

    def get_recent_chat_memory(self, user_id=None, limit=10):
        """
        Retrieve recent chat memory for personalization.
        """
        try:
            query = self.supabase.table('chatbot_conversations') \
                .select('message,response,timestamp') \
                .order('timestamp', desc=True) \
                .limit(limit)

            if user_id is not None:
                query = query.eq('user_id', user_id)

            result = query.execute()
            return list(reversed(result.data)) if result.data else []
        except Exception as e:
            print(f"Memory fetch error: {e}")
            return []
    
    def save_voice_command(self, user_id, command, response, success):
        """
        Save voice command history
        """
        command_data = {
            'user_id': user_id,
            'command': command,
            'response': response,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        result = self.supabase.table('voice_commands').insert(command_data).execute()
        return result.data
    
    def get_user_preferences(self, user_id):
        """
        Get user preferences
        """
        result = self.supabase.table('user_preferences') \
            .select('*') \
            .eq('user_id', user_id) \
            .execute()
        
        return result.data[0] if result.data else None
    
    def update_user_preferences(self, user_id, preferences):
        """
        Update user preferences
        """
        result = self.supabase.table('user_preferences') \
            .update(preferences) \
            .eq('user_id', user_id) \
            .execute()
        
        return result.data
    
    def get_attendance_report(self, user_id=None, start_date=None, end_date=None):
        """
        Get attendance report
        """
        query = self.supabase.table('attendance_logs') \
            .select('*, users(name, department)')
        
        if user_id:
            query = query.eq('user_id', user_id)
        
        if start_date:
            query = query.gte('timestamp', start_date)
        
        if end_date:
            query = query.lte('timestamp', end_date)
        
        result = query.order('timestamp', desc=True).execute()
        return result.data
    
    def get_recent_activity(self, limit=10):
        """
        Get recent activity logs
        """
        result = self.supabase.table('attendance_logs') \
            .select('*, users(name)') \
            .order('timestamp', desc=True) \
            .limit(limit) \
            .execute()
        
        return result.data

# Test the connection
if __name__ == "__main__":
    # Replace with your actual credentials
    db = SupabaseManager(
        url="https://your-project-ref.supabase.co",
        key="your-anon-key"
    )
    
    print("\n🔍 Testing connection...")
    
    # Test: Get all users
    users = db.supabase.table('users').select('*').execute()
    print(f"📊 Found {len(users.data)} users in database")
    
    print("\n✅ Supabase manager ready!")
