# main.py
import time
import cv2

from modules.video_input import VideoStream
from modules.detection import PeopleDetector
from modules.tracking import PeopleTracker
from modules.behaviour import analyse_behaviour
from modules.restricted_area import RestrictedAreaChecker
from modules.alert_logger import AlertLogger

def main():
    # -----------------------------
    # Initialize modules
    # -----------------------------
    video = VideoStream(0)  # Webcam
    detector = PeopleDetector(model_path="yolov8n.pt", conf_threshold=0.5, resize_width=640)
    tracker = PeopleTracker(iou_threshold=0.3, max_missing=30)
    alert_logger = AlertLogger()
    alert_logger.start()

    # Read first frame to initialize restricted area checker
    ret, frame = video.get_frame()
    if not ret:
        print("Error: Cannot read from video source")
        return

    restricted_checker = RestrictedAreaChecker(frame.shape)

    # -----------------------------
    # Main loop
    # -----------------------------
    while True:
        ret, frame = video.get_frame()
        if not ret:
            break

        # 1️⃣ Detection
        detections = detector.detect_people(frame)

        # 2️⃣ Tracking
        tracked_objects = tracker.update(detections)

        # 3️⃣ Behaviour Analysis
        behaviour_input = [
            {
                "id": obj["id"],
                "center": obj["center"],
                "timestamp": obj["timestamp"]
            }
            for obj in tracked_objects
        ]
        alerts = analyse_behaviour(behaviour_input)
        for alert in alerts:
            alert_logger.log_alert(alert)

        # 4️⃣ Restricted Area Check
        # Convert tracked_objects to dict for RestrictedAreaChecker
        tracked_dict = {
            obj["id"]: {
                "centroid": obj["center"],
                "bbox": obj["bbox"]
            } for obj in tracked_objects
        }

        restricted_alerts = restricted_checker.check_restricted_area(tracked_dict)
        for alert in restricted_alerts:
            alert_logger.log_alert(alert)

        # 5️⃣ Visualization (optional)
        frame_vis = frame.copy()
        for obj in tracked_objects:
            x1, y1, x2, y2 = obj["bbox"]
            cid = obj["id"]
            cv2.rectangle(frame_vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame_vis, f"ID: {cid}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        frame_vis = restricted_checker.draw_areas(frame_vis)
        cv2.imshow("Workplace Monitor", frame_vis)

        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # -----------------------------
    # Cleanup
    # -----------------------------
    video.release()
    cv2.destroyAllWindows()
    alert_logger.stop()
    print("System stopped gracefully.")

if __name__ == "__main__":
    main()
