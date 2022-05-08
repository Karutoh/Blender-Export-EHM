bl_info = {
    "name": "Export Event Horizon Mesh (.ehm)",
    "author": "Arron Nelson (AKA Karutoh)",
    "version": (1, 0, 0),
    "blender": (3, 1, 0),
    "location": "File > Export > EHM",
    "description": "The script exports Blender geometry to a Event Horizon Mesh file format.",
    "category": "Import-Export"
}

import sys
import struct

import bmesh

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator, Mesh

def WriteMeshes(bytes, meshes):
    #Mesh Count
    bytes.extend(struct.pack("<I", len(meshes)))
    
    for mesh in meshes:
        #Mesh Name Count
        bytes.extend(struct.pack("<I", len(mesh.name)))
        
        #Mesh Name
        bytes.extend(str.encode(mesh.name))
        
        vertexCount = 0
        
        for polygon in mesh.data.polygons:
            vertexCount += len(polygon.vertices)
        
        #Vertex Count
        bytes.extend(struct.pack("<I", vertexCount))
        
        mesh.data.calc_normals_split()
        
        for polygon in mesh.data.polygons:
            for vertIdx, loopIdx in zip(polygon.vertices, polygon.loop_indices):
                loop = mesh.data.loops[loopIdx]
                
                #Position
                bytes.extend(struct.pack("<f", mesh.data.vertices[vertIdx].co.y))
                bytes.extend(struct.pack("<f", mesh.data.vertices[vertIdx].co.z))
                bytes.extend(struct.pack("<f", mesh.data.vertices[vertIdx].co.x))
                
                #Normal
                bytes.extend(struct.pack("<f", loop.normal.y))
                bytes.extend(struct.pack("<f", loop.normal.z))
                bytes.extend(struct.pack("<f", loop.normal.x))
                
                #UV
                if len(mesh.data.uv_layers.active.data):
                    bytes.extend(struct.pack("<f", mesh.data.uv_layers.active.data[loopIdx].uv.x))
                    bytes.extend(struct.pack("<f", mesh.data.uv_layers.active.data[loopIdx].uv.y))
                else:
                    bytes.extend(struct.pack("<f", 0.0))
                    bytes.extend(struct.pack("<f", 0.0))

def Write(context, filepath, selectionOnly):
    f = open(filepath, "wb")
    
    bytes = bytearray()
    
    #Version
    bytes.extend(struct.pack("<I", 1))
    bytes.extend(struct.pack("<I", 0))
    bytes.extend(struct.pack("<I", 0))
    
    meshes = []
    
    if selectionOnly:
        for obj in context.selected_objects:
            if obj.type == "MESH":
                meshes.append(obj)
    else:
        for obj in context.scene.objects:
            if obj.type == "MESH":
                meshes.append(obj)
    
    WriteMeshes(bytes, meshes)
            
    f.write(bytes)
            
    f.close()
    
    return {'FINISHED'}

class ExportEHM(Operator, ExportHelper):
    """Export to the Event Horizon Mesh format (.ehm)"""
    bl_idname = "export.ehm"
    bl_label = "Export EHM"
    filename_ext = ".ehm"

    filter_glob: StringProperty(
        default="*.ehm",
        options={'HIDDEN'},
        maxlen=255
    )

    selectionOnly: BoolProperty(
        name="Selection Only",
        description="Export selected objects only",
        default=False,
    )

    def execute(self, context):
        return Write(context, self.filepath, self.selectionOnly)

def menu_func(self, context):
    self.layout.operator(ExportEHM.bl_idname, text="EHM")

def register():
    bpy.utils.register_class(ExportEHM)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)

def unregister():
    bpy.utils.unregister_class(ExportEHM)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()
    bpy.ops.export.ehm('INVOKE_DEFAULT')