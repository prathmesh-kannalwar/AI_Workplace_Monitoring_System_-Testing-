import time
import math

# -----------------------------
# Thresholds (Updated As Requested)
# -----------------------------
OBSERVATION_TIME = 60          # 1 minute ignore alerts
IDLE_TIME_THRESHOLD = 120      # 2 minutes no movement
SUSPICIOUS_TIME_THRESHOLD = 180  # 3 minutes total presence
MOVEMENT_THRESHOLD = 5
CROWD_DISTANCE_THRESHOLD = 50
CROWD_COUNT_THRESHOLD = 3
ALERT_COOLDOWN = 10            # Prevent alert spam

person_history = {}


def distance(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def analyse_behaviour(tracked_people):

    alerts = []
    centers = []

    active_ids = {p["id"] for p in tracked_people}

    # -----------------------------
    # Remove disappeared people
    # -----------------------------
    for pid in list(person_history.keys()):
        if pid not in active_ids:
            del person_history[pid]

    current_time = time.time()

    # -----------------------------
    # Process each tracked person
    # -----------------------------
    for person in tracked_people:

        pid = person["id"]
        center = person["center"]
        timestamp = person["timestamp"]

        centers.append((pid, center))

        # -----------------------------
        # Initialize New Person
        # -----------------------------
        if pid not in person_history:
            person_history[pid] = {
                "last_position": center,
                "last_move_time": timestamp,
                "first_seen": timestamp,
                "last_alert_time": {}
            }
            continue

        history = person_history[pid]

        prev_pos = history["last_position"]
        move_dist = distance(center, prev_pos)

        # -----------------------------
        # Movement Detection
        # -----------------------------
        if move_dist > MOVEMENT_THRESHOLD:
            history["last_move_time"] = timestamp
            history["last_position"] = center

        idle_time = timestamp - history["last_move_time"]
        total_time = timestamp - history["first_seen"]

        # -----------------------------
        # 1️⃣ Observation Window
        # -----------------------------
        if total_time < OBSERVATION_TIME:
            continue

        # -----------------------------
        # 2️⃣ Idle Detection (2 Minutes)
        # -----------------------------
        if idle_time >= IDLE_TIME_THRESHOLD:

            last_alert = history["last_alert_time"].get("IDLE", 0)

            if current_time - last_alert > ALERT_COOLDOWN:
                alerts.append({
                    "type": "IDLE",
                    "person_id": pid,
                    "duration": round(idle_time, 2)
                })

                history["last_alert_time"]["IDLE"] = current_time

        # -----------------------------
        # 3️⃣ Suspicious Standing (3 Minutes)
        # -----------------------------
        if total_time >= SUSPICIOUS_TIME_THRESHOLD:

            last_alert = history["last_alert_time"].get("SUSPICIOUS_STANDING", 0)

            if current_time - last_alert > ALERT_COOLDOWN:
                alerts.append({
                    "type": "SUSPICIOUS_STANDING",
                    "person_id": pid,
                    "duration": round(total_time, 2)
                })

                history["last_alert_time"]["SUSPICIOUS_STANDING"] = current_time

    # -----------------------------
    # Crowd Detection (Counts Actual People)
    # -----------------------------
    crowd_people = set()

    for i in range(len(centers)):
        pid1, c1 = centers[i]

        for j in range(i + 1, len(centers)):
            pid2, c2 = centers[j]

            if distance(c1, c2) < CROWD_DISTANCE_THRESHOLD:
                crowd_people.add(pid1)
                crowd_people.add(pid2)

    if len(crowd_people) >= CROWD_COUNT_THRESHOLD:
        alerts.append({
            "type": "CROWD_DETECTED",
            "count": len(crowd_people)
        })

    return alerts
