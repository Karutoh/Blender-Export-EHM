"""bl_info = {
    "name": "Export Event Horizon Mesh (.ehm)",
    "author": "Arron Nelson (AKA Karutoh)",
    "version": (1, 0, 0),
    "blender": (3, 1, 0),
    "location": "File > Export > EHM",
    "description": "The script exports Blender geometry to a Event Horizon Mesh file format.",
    "category": "Import-Export"
}"""

import sys
import struct

import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator, Mesh

def WriteMeshes(bytes, meshes):
    #Mesh Count
    bytes.append(len(meshes))
    
    for mesh in meshes:
        #Mesh Name Count
        bytes.append(len(mesh.name))
        
        #Mesh Name
        bytes.extend(str.encode(mesh.name))
        
        #Has Indices
        bytes.append(True)
        
        #Vertex Count
        bytes.append(len(mesh.data.vertices))
        
        #Vertices
        for vert in mesh.data.vertices:
            #Position
            bytes.extend(struct.pack("f", vert.co.x))
            bytes.extend(struct.pack("f", vert.co.y))
            bytes.extend(struct.pack("f", vert.co.z))
            
            #Normal
            bytes.extend(struct.pack("f", vert.normal.x))
            bytes.extend(struct.pack("f", vert.normal.y))
            bytes.extend(struct.pack("f", vert.normal.z))
            
            #UV
            bytes.extend(struct.pack("f", 0.0))
            bytes.extend(struct.pack("f", 0.0))
            bytes.extend(struct.pack("f", 0.0))
            
            #Color
            bytes.extend(struct.pack("f", 0.0))
            bytes.extend(struct.pack("f", 0.0))
            bytes.extend(struct.pack("f", 0.0))
            bytes.extend(struct.pack("f", 0.0))
            
        indices = []
            
        for face in mesh.data.polygons:
            indices.append(face.vertices[0])
            indices.append(face.vertices[1])
            indices.append(face.vertices[2])
            
        #Index Count
        bytes.append(len(indices))
        
        #Indices
        for i in indices:
            bytes.append(i)
    

def Write(context, filepath, selectionOnly):
    f = open(filepath, "wb")
    
    bytes = bytearray()
    
    #Version
    bytes.append(1)
    bytes.append(0)
    bytes.append(0)
    
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
    #bpy.types.TOPBAR_MT_file_export.append(menu_func)

def unregister():
    bpy.utils.unregister_class(ExportEHM)
    #bpy.types.TOPBAR_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()
    bpy.ops.export.ehm('INVOKE_DEFAULT')