import time
import math

IDLE_TIME_THRESHOLD = 3
SUSPICIOUS_TIME_THRESHOLD = 6
MOVEMENT_THRESHOLD = 5
CROWD_DISTANCE_THRESHOLD = 50
CROWD_COUNT_THRESHOLD = 3

person_history = {}

def distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def analyse_behaviour(tracked_people):
    alerts = []
    centers = []

    active_ids = {p["id"] for p in tracked_people}

    # Remove disappeared people
    for pid in list(person_history.keys()):
        if pid not in active_ids:
            del person_history[pid]

    for person in tracked_people:
        pid = person["id"]
        center = person["center"]
        current_time = person["timestamp"]
        centers.append(center)

        if pid not in person_history:
            person_history[pid] = {
                "last_position": center,
                "last_move_time": current_time,
                "first_seen": current_time
            }
            continue

        prev_pos = person_history[pid]["last_position"]
        move_dist = distance(center, prev_pos)

        if move_dist > MOVEMENT_THRESHOLD:
            person_history[pid]["last_move_time"] = current_time
            person_history[pid]["last_position"] = center

        idle_time = current_time - person_history[pid]["last_move_time"]
        total_time = current_time - person_history[pid]["first_seen"]

        if idle_time >= IDLE_TIME_THRESHOLD:
            alerts.append({
                "type": "IDLE",
                "person_id": pid,
                "duration": round(idle_time, 2)
            })

        if total_time >= SUSPICIOUS_TIME_THRESHOLD:
            alerts.append({
                "type": "SUSPICIOUS_STANDING",
                "person_id": pid,
                "duration": round(total_time, 2)
            })

    # Crowd detection
    close_count = 0
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            if distance(centers[i], centers[j]) < CROWD_DISTANCE_THRESHOLD:
                close_count += 1

    if close_count >= CROWD_COUNT_THRESHOLD:
        alerts.append({
            "type": "CROWD_DETECTED",
            "count": close_count
        })

    return alerts



if __name__ == "__main__":
    import time
    import random
    import cv2
    from tracking import get_tracked_objects  # tracking team's function

    cap = cv2.VideoCapture(0)
    
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break

    tracked_objects = get_tracked_objects(frame)

    behaviour_input = [
            {
                "id": obj["id"],
                "center": obj["center"],
                "timestamp": obj["timestamp"]
            }
            for obj in tracked_objects
        ]

    alerts = analyse_behaviour(behaviour_input)

    if alerts:
        print("ALERTS:", alerts)

    if cv2.waitKey(1) & 0xFF == 27:

        cap.release()

