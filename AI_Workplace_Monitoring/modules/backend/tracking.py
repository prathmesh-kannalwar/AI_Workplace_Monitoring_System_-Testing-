import time
import numpy as np


class PeopleTracker:
    def __init__(self, iou_threshold=0.3, max_missing=30):
        """
        iou_threshold → Minimum IOU to match detections
        max_missing → Frames allowed before object is removed
        """
        self.next_id = 1
        self.tracks = {}
        self.iou_threshold = iou_threshold
        self.max_missing = max_missing

    # ---------------------------
    # Utility: Calculate IOU
    # ---------------------------
    def _iou(self, boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        inter_area = max(0, xB - xA) * max(0, yB - yA)

        boxA_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxB_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        union = boxA_area + boxB_area - inter_area

        if union == 0:
            return 0

        return inter_area / union

    # ---------------------------
    # Utility: Calculate Center
    # ---------------------------
    def _center(self, bbox):
        x1, y1, x2, y2 = bbox
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        return (cx, cy)

    # ---------------------------
    # Main Tracking Function
    # ---------------------------
    def update(self, detections):
        """
        Input → detection module output
        Output → tracked_objects list
        """

        current_time = time.time()
        updated_tracks = {}

        # Keep track of matched track IDs
        matched_ids = set()

        # Convert detections into easier format
        det_boxes = [det["bbox"] for det in detections]

        # ---------------------------
        # Match existing tracks
        # ---------------------------
        for track_id, track_data in self.tracks.items():

            best_iou = 0
            best_det_index = -1

            for i, det in enumerate(det_boxes):

                if i in matched_ids:
                    continue

                iou_score = self._iou(track_data["bbox"], det)

                if iou_score > best_iou:
                    best_iou = iou_score
                    best_det_index = i

            # If matched detection found
            if best_iou > self.iou_threshold and best_det_index != -1:

                det = detections[best_det_index]
                bbox = det["bbox"]

                updated_tracks[track_id] = {
                    "id": track_id,
                    "bbox": bbox,
                    "confidence": det["confidence"],
                    "center": self._center(bbox),
                    "timestamp": current_time,
                    "missing": 0
                }

                matched_ids.add(best_det_index)

            else:
                # Increase missing counter
                track_data["missing"] += 1

                if track_data["missing"] <= self.max_missing:
                    updated_tracks[track_id] = track_data

        # ---------------------------
        # Add New Tracks
        # ---------------------------
        for i, det in enumerate(detections):

            if i in matched_ids:
                continue

            bbox = det["bbox"]

            updated_tracks[self.next_id] = {
                "id": self.next_id,
                "bbox": bbox,
                "confidence": det["confidence"],
                "center": self._center(bbox),
                "timestamp": current_time,
                "missing": 0
            }

            self.next_id += 1

        # Update tracker state
        self.tracks = updated_tracks

        # ---------------------------
        # Prepare Output Format
        # ---------------------------
        tracked_objects = []

        for track in self.tracks.values():

            tracked_objects.append({
                "id": track["id"],
                "bbox": track["bbox"],
                "confidence": track["confidence"],
                "center": track["center"],
                "timestamp": track["timestamp"]
            })

        return tracked_objects
