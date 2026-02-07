import time
import threading
import queue
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertPriority:
    """Alert priority levels"""

    HIGH = "HIGH_PRIORITY"
    MEDIUM = "MEDIUM_PRIORITY"
    LOW = "LOW_PRIORITY"

    PRIORITY_MAP = {
        "CROWD_DETECTED": HIGH,
        "SUSPICIOUS_STANDING": MEDIUM,
        "IDLE": LOW,
        "RESTRICTED_AREA_BREACH": HIGH,
        "UNAUTHORIZED_ACCESS": HIGH,
        "VIOLENCE_DETECTED": HIGH,
        "WEAPON_DETECTED": HIGH,
        "LOITERING": MEDIUM,
        "UNUSUAL_BEHAVIOR": MEDIUM,
        "NORMAL_ACTIVITY": LOW
    }

    @classmethod
    def get_priority(cls, alert_type: str) -> str:
        return cls.PRIORITY_MAP.get(alert_type, cls.MEDIUM)


# Priority limits (Used for deduplication control)
PRIORITY_LIMITS = {
    AlertPriority.HIGH: 5,
    AlertPriority.MEDIUM: 3,
    AlertPriority.LOW: 1
}


class AlertDeduplicator:
    """Prevents alert spam with cooldown support"""

    def __init__(self, time_window: int = 30):
        self.time_window = time_window
        self.alert_cache = {}
        self.cooldown_cache = {}
        self.lock = threading.Lock()

        # Cooldown periods (seconds)
        self.cooldowns = {
            "CROWD_DETECTED": 30   # Crowd alert only once every 30 sec
        }

    def _generate_hash(self, alert: Dict) -> str:
        hash_data = {
            "type": alert.get("type", ""),
            "person_id": alert.get("person_id", ""),
        }
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(hash_string.encode()).hexdigest()

    def should_process_alert(self, alert: Dict) -> Tuple[bool, int]:
        with self.lock:
            current_time = time.time()
            alert_type = alert.get("type", "")
            alert_hash = self._generate_hash(alert)

            # ---------- COOLDOWN LOGIC ----------
            if alert_type in self.cooldowns:
                cooldown_time = self.cooldowns[alert_type]

                last_trigger = self.cooldown_cache.get(alert_type, 0)

                if current_time - last_trigger < cooldown_time:
                    return False, 0

                self.cooldown_cache[alert_type] = current_time
                return True, 1

            # ---------- NORMAL DEDUP LOGIC ----------
            expired = [
                k for k, (t, _) in self.alert_cache.items()
                if current_time - t > self.time_window * 2
            ]
            for k in expired:
                del self.alert_cache[k]

            if alert_hash in self.alert_cache:
                last_time, count = self.alert_cache[alert_hash]

                if current_time - last_time < self.time_window:
                    new_count = count + 1
                    self.alert_cache[alert_hash] = (current_time, new_count)

                    priority = AlertPriority.get_priority(alert_type)
                    max_count = PRIORITY_LIMITS.get(priority, 3)

                    return new_count <= max_count, new_count

                else:
                    self.alert_cache[alert_hash] = (current_time, 1)
                    return True, 1

            else:
                self.alert_cache[alert_hash] = (current_time, 1)
                return True, 1



class AlertLogger:
    """Lightweight alert logging system"""

    def __init__(self):
        self.deduplicator = AlertDeduplicator()
        self.alert_queue = queue.Queue(maxsize=100)
        self.running = False
        self.worker_thread = None

        self.stats = {
            "total_alerts": 0,
            "high_priority": 0,
            "medium_priority": 0,
            "low_priority": 0,
            "duplicates_filtered": 0
        }

    def start(self):
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._process_alerts)
        self.worker_thread.daemon = True
        self.worker_thread.start()

        logger.info("Alert logger started")

    def stop(self):
        self.running = False

        try:
            self.alert_queue.put(None, timeout=1)
        except:
            pass

        if self.worker_thread:
            self.worker_thread.join(timeout=5)

        logger.info("Alert logger stopped")

    def log_alert(self, alert: Dict):
        try:
            if 'timestamp' not in alert:
                alert['timestamp'] = time.time()

            self.alert_queue.put(alert, timeout=1)

        except queue.Full:
            logger.warning("Alert queue full, dropping alert")

    def _process_alerts(self):
        while self.running or not self.alert_queue.empty():

            try:
                alert = self.alert_queue.get(timeout=1)

                if alert is None:
                    break

                self.stats["total_alerts"] += 1

                # Deduplication
                should_process, occurrence_count = self.deduplicator.should_process_alert(alert)

                if not should_process:
                    self.stats["duplicates_filtered"] += 1
                    continue

                # Priority detection
                priority = AlertPriority.get_priority(alert.get('type', ''))

                if priority == AlertPriority.HIGH:
                    self.stats["high_priority"] += 1
                elif priority == AlertPriority.MEDIUM:
                    self.stats["medium_priority"] += 1
                else:
                    self.stats["low_priority"] += 1

                # Print real-time alert
                timestamp = datetime.fromtimestamp(alert['timestamp']).strftime('%H:%M:%S')

                print(
                    f"[{timestamp}] {priority} ALERT: {alert.get('type')} "
                    f"(Person {alert.get('person_id', 'N/A')}) - Occurrence #{occurrence_count}"
                )

                logger.info(f"{priority} ALERT: {json.dumps(alert)}")

            except queue.Empty:
                continue

            except Exception as e:
                logger.error(f"Error processing alert: {e}")

    def get_statistics(self) -> Dict:
        return self.stats.copy()


# ---------------- TEST RUN ----------------
if __name__ == "__main__":
    alert_logger = AlertLogger()
    alert_logger.start()

    try:
        test_alerts = [
            {"type": "IDLE", "person_id": 1, "duration": 5.5},
            {"type": "CROWD_DETECTED", "count": 4},
            {"type": "SUSPICIOUS_STANDING", "person_id": 2, "duration": 8.2},
            {"type": "CROWD_DETECTED", "count": 5},
            {"type": "IDLE", "person_id": 1, "duration": 6.0},
        ]

        for alert in test_alerts:
            alert_logger.log_alert(alert)
            time.sleep(1)

        time.sleep(3)
        print("\nStatistics:", alert_logger.get_statistics())

    finally:
        alert_logger.stop()
