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

        # -----------------------------
        # Server Room (LEFT - Full Height)
        # -----------------------------
        server_points = np.array([
            [0, 0],
            [self.frame_width * 0.33, 0],
            [self.frame_width * 0.33, self.frame_height],
            [0, self.frame_height]
        ], dtype=np.int32)

        self.restricted_areas.append({
            'name': 'Server Room',
            'points': server_points,
            'max_people': 0
        })

        # -----------------------------
        # Equipment Zone (RIGHT - Full Height)
        # -----------------------------
        equipment_points = np.array([
            [self.frame_width * 0.67, 0],
            [self.frame_width, 0],
            [self.frame_width, self.frame_height],
            [self.frame_width * 0.67, self.frame_height]
        ], dtype=np.int32)

        self.restricted_areas.append({
            'name': 'Equipment Zone',
            'points': equipment_points,
            'max_people': 1
        })

    def point_in_polygon(self, point, polygon_points):
        x, y = point
        return cv2.pointPolygonTest(polygon_points, (float(x), float(y)), False) >= 0

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

        overlay = frame.copy()

        for area in self.restricted_areas:
            points = area['points']
            name = area['name']

            # Transparent fill
            cv2.fillPoly(overlay, [points], (0, 0, 255))

            # Border
            cv2.polylines(frame, [points], True, (0, 0, 255), 2)

            centroid = points.mean(axis=0).astype(int)

            cv2.putText(frame, name, tuple(centroid),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Blend overlay
        alpha = 0.2
        frame = cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

        return frame

    def draw_centroids(self, frame, tracked_people):
        """DEBUG: Shows tracked centers"""

        for person in tracked_people:
            cx, cy = person["center"]
            cv2.circle(frame, (int(cx), int(cy)), 5, (255, 0, 0), -1)

        return frame

    def reset_frame_alerts(self):
        self.alerts_logged.clear()
