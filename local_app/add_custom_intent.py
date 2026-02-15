# add_custom_intents.py
"""
Add YOUR custom intents and personality to the chatbot
"""

import json
import os

class CustomIntents:
    def __init__(self):
        self.intents_file = "my_intents.json"
        self.intents = self.load_or_create()
    
    def load_or_create(self):
        """Load existing intents or create new"""
        if os.path.exists(self.intents_file):
            with open(self.intents_file, 'r') as f:
                return json.load(f)
        else:
            # Default intents
            return {
                "intents": [
                    {
                        "tag": "greeting",
                        "patterns": ["hello", "hi", "hey", "good morning"],
                        "responses": [
                            "Hello! I'm FaceTalk AI, your personal assistant!",
                            "Hi there! Great to see you!"
                        ]
                    },
                    {
                        "tag": "about_me",
                        "patterns": ["who are you", "your name", "introduce yourself"],
                        "responses": [
                            "I'm FaceTalk AI, created for a final year project at BVIT!",
                            "I'm your intelligent assistant with face recognition!"
                        ]
                    }
                ]
            }
    
    def add_intent(self):
        """Add a new custom intent"""
        print("\n➕ ADD CUSTOM INTENT")
        print("-" * 40)
        
        tag = input("Intent name (e.g., 'about_college'): ").strip()
        if not tag:
            return
        
        # Get patterns
        print("\nEnter question patterns (one per line, empty line to stop):")
        patterns = []
        while True:
            pattern = input("  > ").strip()
            if not pattern:
                break
            patterns.append(pattern)
        
        # Get responses
        print("\nEnter responses (one per line, empty line to stop):")
        responses = []
        while True:
            response = input("  > ").strip()
            if not response:
                break
            responses.append(response)
        
        # Create intent
        intent = {
            "tag": tag,
            "patterns": patterns,
            "responses": responses
        }
        
        self.intents["intents"].append(intent)
        self.save()
        print(f"\n✅ Intent '{tag}' added successfully!")
    
    def add_team_intents(self):
        """Add intents about your team"""
        team_intents = [
            {
                "tag": "team_members",
                "patterns": [
                    "who are team members",
                    "who is in your team",
                    "your developers",
                    "who created you"
                ],
                "responses": [
                    "Our team consists of Abhijeet Shahu, Rohit Shinde, and Akshay Patel!",
                    "Abhijeet, Rohit, and Akshay are the three developers behind FaceTalk AI."
                ]
            },
            {
                "tag": "about_abhijeet",
                "patterns": [
                    "tell me about abhijeet",
                    "who is abhijeet",
                    "abhijeet's role"
                ],
                "responses": [
                    "Abhijeet Shahu is the lead developer working on face recognition and integration!",
                    "Abhijeet handles the face recognition module and overall system architecture."
                ]
            },
            {
                "tag": "about_rohit",
                "patterns": [
                    "tell me about rohit",
                    "who is rohit",
                    "rohit's role"
                ],
                "responses": [
                    "Rohit Shinde is working on the voice assistant module!",
                    "Rohit is responsible for voice recognition and text-to-speech features."
                ]
            },
            {
                "tag": "about_akshay",
                "patterns": [
                    "tell me about akshay",
                    "who is akshay",
                    "akshay's role"
                ],
                "responses": [
                    "Akshay Patel is working on the UI/UX and database integration!",
                    "Akshay handles the user interface and database connections."
                ]
            }
        ]
        
        for intent in team_intents:
            self.intents["intents"].append(intent)
        
        self.save()
        print("✅ Team intents added!")
    
    def add_college_intents(self):
        """Add intents about your college"""
        college_intents = [
            {
                "tag": "college_name",
                "patterns": [
                    "your college name",
                    "which college",
                    "college details",
                    "where are you from"
                ],
                "responses": [
                    "We're from Bharati Vidyapeeth's Institute of Technology, Navi Mumbai!",
                    "BVIT, Navi Mumbai - that's our home institution!"
                ]
            },
            {
                "tag": "guide",
                "patterns": [
                    "who is your guide",
                    "your mentor",
                    "project guide",
                    "mhatre sir"
                ],
                "responses": [
                    "Our project guide is Mr. Mithun Mhatre. He's been helping us throughout this project!",
                    "Mr. Mithun Mhatre is guiding our team with his valuable expertise."
                ]
            },
            {
                "tag": "department",
                "patterns": [
                    "which department",
                    "computer technology",
                    "your branch"
                ],
                "responses": [
                    "We're from the Department of Computer Technology!",
                    "Computer Technology department at BVIT."
                ]
            }
        ]
        
        for intent in college_intents:
            self.intents["intents"].append(intent)
        
        self.save()
        print("✅ College intents added!")
    
    def add_project_intents(self):
        """Add intents about the project"""
        project_intents = [
            {
                "tag": "what_is_facetalk",
                "patterns": [
                    "what is facetalk",
                    "about facetalk",
                    "tell me about facetalk",
                    "project details"
                ],
                "responses": [
                    "FaceTalk AI is an intelligent face recognition system combined with AI chatbot! It can recognize faces through camera and have natural conversations.",
                    "This project combines computer vision for face recognition with AI-powered conversation to create a personalized assistant."
                ]
            },
            {
                "tag": "how_it_works",
                "patterns": [
                    "how does it work",
                    "how facetalk works",
                    "working principle"
                ],
                "responses": [
                    "FaceTalk uses advanced algorithms to detect faces, create unique faceprints, and match them with our database. The AI chatbot uses Groq API for natural conversations!",
                    "We use OpenCV and face_recognition library for face detection, and Groq's LLM for intelligent conversations."
                ]
            },
            {
                "tag": "technologies",
                "patterns": [
                    "which technologies",
                    "tech stack",
                    "what technologies used",
                    "programming languages"
                ],
                "responses": [
                    "We use Python with OpenCV for face recognition, Groq API for AI conversations, Supabase for cloud database, and Tkinter for the user interface!",
                    "Tech stack: Python, OpenCV, face_recognition, Groq, Supabase, and Tkinter."
                ]
            }
        ]
        
        for intent in project_intents:
            self.intents["intents"].append(intent)
        
        self.save()
        print("✅ Project intents added!")
    
    def save(self):
        """Save intents to file"""
        with open(self.intents_file, 'w') as f:
            json.dump(self.intents, f, indent=2)
        print(f"💾 Saved to {self.intents_file}")
    
    def show_menu(self):
        """Show interactive menu"""
        while True:
            print("\n" + "="*50)
            print("🎨 CUSTOM CHATBOT INTENTS")
            print("="*50)
            print("1. Add custom intent")
            print("2. Add team intents (Abhijeet, Rohit, Akshay)")
            print("3. Add college intents (BVIT, Guide)")
            print("4. Add project intents (FaceTalk)")
            print("5. View all intents")
            print("6. Save and exit")
            
            choice = input("\nChoice (1-6): ").strip()
            
            if choice == '1':
                self.add_intent()
            elif choice == '2':
                self.add_team_intents()
            elif choice == '3':
                self.add_college_intents()
            elif choice == '4':
                self.add_project_intents()
            elif choice == '5':
                self.view_intents()
            elif choice == '6':
                print("✅ Exiting...")
                break
    
    def view_intents(self):
        """View all intents"""
        print("\n📋 CURRENT INTENTS:")
        for i, intent in enumerate(self.intents["intents"], 1):
            print(f"\n{i}. {intent['tag']}")
            print(f"   Patterns: {', '.join(intent['patterns'][:3])}...")
            print(f"   Responses: {intent['responses'][0][:50]}...")

if __name__ == "__main__":
    ci = CustomIntents()
    ci.show_menu()