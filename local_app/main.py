import cv2
import face_recognition
import pickle

data = pickle.load(open("encodings.pickle", "rb"))
cap = cv2.VideoCapture(0)

process_this_frame = True
face_locations = []
face_names = []

while True:
    ret, frame = cap.read()
    if not ret:
        print("Camera frame not received")
        break

    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb_small_frame = small_frame[:, :, ::-1]

    if process_this_frame:
        face_locations = face_recognition.face_locations(
            rgb_small_frame, model="hog"
        )
        encodings = face_recognition.face_encodings(
            rgb_small_frame, face_locations
        )

        face_names = []

        for encoding in encodings:
            matches = face_recognition.compare_faces(
                data["encodings"], encoding
            )
            name = "Unknown"

            if True in matches:
                matchedIdx = matches.index(True)
                name = data["names"][matchedIdx]

            face_names.append(name)

    process_this_frame = not process_this_frame

    for (top, right, bottom, left), name in zip(face_locations, face_names):
        top *= 2
        right *= 2
        bottom *= 2
        left *= 2

        cv2.rectangle(frame, (left, top), (right, bottom),
                      (0, 255, 0), 2)

        cv2.putText(frame, name, (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (0, 255, 0), 2)

    cv2.imshow("FaceTalk AI", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
