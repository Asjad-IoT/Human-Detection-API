import redis
import json
import os
import time
from Modules.config import REDIS_BACKUP_FILE, BACKUP_INTERVAL

redis_client = redis.StrictRedis(host='0.0.0.0', port=6379, decode_responses=True)

def save_redis_backup():
    """Save Redis data to a backup file periodically."""
    while True:
        try:
            keys = redis_client.keys("*")
            backup_data = {key: redis_client.hgetall(key) if redis_client.type(key) == "hash" else redis_client.get(key) for key in keys}
            with open(REDIS_BACKUP_FILE, "w") as backup_file:
                json.dump(backup_data, backup_file)
            print(f"[INFO] Redis data backed up to {REDIS_BACKUP_FILE}")
        except Exception as e:
            print(f"[ERROR] Failed to back up Redis data: {str(e)}")
        time.sleep(BACKUP_INTERVAL)

def restore_redis_backup():
    """Restore Redis data from a backup file."""
    if os.path.exists(REDIS_BACKUP_FILE):
        try:
            with open(REDIS_BACKUP_FILE, "r") as backup_file:
                backup_data = json.load(backup_file)
            for key, value in backup_data.items():
                if isinstance(value, dict):
                    redis_client.hmset(key, value)
                else:
                    redis_client.set(key, value)
            print(f"[INFO] Redis data restored from {REDIS_BACKUP_FILE}")
        except Exception as e:
            print(f"[ERROR] Failed to restore Redis data: {str(e)}")
