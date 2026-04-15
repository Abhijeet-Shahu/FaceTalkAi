"""
Utility script to validate the trained face-recognition model and chatbot intents.

Run from either the project root or from `local_app/`.
"""

from __future__ import annotations

import json
import os
import pickle
import random
from pathlib import Path

import cv2
import face_recognition
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
MODEL_CANDIDATES = (
    BASE_DIR / "models" / "face_model.pickle",
    BASE_DIR / "encodings.pickle",
    PROJECT_ROOT / "models" / "face_model.pickle",
    PROJECT_ROOT / "encodings.pickle",
)
INTENTS_CANDIDATES = (
    BASE_DIR / "my_intents.json",
    PROJECT_ROOT / "my_intents.json",
)


class ModelTester:
    def __init__(self) -> None:
        self.face_model = None
        self.model_path = None
        self.intents_path = None

    def find_existing_path(self, candidates: tuple[Path, ...]) -> Path | None:
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def load_face_model(self) -> bool:
        """Load the face model from the project."""
        self.model_path = self.find_existing_path(MODEL_CANDIDATES)
        if self.model_path is None:
            print("No face model found. Train the model first.")
            return False

        try:
            with self.model_path.open("rb") as model_file:
                data = pickle.load(model_file)
        except Exception as exc:
            print(f"Failed to load face model: {exc}")
            return False

        encodings = data.get("encodings", [])
        names = data.get("names", [])

        if not isinstance(encodings, list) or not isinstance(names, list):
            print("Face model format is invalid.")
            return False

        if len(encodings) != len(names):
            print("Face model is inconsistent: encodings and names count do not match.")
            return False

        self.face_model = {
            "encodings": encodings,
            "names": names,
            "trained_date": data.get("trained_date"),
            "stats": data.get("stats", {}),
        }
        print(f"Loaded model from: {self.model_path}")
        print(f"Total encodings: {len(encodings)}")
        return True

    def load_intents(self) -> dict | None:
        """Load chatbot intents from the project."""
        self.intents_path = self.find_existing_path(INTENTS_CANDIDATES)
        if self.intents_path is None:
            print("No intents file found.")
            return None

        try:
            with self.intents_path.open("r", encoding="utf-8") as intents_file:
                data = json.load(intents_file)
        except Exception as exc:
            print(f"Failed to load intents: {exc}")
            return None

        if not isinstance(data, dict) or "intents" not in data or not isinstance(data["intents"], list):
            print("Intents file format is invalid.")
            return None

        print(f"Loaded intents from: {self.intents_path}")
        print(f"Total intents: {len(data['intents'])}")
        return data

    def test_face_recognition(self, test_image: str | None = None) -> None:
        """Test face recognition model using a camera or single image."""
        print("\n" + "=" * 50)
        print("TESTING FACE RECOGNITION")
        print("=" * 50)

        if not self.load_face_model():
            return

        if test_image:
            self.test_with_image(test_image)
        else:
            self.test_with_camera()

    def test_with_camera(self) -> None:
        """Test with live camera."""
        if not self.face_model or not self.face_model["encodings"]:
            print("No face encodings available in the model.")
            return

        print("\nCamera test started. Press 'q' to quit.")
        cap = cv2.VideoCapture(0)

        if not cap.isOpened():
            print("Could not open camera.")
            return

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to read frame from camera.")
                    break

                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                face_locations = face_recognition.face_locations(rgb_small)
                face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    top, right, bottom, left = top * 4, right * 4, bottom * 4, left * 4
                    name, confidence = self.identify_face(face_encoding)
                    color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
                    label = f"{name} ({confidence:.1f}%)" if name != "Unknown" else name

                    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                    cv2.putText(
                        frame,
                        label,
                        (left, max(top - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        color,
                        2,
                    )

                cv2.imshow("Face Recognition Test", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

    def test_with_image(self, image_path: str) -> None:
        """Test with a single image."""
        image_file = Path(image_path)
        if not image_file.is_absolute():
            image_file = (Path.cwd() / image_file).resolve()

        if not image_file.exists():
            print(f"Image not found: {image_file}")
            return

        if not self.face_model or not self.face_model["encodings"]:
            print("No face encodings available in the model.")
            return

        image = face_recognition.load_image_file(str(image_file))
        face_locations = face_recognition.face_locations(image)
        face_encodings = face_recognition.face_encodings(image, face_locations)

        print(f"\nTesting image: {image_file}")
        print(f"Found {len(face_locations)} face(s)")

        if not face_encodings:
            print("No encodable faces found in the image.")
            return

        for index, face_encoding in enumerate(face_encodings, start=1):
            name, confidence = self.identify_face(face_encoding)
            if name == "Unknown":
                print(f"Face {index}: Unknown")
            else:
                print(f"Face {index}: {name} ({confidence:.1f}%)")

    def identify_face(self, face_encoding: np.ndarray) -> tuple[str, float]:
        """Return the best-matching name and confidence percentage."""
        known_encodings = self.face_model["encodings"]
        distances = face_recognition.face_distance(known_encodings, face_encoding)
        best_match_index = int(np.argmin(distances))
        best_distance = float(distances[best_match_index])

        if best_distance < 0.6:
            confidence = max(0.0, min(100.0, (1.0 - best_distance) * 100.0))
            return self.face_model["names"][best_match_index], confidence

        return "Unknown", 0.0

    def test_chatbot(self) -> None:
        """Test chatbot with sample queries."""
        print("\n" + "=" * 50)
        print("TESTING CHATBOT")
        print("=" * 50)

        intents = self.load_intents()
        if not intents:
            return

        test_queries = [
            "hello",
            "who are you",
            "who is abhijeet",
            "what is facetalk",
            "your college name",
            "bye",
        ]

        print("\nTesting sample queries:")
        for query in test_queries:
            response = self.match_intent(query, intents)
            print(f"\nQ: {query}")
            print(f"A: {response}")

    def match_intent(self, query: str, intents: dict) -> str:
        """Match query to the first compatible custom intent."""
        query_lower = query.lower()

        for intent in intents["intents"]:
            patterns = intent.get("patterns", [])
            responses = intent.get("responses", [])
            if not patterns or not responses:
                continue

            for pattern in patterns:
                if pattern.lower() in query_lower:
                    return random.choice(responses)

        return "I'm still learning! Can you rephrase that?"


def prompt_image_path() -> str | None:
    image_path = input("Enter image path: ").strip()
    return image_path or None


if __name__ == "__main__":
    tester = ModelTester()

    print("FACETALK AI TESTER")
    print("1. Test Face Recognition (camera)")
    print("2. Test Face Recognition (image)")
    print("3. Test Chatbot")
    print("4. Test All")

    choice = input("\nChoice (1-4): ").strip()

    if choice == "1":
        tester.test_face_recognition()
    elif choice == "2":
        selected_image = prompt_image_path()
        if selected_image:
            tester.test_face_recognition(selected_image)
        else:
            print("No image path provided.")
    elif choice == "3":
        tester.test_chatbot()
    elif choice == "4":
        tester.test_face_recognition()
        tester.test_chatbot()
    else:
        print("Invalid choice.")
