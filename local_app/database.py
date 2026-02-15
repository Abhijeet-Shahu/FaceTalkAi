# database.py
from supabase_manager import SupabaseManager
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.db = SupabaseManager(
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_KEY')
        )
    
    def __getattr__(self, name):
        # Pass any method calls to the underlying db
        return getattr(self.db, name)