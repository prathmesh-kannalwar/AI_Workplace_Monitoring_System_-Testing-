import time
import threading
import queue
import hashlib
import json
import csv
import os
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

class AlertDeduplicator:
    """Prevents alert spam"""

    def __init__(self, time_window: int = 30):
        self.time_window = time_window
        self.alert_cache = {}
        self.lock = threading.Lock()

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
            alert_hash = self._generate_hash(alert)

            # Clean old entries
            expired = [k for k, (t, _) in self.alert_cache.items()
                      if current_time - t > self.time_window * 2]
            for k in expired:
                del self.alert_cache[k]

            if alert_hash in self.alert_cache:
                last_time, count = self.alert_cache[alert_hash]
                if current_time - last_time < self.time_window:
                    self.alert_cache[alert_hash] = (current_time, count + 1)
                    priority = AlertPriority.get_priority(alert.get("type", ""))
                    max_count = {"HIGH": 5, "MEDIUM": 3, "LOW": 1}[priority]
                    return count + 1 <= max_count, count + 1
                else:
                    self.alert_cache[alert_hash] = (current_time, 1)
                    return True, 1
            else:
                self.alert_cache[alert_hash] = (current_time, 1)
                return True, 1

class AlertLogger:
    """Lightweight alert logging system"""

    def __init__(self, log_dir: str = "logs"):
        self.deduplicator = AlertDeduplicator()
        self.alert_queue = queue.Queue(maxsize=100)
        self.running = False
        self.worker_thread = None
        self.log_dir = log_dir
        
        # Create logs directory
        os.makedirs(log_dir, exist_ok=True)
        self.alert_csv_file = f"{log_dir}/alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.csv_lock = threading.Lock()
        
        # Initialize CSV file with headers
        self._initialize_csv_file()

        # Statistics
        self.stats = {
            "total_alerts": 0,
            "high_priority": 0,
            "medium_priority": 0,
            "low_priority": 0,
            "duplicates_filtered": 0
        }

    def start(self):
        """Start the alert processing"""
        if self.running:
            return
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_alerts)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        logger.info("Alert logger started")

    def stop(self):
        """Stop the alert processing"""
        self.running = False
        if self.alert_queue:
            try:
                self.alert_queue.put(None, timeout=1)
            except:
                pass
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Alert logger stopped")

    def log_alert(self, alert: Dict):
        """Log an alert to the system"""
        try:
            if 'timestamp' not in alert:
                alert['timestamp'] = time.time()
            self.alert_queue.put(alert, timeout=1)
        except queue.Full:
            logger.warning("Alert queue full, dropping alert")

    def _process_alerts(self):
        """Process alerts from queue"""
        while self.running:
            try:
                alert = self.alert_queue.get(timeout=1)
                if alert is None:
                    break

                self.stats["total_alerts"] += 1

                # Check deduplication
                should_process, occurrence_count = self.deduplicator.should_process_alert(alert)
                if not should_process:
                    self.stats["duplicates_filtered"] += 1
                    continue

                # Get priority
                priority = AlertPriority.get_priority(alert.get('type', ''))
                self.stats[f"{priority.lower()}_priority"] += 1

                # Real-time notification
                timestamp = datetime.fromtimestamp(alert['timestamp']).strftime('%H:%M:%S')
                print(f"[{timestamp}] {priority} ALERT: {alert.get('type')} "
                      f"(Person {alert.get('person_id', 'N/A')}) - Occurrence #{occurrence_count}")

                # Log to console and CSV file
                logger.info(f"{priority} ALERT: {json.dumps(alert)}")
                self._save_alert_to_csv(alert, priority, occurrence_count)

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing alert: {e}")

    def _initialize_csv_file(self):
        """Initialize CSV file with headers"""
        try:
            with open(self.alert_csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Priority', 'Alert Type', 'Person ID', 
                    'Duration', 'Count', 'Occurrence', 'Saved At'
                ])
        except Exception as e:
            logger.error(f"Error initializing CSV file: {e}")
    
    def _save_alert_to_csv(self, alert: Dict, priority: str, occurrence_count: int):
        """Save alert to CSV file"""
        try:
            with self.csv_lock:
                with open(self.alert_csv_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        datetime.fromtimestamp(alert.get('timestamp', time.time())).strftime('%Y-%m-%d %H:%M:%S'),
                        priority,
                        alert.get('type', ''),
                        alert.get('person_id', ''),
                        alert.get('duration', ''),
                        alert.get('count', ''),
                        occurrence_count,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ])
        except Exception as e:
            logger.error(f"Error saving alert to CSV: {e}")

    def get_statistics(self) -> Dict:
        """Get alert statistics"""
        return self.stats.copy()

# Example usage
if __name__ == "__main__":
    logger = AlertLogger()
    logger.start()

    try:
        # Test alerts
        test_alerts = [
            {"type": "IDLE", "person_id": 1, "duration": 5.5},
            {"type": "CROWD_DETECTED", "count": 4},
            {"type": "SUSPICIOUS_STANDING", "person_id": 2, "duration": 8.2},
            {"type": "CROWD_DETECTED", "count": 5},  # Should be deduplicated
            {"type": "IDLE", "person_id": 1, "duration": 6.0},  # Should be deduplicated
        ]

        for alert in test_alerts:
            logger.log_alert(alert)
            time.sleep(1)

        time.sleep(3)
        print("\nStatistics:", logger.get_statistics())

    finally:
        logger.stop()
