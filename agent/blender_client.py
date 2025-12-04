"""
Blender MCP Client for communicating with Blender MCP server via Orchestrator.
"""
import requests
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class BlenderMCPClient:
    """Client for communicating with Blender MCP server via Orchestrator."""
    
    def __init__(self, orchestrator_url: str):
        self.orchestrator_url = orchestrator_url
        self.tools = []
        # Tools are static for now, or we could fetch from a default instance
        # For simplicity, we'll hardcode or fetch from orchestrator if it supported it.
        # Let's assume we can still hit the orchestrator to list tools (which might proxy to a default/any instance)
        # OR just hardcode them for now since we know what they are.
        # Better: Try to fetch from orchestrator (which needs a list_tools endpoint or we just assume standard tools)
        # Let's keep the fetch logic but point to orchestrator if we add a list endpoint there, 
        # OR just use the known tool definitions.
        # For now, let's assume the orchestrator can proxy 'list_tools' to *some* instance.
        # But wait, we don't have a user_id here. 
        # Let's just hardcode the tools for this architectural step to avoid circular dependency on "which user?".
        self.tools = [
            {"name": "initialize_scene", "description": "Initialize a clean Blender scene", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "add_cube", "description": "Add a cube", "inputSchema": {"type": "object", "properties": {"location": {"type": "array", "items": {"type": "number"}}, "size": {"type": "number"}, "name": {"type": "string"}}}},
            {"name": "add_sphere", "description": "Add a sphere", "inputSchema": {"type": "object", "properties": {"location": {"type": "array", "items": {"type": "number"}}, "radius": {"type": "number"}, "name": {"type": "string"}}}},
            {"name": "add_cylinder", "description": "Add a cylinder", "inputSchema": {"type": "object", "properties": {"location": {"type": "array", "items": {"type": "number"}}, "radius": {"type": "number"}, "depth": {"type": "number"}, "name": {"type": "string"}}}},
            {"name": "set_object_color", "description": "Set object color", "inputSchema": {"type": "object", "properties": {"object_name": {"type": "string"}, "color": {"type": "array", "items": {"type": "number"}}}, "required": ["object_name"]}},
            {"name": "render_scene", "description": "Render scene", "inputSchema": {"type": "object", "properties": {"resolution_x": {"type": "integer"}, "resolution_y": {"type": "integer"}, "samples": {"type": "integer"}}}},
            {"name": "list_objects", "description": "List objects", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "clear_scene", "description": "Clear scene", "inputSchema": {"type": "object", "properties": {}}}
        ]
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Call a tool via Orchestrator."""
        try:
            response = requests.post(
                f"{self.orchestrator_url}/execute",
                json={
                    "user_id": user_id,
                    "tool_name": tool_name, 
                    "arguments": arguments
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract text content if wrapped
            if 'content' in result and len(result['content']) > 0:
                text_content = result['content'][0].get('text', '{}')
                return json.loads(text_content)
            
            return result
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Format tools for OpenRouter function calling."""
        formatted_tools = []
        for tool in self.tools:
            formatted_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["inputSchema"]
                }
            })
        return formatted_tools
