import cv2
import time
from deep_sort_realtime.deepsort_tracker import DeepSort

# -------------------------------
# Initialize DeepSORT tracker
# -------------------------------
tracker = DeepSort(max_age=30)

# -------------------------------
# Camera (only to get frames)
# -------------------------------
cap = cv2.VideoCapture(0)

# Used to simulate changing detection input
x_offset = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w, _ = frame.shape
    x_offset = (x_offset + 4) % (w - 200)

    # ----------------------------------
    # INPUT FROM DETECTION TEAM
    # (Must change every frame to track)
    # Format: [x, y, width, height, confidence]
    # ----------------------------------
    detections_from_team = [
        [100 + x_offset, 80, 60, 150, 0.92],
        [300 - x_offset // 2, 90, 70, 160, 0.88]
    ]

    # ----------------------------------
    # Convert to DeepSORT format
    # ----------------------------------
    tracker_inputs = []
    for d in detections_from_team:
        x, y, w_box, h_box, conf = d
        tracker_inputs.append(([x, y, w_box, h_box], conf, "person"))

    # ----------------------------------
    # Run DeepSORT tracking
    # ----------------------------------
    tracks = tracker.update_tracks(tracker_inputs, frame=frame)

    # ----------------------------------
    # FINAL TRACKING OUTPUT
    # ----------------------------------
    tracked_output = []

    for track in tracks:
        if not track.is_confirmed():
            continue

        track_id = track.track_id
        x1, y1, x2, y2 = map(int, track.to_ltrb())

        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        tracked_output.append({
            "track_id": track_id,
            "bbox": [x1, y1, x2, y2],
            "center": [cx, cy],
            "confidence": track.det_conf,
            "timestamp": time.time()
        })

        # ----------------------------------
        # Visualization
        # ----------------------------------
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(
            frame,
            f"ID {track_id}",
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    # ----------------------------------
    # Print output (for integration)
    # ----------------------------------
    print(tracked_output)

    cv2.imshow("Person Tracking Module", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

# -------------------------------
# Cleanup
# -------------------------------
cap.release()
cv2.destroyAllWindows()
