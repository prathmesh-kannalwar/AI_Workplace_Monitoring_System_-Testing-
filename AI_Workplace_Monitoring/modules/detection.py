from ultralytics import YOLO
import torch
import cv2


class PeopleDetector:

    PERSON_CLASS_ID = 0

    def __init__(self, model_path="yolov8n.pt", conf_threshold=0.5, resize_width=None):

        # Select device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = YOLO(model_path)
        self.model.to(self.device)

        self.conf_threshold = conf_threshold
        self.resize_width = resize_width

    def preprocess(self, frame):
        """
        Optional resizing for performance
        """
        if self.resize_width is None:
            return frame

        height, width = frame.shape[:2]
        ratio = self.resize_width / width
        new_height = int(height * ratio)

        return cv2.resize(frame, (self.resize_width, new_height))

    def detect_people(self, frame):

        if frame is None:
            return []

        frame = self.preprocess(frame)

        results = self.model(frame, verbose=False)

        detections = []

        for result in results:
            for box in result.boxes:

                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                if (
                    class_id == self.PERSON_CLASS_ID
                    and confidence > self.conf_threshold
                ):

                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": confidence
                    })

        return detections
