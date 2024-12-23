from flask import Flask
import threading
from Modules.redis_manager import restore_redis_backup, save_redis_backup
from Modules.camera_process import initialize_cameras
from Modules.api import api_blueprint

app = Flask(__name__)
app.register_blueprint(api_blueprint)  # Register API routes

if __name__ == "__main__":
    restore_redis_backup()  # Restore Redis data from the backup file
    initialize_cameras()  # Initialize cameras before starting the app

    # Start the Redis backup thread
    backup_thread = threading.Thread(target=save_redis_backup, daemon=True)
    backup_thread.start()

    app.run(host="0.0.0.0", port=5050)
