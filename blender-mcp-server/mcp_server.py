"""
MCP Server for Blender using FastMCP.
Exposes Blender operations as MCP tools.
"""
import sys
import os

# Add the script directory to Python path so we can import blender_operations
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastmcp import FastMCP, Image
import base64
from typing import Optional, List
import logging

# Import blender operations
import blender_operations as bops

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("BlenderMCP")


@mcp.tool()
def initialize_scene() -> str:
    """Initialize a clean Blender scene with camera and lighting"""
    result = bops.initialize_scene()
    return f"Scene initialized: {result['message']}"


@mcp.tool()
def add_cube(
    location: List[float] = [0, 0, 0],
    size: float = 2.0,
    name: Optional[str] = None
) -> str:
    """
    Add a cube to the 3D scene
    
    Args:
        location: Position [x, y, z] in 3D space
        size: Size of the cube
        name: Optional name for the object
    """
    result = bops.add_cube(
        location=tuple(location),
        size=size,
        name=name
    )
    return f"Added cube '{result['object_name']}' at {result['location']} with size {result['size']}"


@mcp.tool()
def add_sphere(
    location: List[float] = [0, 0, 0],
    radius: float = 1.0,
    name: Optional[str] = None
) -> str:
    """
    Add a sphere to the 3D scene
    
    Args:
        location: Position [x, y, z] in 3D space
        radius: Radius of the sphere
        name: Optional name for the object
    """
    result = bops.add_sphere(
        location=tuple(location),
        radius=radius,
        name=name
    )
    return f"Added sphere '{result['object_name']}' at {result['location']} with radius {result['radius']}"


@mcp.tool()
def add_cylinder(
    location: List[float] = [0, 0, 0],
    radius: float = 1.0,
    depth: float = 2.0,
    name: Optional[str] = None
) -> str:
    """
    Add a cylinder to the 3D scene
    
    Args:
        location: Position [x, y, z] in 3D space
        radius: Radius of the cylinder
        depth: Height of the cylinder
        name: Optional name for the object
    """
    result = bops.add_cylinder(
        location=tuple(location),
        radius=radius,
        depth=depth,
        name=name
    )
    return f"Added cylinder '{result['object_name']}' at {result['location']} with radius {result['radius']} and depth {result['depth']}"


@mcp.tool()
def set_object_color(
    object_name: str,
    color: List[float] = [1.0, 0.0, 0.0, 1.0]
) -> str:
    """
    Set the color of an object in the scene
    
    Args:
        object_name: Name of the object to color
        color: RGBA color [r, g, b, a] with values 0-1
    """
    result = bops.set_object_color(
        object_name=object_name,
        color=tuple(color)
    )
    
    if result['status'] == 'error':
        raise Exception(result['message'])
    
    return f"Set color of '{result['object_name']}' to {result['color']}"


@mcp.tool()
def render_scene(
    resolution_x: int = 1920,
    resolution_y: int = 1080,
    samples: int = 64
) -> Image:
    """
    Render the current 3D scene to an image
    
    Args:
        resolution_x: Width in pixels
        resolution_y: Height in pixels
        samples: Render quality (higher = better, slower)
    """
    output_path = "/tmp/render.png"
    result = bops.render_scene(
        output_path=output_path,
        resolution_x=resolution_x,
        resolution_y=resolution_y,
        samples=samples
    )
    
    # Read the rendered image
    if os.path.exists(output_path):
        with open(output_path, 'rb') as f:
            image_data = f.read()
        
        logger.info(f"Rendered scene at {resolution_x}x{resolution_y} with {samples} samples")
        return Image(data=image_data, format="png")
    else:
        raise Exception("Render failed: output file not created")


@mcp.tool()
def list_objects() -> str:
    """List all objects currently in the scene"""
    result = bops.list_objects()
    
    if result['count'] == 0:
        return "No objects in scene"
    
    objects_info = []
    for obj in result['objects']:
        objects_info.append(f"- {obj['name']} ({obj['type']}) at {obj['location']}")
    
    return f"Scene contains {result['count']} objects:\n" + "\n".join(objects_info)


@mcp.tool()
def clear_scene() -> str:
    """Remove all objects from the scene"""
    result = bops.clear_scene()
    return result['message']


def main():
    """Run the MCP server"""
    logger.info("Starting Blender MCP Server with FastMCP...")
    logger.info(f"Available tools: initialize_scene, add_cube, add_sphere, add_cylinder, set_object_color, render_scene, list_objects, clear_scene")
    mcp.run()


if __name__ == '__main__':
    main()
