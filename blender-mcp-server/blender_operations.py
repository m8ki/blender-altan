"""
Blender operations wrapper for MCP server.
Provides high-level functions that wrap Blender's bpy API.
"""
import bpy
import os
from typing import Dict, Any, Optional, Tuple


def initialize_scene():
    """Initialize a clean Blender scene."""
    # Clear existing objects
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Add camera
    bpy.ops.object.camera_add(location=(7, -7, 5))
    camera = bpy.context.view_layer.objects.active
    camera.rotation_euler = (1.1, 0, 0.785)
    bpy.context.scene.camera = camera
    
    # Add light
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    light = bpy.context.view_layer.objects.active
    light.data.energy = 2.0
    
    return {"status": "success", "message": "Scene initialized"}


def add_cube(location: Tuple[float, float, float] = (0, 0, 0), 
             size: float = 2.0,
             name: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a cube to the scene.
    
    Args:
        location: (x, y, z) position
        size: Size of the cube
        name: Optional name for the object
    
    Returns:
        Dict with status and object info
    """
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    obj = bpy.context.view_layer.objects.active
    
    if name:
        obj.name = name
    
    return {
        "status": "success",
        "object_name": obj.name,
        "location": list(location),
        "size": size
    }


def add_sphere(location: Tuple[float, float, float] = (0, 0, 0),
               radius: float = 1.0,
               name: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a UV sphere to the scene.
    
    Args:
        location: (x, y, z) position
        radius: Radius of the sphere
        name: Optional name for the object
    
    Returns:
        Dict with status and object info
    """
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location)
    obj = bpy.context.view_layer.objects.active
    
    if name:
        obj.name = name
    
    return {
        "status": "success",
        "object_name": obj.name,
        "location": list(location),
        "radius": radius
    }


def add_cylinder(location: Tuple[float, float, float] = (0, 0, 0),
                 radius: float = 1.0,
                 depth: float = 2.0,
                 name: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a cylinder to the scene.
    
    Args:
        location: (x, y, z) position
        radius: Radius of the cylinder
        depth: Height of the cylinder
        name: Optional name for the object
    
    Returns:
        Dict with status and object info
    """
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=location)
    obj = bpy.context.view_layer.objects.active
    
    if name:
        obj.name = name
    
    return {
        "status": "success",
        "object_name": obj.name,
        "location": list(location),
        "radius": radius,
        "depth": depth
    }


def set_object_color(object_name: str, 
                     color: Tuple[float, float, float, float] = (1.0, 0.0, 0.0, 1.0)) -> Dict[str, Any]:
    """
    Set the color of an object.
    
    Args:
        object_name: Name of the object
        color: RGBA color tuple (values 0-1)
    
    Returns:
        Dict with status
    """
    obj = bpy.data.objects.get(object_name)
    if not obj:
        return {"status": "error", "message": f"Object '{object_name}' not found"}
    
    # Create or get material
    mat_name = f"{object_name}_material"
    mat = bpy.data.materials.get(mat_name)
    
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        obj.data.materials.append(mat)
    
    # Set color
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = color
    
    return {
        "status": "success",
        "object_name": object_name,
        "color": list(color)
    }


def render_scene(output_path: str = "/tmp/render.png",
                 resolution_x: int = 1920,
                 resolution_y: int = 1080,
                 samples: int = 64) -> Dict[str, Any]:
    """
    Render the current scene.
    
    Args:
        output_path: Path to save the rendered image
        resolution_x: Width in pixels
        resolution_y: Height in pixels
        samples: Number of render samples (higher = better quality, slower)
    
    Returns:
        Dict with status and output path
    """
    scene = bpy.context.scene
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y
    scene.render.filepath = output_path
    
    # Use Cycles for better quality
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    
    # Render
    bpy.ops.render.render(write_still=True)
    
    return {
        "status": "success",
        "output_path": output_path,
        "resolution": [resolution_x, resolution_y],
        "samples": samples
    }


def list_objects() -> Dict[str, Any]:
    """
    List all objects in the scene.
    
    Returns:
        Dict with list of objects
    """
    objects = []
    for obj in bpy.data.objects:
        objects.append({
            "name": obj.name,
            "type": obj.type,
            "location": list(obj.location)
        })
    
    return {
        "status": "success",
        "objects": objects,
        "count": len(objects)
    }


def delete_object(object_name: str) -> Dict[str, Any]:
    """
    Delete an object from the scene.
    
    Args:
        object_name: Name of the object to delete
    
    Returns:
        Dict with status
    """
    obj = bpy.data.objects.get(object_name)
    if not obj:
        return {"status": "error", "message": f"Object '{object_name}' not found"}
    
    bpy.data.objects.remove(obj, do_unlink=True)
    
    return {
        "status": "success",
        "message": f"Object '{object_name}' deleted"
    }


def clear_scene() -> Dict[str, Any]:
    """
    Clear all objects from the scene.
    
    Returns:
        Dict with status
    """
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    return {
        "status": "success",
        "message": "Scene cleared"
    }
