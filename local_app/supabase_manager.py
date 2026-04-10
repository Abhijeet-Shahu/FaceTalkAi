# supabase_manager.py
from datetime import datetime
import json

import numpy as np
from supabase import Client, create_client


class SupabaseManager:
    def __init__(self, url, key):
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY are required.")

        self.url = url
        self.key = key
        self.supabase: Client = create_client(url, key)
        print("Connected to Supabase")

    def _safe_execute(self, query, action_name):
        try:
            return query.execute()
        except Exception as e:
            print(f"{action_name} error: {e}")
            return None

    def _normalize_face_encoding(self, face_encoding):
        if face_encoding is None:
            return None
        if isinstance(face_encoding, np.ndarray):
            return json.dumps(face_encoding.tolist())
        if isinstance(face_encoding, str):
            return face_encoding
        return json.dumps(face_encoding)

    def _apply_user_scope(self, query, user_id):
        if user_id is None:
            return query.is_("user_id", "null")
        return query.eq("user_id", user_id)

    def add_user(self, name, face_encoding, email=None, department=None, profile_image=None):
        """
        Add new user with face encoding.
        """
        user_data = {
            "name": name,
            "email": email,
            "department": department,
            "registration_date": datetime.now().isoformat(),
            "face_encoding": self._normalize_face_encoding(face_encoding),
            "profile_image_url": profile_image,
        }

        result = self._safe_execute(
            self.supabase.table("users").insert(user_data),
            "Add user",
        )
        if result and result.data:
            user_id = result.data[0]["id"]
            pref_data = {
                "user_id": user_id,
                "theme": "dark",
                "voice_speed": 1.0,
                "language": "en",
                "notification_enabled": True,
            }
            self._safe_execute(
                self.supabase.table("user_preferences").insert(pref_data),
                "Create user preferences",
            )
            print(f"User {name} added with ID: {user_id}")
            return user_id
        return None

    def find_user_by_face(self, face_encoding, threshold=0.6):
        """
        Find user by comparing face encoding.
        """
        result = self._safe_execute(
            self.supabase.table("users").select("id, name, face_encoding"),
            "Find user by face",
        )
        if not result or not result.data:
            return None

        input_encoding = face_encoding if isinstance(face_encoding, np.ndarray) else np.array(face_encoding)
        best_match = None
        min_distance = float("inf")

        for user in result.data:
            stored_face_encoding = user.get("face_encoding")
            if not stored_face_encoding:
                continue

            try:
                stored_encoding = np.array(json.loads(stored_face_encoding))
                distance = np.linalg.norm(input_encoding - stored_encoding)
                if distance < min_distance and distance < threshold:
                    min_distance = distance
                    best_match = {
                        "id": user["id"],
                        "name": user["name"],
                        "confidence": 1 - min(1, distance),
                    }
            except Exception:
                continue

        return best_match

    def log_attendance(self, user_id, action, confidence=None, face_image=None):
        """
        Log user attendance/activity.
        """
        log_data = {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "confidence": confidence,
            "face_image_url": face_image,
        }

        result = self._safe_execute(
            self.supabase.table("attendance_logs").insert(log_data),
            "Log attendance",
        )
        self._safe_execute(
            self.supabase.table("users")
            .update({"last_seen": datetime.now().isoformat()})
            .eq("id", user_id),
            "Update last seen",
        )
        return result.data if result else None

    def log_unknown_face(self, face_image=None):
        """
        Log unknown face detection.
        """
        log_data = {
            "action": "unknown_face",
            "timestamp": datetime.now().isoformat(),
            "confidence": 0,
            "face_image_url": face_image,
        }
        result = self._safe_execute(
            self.supabase.table("attendance_logs").insert(log_data),
            "Log unknown face",
        )
        return result.data if result else None

    def save_chat_message(self, user_id, message, response):
        """
        Save chatbot conversation.
        """
        try:
            chat_data = {
                "user_id": user_id,
                "message": message,
                "response": response,
                "timestamp": datetime.now().isoformat(),
            }
            result = self._safe_execute(
                self.supabase.table("chatbot_conversations").insert(chat_data),
                "Save chat",
            )
            return result.data if result else None
        except Exception as e:
            print(f"Chat save error: {e}")
            return None

    def get_recent_chat_memory(self, user_id=None, limit=10):
        """
        Retrieve recent chat memory for personalization.
        """
        try:
            query = self.supabase.table("chatbot_conversations") \
                .select("message,response,timestamp") \
                .order("timestamp", desc=True) \
                .limit(limit)

            query = self._apply_user_scope(query, user_id)

            result = query.execute()
            return list(reversed(result.data)) if result.data else []
        except Exception as e:
            print(f"Memory fetch error: {e}")
            return []

    def get_chat_history(self, user_id=None, limit=100):
        """
        Retrieve saved chat history for the active user.
        """
        try:
            query = self.supabase.table("chatbot_conversations") \
                .select("message,response,timestamp,user_id") \
                .order("timestamp", desc=False) \
                .limit(limit)

            query = self._apply_user_scope(query, user_id)

            result = query.execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Chat history fetch error: {e}")
            return []

    def save_voice_command(self, user_id, command, response, success):
        """
        Save voice command history.
        """
        command_data = {
            "user_id": user_id,
            "command": command,
            "response": response,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        }
        result = self._safe_execute(
            self.supabase.table("voice_commands").insert(command_data),
            "Save voice command",
        )
        return result.data if result else None

    def get_user_preferences(self, user_id):
        """
        Get user preferences.
        """
        result = self._safe_execute(
            self.supabase.table("user_preferences").select("*").eq("user_id", user_id),
            "Get user preferences",
        )
        return result.data[0] if result and result.data else None

    def update_user_preferences(self, user_id, preferences):
        """
        Update user preferences.
        """
        result = self._safe_execute(
            self.supabase.table("user_preferences").update(preferences).eq("user_id", user_id),
            "Update user preferences",
        )
        return result.data if result else None

    def get_attendance_report(self, user_id=None, start_date=None, end_date=None):
        """
        Get attendance report.
        """
        query = self.supabase.table("attendance_logs").select("*, users(name, department)")
        if user_id:
            query = query.eq("user_id", user_id)
        if start_date:
            query = query.gte("timestamp", start_date)
        if end_date:
            query = query.lte("timestamp", end_date)

        result = self._safe_execute(query.order("timestamp", desc=True), "Attendance report")
        return result.data if result else []

    def get_recent_activity(self, limit=10):
        """
        Get recent activity logs.
        """
        result = self._safe_execute(
            self.supabase.table("attendance_logs")
            .select("*, users(name)")
            .order("timestamp", desc=True)
            .limit(limit),
            "Recent activity",
        )
        return result.data if result else []


if __name__ == "__main__":
    db = SupabaseManager(
        url="https://your-project-ref.supabase.co",
        key="your-anon-key",
    )
    print("Testing connection...")
    users = db.supabase.table("users").select("*").execute()
    print(f"Found {len(users.data)} users in database")
