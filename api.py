from flask import Blueprint, request, jsonify
from Modules.redis_manager import redis_client
from Modules.camera_process import process_camera, cameras, camera_threads
import threading

api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/add_camera/<group_name>', methods=['POST'])
def add_camera(group_name="global"):
    data = request.json
    camera_id = data.get('camera_id')
    rtsp_url = data.get('rtsp_url')
    if not camera_id or not rtsp_url:
        return jsonify({"error": "Invalid camera data"}), 400

    redis_client.hset(f"group:{group_name}", camera_id, rtsp_url)
    redis_client.set(f"human_count:{camera_id}", 0)
    cameras[camera_id] = rtsp_url
    thread = threading.Thread(target=process_camera, args=(camera_id, rtsp_url), daemon=True)
    camera_threads[camera_id] = thread
    thread.start()

    return jsonify({"message": "Camera added successfully", "group": group_name})

@api_blueprint.route('/list_cameras/<group_name>', methods=['GET'])
def list_cameras(group_name="global"):
    cameras = redis_client.hgetall(f"group:{group_name}")
    return jsonify(cameras) if cameras else jsonify({"error": "No cameras found"}), 404

@api_blueprint.route('/remove_camera/<camera_id>', methods=['POST'])
def remove_camera(camera_id):
    for key in redis_client.keys("group:*"):
        if redis_client.hdel(key, camera_id):
            redis_client.delete(f"human_count:{camera_id}")
            cameras.pop(camera_id, None)
            if camera_id in camera_threads:
                camera_threads[camera_id].join()
            return jsonify({"message": f"Camera {camera_id} removed successfully"})
    return jsonify({"error": "Camera not found"}), 404

@api_blueprint.route('/get_human_count/<camera_id>', methods=['GET'])
def get_human_count(camera_id):
    human_count = redis_client.get(f"human_count:{camera_id}")
    return jsonify({"camera_id": camera_id, "human_count": human_count}) if human_count else jsonify({"error": "Not found"}), 404
