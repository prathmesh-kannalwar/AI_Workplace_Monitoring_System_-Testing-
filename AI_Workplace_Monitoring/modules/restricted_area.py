import cv2
import numpy as np


class RestrictedAreaChecker:
    """Manages restricted areas"""

    def __init__(self, frame_shape):
        self.frame_height, self.frame_width = frame_shape[:2]
        self.restricted_areas = []
        self.alerts_logged = set()
        self._create_default_areas()

    def _create_default_areas(self):
        # Area 1: Bottom-right
        area1_points = np.array([
            [self.frame_width * 0.7, self.frame_height * 0.6],
            [self.frame_width, self.frame_height * 0.6],
            [self.frame_width, self.frame_height],
            [self.frame_width * 0.7, self.frame_height]
        ], dtype=np.int32)

        self.restricted_areas.append({
            'name': 'Equipment Zone',
            'points': area1_points,
            'max_people': 1
        })

        # Area 2: Top-right
        area2_points = np.array([
            [self.frame_width * 0.7, 0],
            [self.frame_width, 0],
            [self.frame_width, self.frame_height * 0.3],
            [self.frame_width * 0.7, self.frame_height * 0.3]
        ], dtype=np.int32)

        self.restricted_areas.append({
            'name': 'Server Room',
            'points': area2_points,
            'max_people': 0
        })

    def point_in_polygon(self, point, polygon_points):
        x, y = point
        return cv2.pointPolygonTest(polygon_points, (float(x), float(y)), False) >= 0

    # ✅ THIS METHOD MUST BE INSIDE THE CLASS
    def check_restricted_area(self, tracked_people):
        alerts = []

        for area in self.restricted_areas:
            area_name = area['name']
            area_points = area['points']
            max_allowed = area['max_people']

            people_in_area = []

            for person in tracked_people:
                person_id = person['id']
                centroid = person['center']

                if self.point_in_polygon(centroid, area_points):
                    people_in_area.append(person_id)

            if len(people_in_area) > max_allowed:
                alerts.append({
                    'type': 'RESTRICTED_AREA_BREACH',
                    'person_id': people_in_area[0],
                    'details': f'{len(people_in_area)} people in {area_name}'
                })

        return alerts

    def draw_areas(self, frame):
        for area in self.restricted_areas:
            points = area['points']
            name = area['name']
            cv2.polylines(frame, [points], True, (0, 0, 255), 2)
            centroid = points.mean(axis=0).astype(int)
            cv2.putText(frame, name, tuple(centroid),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        return frame

    def reset_frame_alerts(self):
        self.alerts_logged.clear()
