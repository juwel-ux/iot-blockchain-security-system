# face_auth.py
import cv2
import face_recognition
import base64
import numpy as np
import os
import json

class FaceAuth:
    def __init__(self, face_db="face_db.json"):
        self.face_db = face_db
        self.known_faces = {}
        self.load_faces()
    
    def load_faces(self):
        if os.path.exists(self.face_db):
            with open(self.face_db, 'r') as f:
                data = json.load(f)
                for user_id, encoding in data.items():
                    self.known_faces[user_id] = np.array(encoding)
    
    def save_faces(self):
        data = {}
        for user_id, encoding in self.known_faces.items():
            data[user_id] = encoding.tolist()
        with open(self.face_db, 'w') as f:
            json.dump(data, f)
    
    def register_face(self, user_id, image_base64):
        # Decode base64 image
        image_data = base64.b64decode(image_base64.split(',')[1])
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Get face encoding
        face_locations = face_recognition.face_locations(img)
        face_encodings = face_recognition.face_encodings(img, face_locations)
        
        if face_encodings:
            self.known_faces[user_id] = face_encodings[0]
            self.save_faces()
            return True, "Face registered"
        return False, "No face detected"
    
    def verify_face(self, image_base64):
        # Decode base64 image
        image_data = base64.b64decode(image_base64.split(',')[1])
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Get face encoding
        face_locations = face_recognition.face_locations(img)
        face_encodings = face_recognition.face_encodings(img, face_locations)
        
        if not face_encodings:
            return False, "No face detected"
        
        # Compare with known faces
        for user_id, known_encoding in self.known_faces.items():
            matches = face_recognition.compare_faces([known_encoding], face_encodings[0])
            if matches[0]:
                return True, user_id
        
        return False, "Face not recognized"