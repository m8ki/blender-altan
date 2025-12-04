import logging
import requests
from flask import Response

logger = logging.getLogger(__name__)

class OrchestratorService:
    def __init__(self, provider):
        self.provider = provider

    def get_instance_info(self, user_id):
        return self.provider.get_instance_info(user_id)

    def execute_tool(self, user_id, tool_name, arguments):
        # Get or create instance
        instance_url = self.provider.spawn_instance(user_id)
        if not instance_url:
             raise Exception("Failed to get Blender instance URL")
             
        logger.info(f"Routing tool {tool_name} for user {user_id} to {instance_url}")
        
        # Forward request
        response = requests.post(
            f"{instance_url}/tools/call",
            json={"name": tool_name, "arguments": arguments},
            timeout=60
        )
        
        return response

    def despawn_instance(self, user_id):
        """Despawn the Blender instance for the given user."""
        return self.provider.despawn_instance(user_id)
