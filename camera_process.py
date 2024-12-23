import cv2
import threading
import time
from ultralytics import YOLO
import requests
from Modules.redis_manager import redis_client
from Modules.config import *

model = YOLO("yolov8n.pt")
model.fuse()

cameras = {}
camera_threads = {}

def process_camera(camera_id, rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print(f"[ERROR] Unable to open camera stream for {camera_id}. RTSP URL: {rtsp_url}")
        return  

    last_detection_time = 0
    last_frame_time = time.time()

    if not redis_client.exists(f"human_count:{camera_id}"):
        redis_client.set(f"human_count:{camera_id}", 0)

    last_human_count = int(redis_client.get(f"human_count:{camera_id}"))

    while camera_id in cameras:
        ret, frame = cap.read()

        if not ret:
            if time.time() - last_frame_time >= TIMEOUT:
                print(f"[INFO] Timeout reached for camera {camera_id}.")
                break
            time.sleep(1)
            continue

        last_frame_time = time.time()
        current_time = time.time()
        if current_time - last_detection_time >= DETECTION_INTERVAL:
            last_detection_time = current_time
            frame = cv2.resize(frame, (800, 600))
            results = model(frame, verbose=False)
            detections = results[0].boxes.data.cpu().numpy()

            human_count = sum(int(detection[5] == 0) for detection in detections)
            if human_count != last_human_count:
                redis_client.set(f"human_count:{camera_id}", human_count)
                last_human_count = human_count

                telemetry_data = {
                    "device_id": camera_id,
                    "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(current_time)),
                    "message": f"Human Count: {human_count}"
                }
                try:
                    response = requests.post(TELEMETRY_ENDPOINT, json=telemetry_data)
                    if response.status_code != 200:
                        print(f"[ERROR] Failed to send telemetry. Status: {response.status_code}")
                except Exception as e:
                    print(f"[ERROR] Exception while sending telemetry: {str(e)}")

    cap.release()
    print(f"[INFO] Camera {camera_id} processing stopped.")
    retry_camera(camera_id, rtsp_url)

def retry_camera(camera_id, rtsp_url):
    while camera_id in cameras:
        print(f"[INFO] Retrying camera {camera_id}...")
        cap = cv2.VideoCapture(rtsp_url)
        if cap.isOpened():
            thread = threading.Thread(target=process_camera, args=(camera_id, rtsp_url), daemon=True)
            camera_threads[camera_id] = thread
            thread.start()
            break
        time.sleep(CHECK_INTERVAL)

def initialize_cameras():
    initialized_cameras = []  # List to store initialized camera IDs
    for key in redis_client.keys("group:*"):
        cameras_data = redis_client.hgetall(key)
        for camera_id, rtsp_url in cameras_data.items():
            print(f"[INFO] Initializing camera {camera_id} with RTSP URL: {rtsp_url}")
            cameras[camera_id] = rtsp_url
            initialized_cameras.append(camera_id)
            thread = threading.Thread(target=process_camera, args=(camera_id, rtsp_url), daemon=True)
            camera_threads[camera_id] = thread
            thread.start()

    print("[INFO] All cameras initialized from Redis.")
    print(f"[INFO] Initialized cameras with threads: {', '.join(initialized_cameras)}")
