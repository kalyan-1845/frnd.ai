import threading
import time
import math
from core.logger import log_event, log_error

_CURRENT_EMOTION = "Neutral"
_VISION_RUNNING = False

def get_current_emotion() -> str:
    """Returns the globally locked current emotion state from the webcam feed."""
    return _CURRENT_EMOTION

def _vision_daemon():
    global _CURRENT_EMOTION, _VISION_RUNNING
    
    try:
        import cv2
        import mediapipe as mp
        
        # Defensive check for broken MediaPipe installations
        if not hasattr(mp, "solutions"):
             from mediapipe.python import solutions
             mp.solutions = solutions

        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        
        cap = cv2.VideoCapture(0)
        # Suppress OpenCV warnings locally
        cap.set(cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY)
        
        if not cap.isOpened():
            _CURRENT_EMOTION = "Camera Offline"
            return
            
        log_event("VisionTracker", "MediaPipe emotion tracking online.")
        
        while _VISION_RUNNING:
            success, image = cap.read()
            if not success:
                time.sleep(1)
                continue
                
            # Process face purely internally
            image.flags.writeable = False
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(image)
            
            emotion = "Neutral"
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    # Calculate simple distance between mouth corners
                    left_mouth = face_landmarks.landmark[61]
                    right_mouth = face_landmarks.landmark[291]
                    top_lip = face_landmarks.landmark[13]
                    bottom_lip = face_landmarks.landmark[14]
                    
                    mouth_width = math.hypot(left_mouth.x - right_mouth.x, left_mouth.y - right_mouth.y)
                    mouth_height = math.hypot(top_lip.x - bottom_lip.x, top_lip.y - bottom_lip.y)
                    
                    # Ratios for happy/sad 
                    if mouth_width > 0.15 and mouth_height < 0.05:
                        emotion = "Smiling / Happy"
                    elif mouth_height > 0.1:
                        emotion = "Surprised / Talking"
                    elif left_mouth.y > bottom_lip.y and right_mouth.y > bottom_lip.y:
                        emotion = "Frowning / Stressed"
                        
            _CURRENT_EMOTION = emotion
            time.sleep(0.5) # Sample at 2 FPS to save CPU completely
            
    except ImportError:
        _CURRENT_EMOTION = "Requires OpenCV/MediaPipe"
    except Exception as e:
        log_error("VisionTrackerCrash", e)
        _CURRENT_EMOTION = "Vision Error (Suppressed)"
    finally:
        try:
            if 'cap' in locals() and cap is not None:
                cap.release()
        except: pass

def start_vision_tracker():
    """Starts the ultra-lightweight background emotion crawler. Guaranteed not to crash the main app."""
    global _VISION_RUNNING
    if _VISION_RUNNING: return
    _VISION_RUNNING = True
    t = threading.Thread(target=_vision_daemon, daemon=True)
    t.start()
    
def stop_vision_tracker():
    global _VISION_RUNNING
    _VISION_RUNNING = False
