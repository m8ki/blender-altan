import logging
import os
from flask import Flask, request, jsonify, Response
from k8s_provider import K8sProvider
from orchestrator_service import OrchestratorService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Provider and Orchestrator
orchestrator = None
try:
    provider = K8sProvider()
    orchestrator = OrchestratorService(provider)
    logger.info("Orchestrator initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Orchestrator: {e}")
    logger.error("Orchestrator will not be available. Ensure Kubernetes is configured properly.")


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "mode": "k8s"})

@app.route('/instance/<user_id>', methods=['GET'])
def get_instance(user_id):
    if not orchestrator:
        return jsonify({"error": "Orchestrator not initialized"}), 503
    try:
        info = orchestrator.get_instance_info(user_id)
        return jsonify(info)
    except Exception as e:
        logger.error(f"Error getting instance info: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/execute', methods=['POST'])
def execute_tool():
    data = request.json
    user_id = data.get('user_id')
    tool_name = data.get('tool_name')
    arguments = data.get('arguments')
    
    if not user_id or not tool_name:
        return jsonify({"error": "Missing user_id or tool_name"}), 400
        
    if not orchestrator:
        return jsonify({"error": "Orchestrator not initialized"}), 503
        
    try:
        response = orchestrator.execute_tool(user_id, tool_name, arguments)
        
        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type')
        )
        
    except Exception as e:
        logger.error(f"Orchestration error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/instance/<user_id>', methods=['DELETE'])
def despawn_instance(user_id):
    if not orchestrator:
        return jsonify({"error": "Orchestrator not initialized"}), 503
    try:
        success = orchestrator.despawn_instance(user_id)
        if success:
            return jsonify({"message": f"Instance for user {user_id} despawned successfully"}), 200
        else:
            return jsonify({"message": f"Instance for user {user_id} not found"}), 404
    except Exception as e:
        logger.error(f"Error despawning instance: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
