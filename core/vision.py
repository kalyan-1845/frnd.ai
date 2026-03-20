import os

try:
    import cv2
except Exception:
    cv2 = None

try:
    import face_recognition
except Exception:
    face_recognition = None

# Path to the authorized user's photo
USER_PHOTO_PATH = "user_face.jpg"
_known_encoding = None


def _vision_dependencies_ok() -> bool:
    return bool(cv2 and face_recognition)

def load_user_face():
    """Loads and encodes the user's face from a file."""
    global _known_encoding

    if not _vision_dependencies_ok():
        print("[Vision] Dependencies missing (opencv-python / face-recognition). Vision features disabled.")
        return

    if os.path.exists(USER_PHOTO_PATH):
        try:
            image = face_recognition.load_image_file(USER_PHOTO_PATH)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                _known_encoding = encodings[0]
                print("[Vision] User face loaded successfully.")
            else:
                print("[Vision] No face found in user_face.jpg.")
        except Exception as e:
            print(f"[Vision Error] Could not load face: {e}")
    else:
        print("[Vision] Warning: user_face.jpg not found. Face verification disabled.")

def verify_user():
    """
    Captures a frame from the camera and checks if it matches the known user.
    Returns: (is_match, message)
    """
    if not _vision_dependencies_ok():
        return False, "Vision dependencies are not installed (opencv-python / face-recognition)."

    if _known_encoding is None:
        load_user_face()
        if _known_encoding is None:
            return False, "Setup required: Please verify your face first."

    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        return False, "Camera unavailable."

    print("[Vision] Verifying user...")
    ret, frame = video_capture.read()
    video_capture.release()

    if not ret:
        return False, "Failed to capture image."

    # Convert BGR (OpenCV) to RGB (face_recognition)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Detect faces
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for encoding in face_encodings:
        matches = face_recognition.compare_faces([_known_encoding], encoding, tolerance=0.6)
        if matches[0]:
            return True, "User verified successfully."

    return False, "Access denied: Face not recognized."

def capture_user_face():
    """Helper to capture the initial photo for setup."""
    if not _vision_dependencies_ok():
        return False, "Vision dependencies are not installed (opencv-python / face-recognition)."

    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        return False, "Camera unavailable."
        
    print("[Vision] Look at the camera to register your face...")
    ret, frame = video_capture.read()
    video_capture.release()
    
    if ret:
        cv2.imwrite(USER_PHOTO_PATH, frame)
        print(f"[Vision] Saved {USER_PHOTO_PATH}.")
        load_user_face() # Reload
        return True, "Face registered."
    return False, "Capture failed."

def check_user_attention():
    """
    Checks if the user is looking at the screen (Face detected).
    Returns: (is_looking, message)
    """
    if not _vision_dependencies_ok():
        return False, "Vision dependencies are not installed (opencv-python / face-recognition)."

    video_capture = cv2.VideoCapture(0)
    if not video_capture.isOpened():
        return False, "Camera unavailable."
        
    ret, frame = video_capture.read()
    video_capture.release()
    
    if not ret:
        return False, "Capture failed."
        
    # Quick face detect
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    
    if face_locations:
        return True, "User is present."
    return False, "User not detected."
