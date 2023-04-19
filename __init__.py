bl_info = {
    "name": "Export Event Horizon Model (.ehm)",
    "author": "Arron Nelson (AKA Karutoh)",
    "version": (1, 0, 0),
    "blender": (3, 1, 0),
    "location": "File > Export > EHM",
    "description": "The script exports Blender geometry to a Event Horizon Model file format.",
    "category": "Import-Export"
}

import sys
import struct
import mathutils
import bmesh

import bpy
from bpy_extras.io_utils import ExportHelper, axis_conversion
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator, Mesh

def WriteMeshes(bytes, meshes, exportIndices):
    newTrans = axis_conversion(from_forward='-Y', from_up='Z', to_forward='Z', to_up='Y').to_4x4()
    
    #Mesh Count
    bytes.extend(struct.pack("<Q", len(meshes)))
    
    for mesh in meshes:
        mesh.update_from_editmode()
        mesh.data.calc_normals_split()
        
        edit = bmesh.new()
        edit.from_mesh(mesh.data)
        bmesh.ops.triangulate(edit, faces = edit.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
        
        result = bpy.data.meshes.new("tmp")
        
        edit.to_mesh(result)
        edit.free()
        
        result.update()
        #result.transform(newTrans)
        
        #Mesh Name Count
        bytes.extend(struct.pack("<Q", len(mesh.name)))
        
        #Mesh Name
        bytes.extend(str.encode(mesh.name))
        
        indices = []
        coordinates = []
        normals = []
        uvs = []
        
        if exportIndices:
            for face in result.polygons:
                for i in face.vertices:
                    indices.append(i)
                    
            for vert in result.vertices:
                coordinates.append(vert.co)
                normals.append(vert.normal)
                
            for uv in result.uv_layers[0].data:
                uvs.append(uv.uv)
        else:
            for face in result.polygons:
                for i in face.vertices:
                    coordinates.append(result.vertices[i].co)
                    normals.append(result.vertices[i].normal)
                    uvs.append(result.uv_layers[0].data[i].uv)
                
        #Vertex Count
        bytes.extend(struct.pack("<Q", len(coordinates)))
                
        for i in range(len(coordinates)):
            #Coordinate
            bytes.extend(struct.pack("<f", coordinates[i].x))
            bytes.extend(struct.pack("<f", coordinates[i].y))
            bytes.extend(struct.pack("<f", coordinates[i].z))
            
            #Normal
            bytes.extend(struct.pack("<f", normals[i].x))
            bytes.extend(struct.pack("<f", normals[i].y))
            bytes.extend(struct.pack("<f", normals[i].z))
            
            #UV
            bytes.extend(struct.pack("<f", uvs[i].x))
            bytes.extend(struct.pack("<f", uvs[i].y))
            
        #Index Count
        bytes.extend(struct.pack("<Q", len(indices)))
        
        for i in indices:
            bytes.extend(struct.pack("<I", i))

def Write(context, filepath, selectionOnly, exportIndices):
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
    
    WriteMeshes(bytes, meshes, exportIndices)
            
    f.write(bytes)
            
    f.close()
    
    return {'FINISHED'}

class ExportEHM(Operator, ExportHelper):
    """Export to the Event Horizon Model format (.ehm)"""
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
    
    exportIndices: BoolProperty(
        name="Export Indices",
        description="Export mesh indices",
        default=False,
    )

    def execute(self, context):
        return Write(context, self.filepath, self.selectionOnly, self.exportIndices)

def menu_func(self, context):
    self.layout.operator(ExportEHM.bl_idname, text="Event Horizon Model")

def register():
    bpy.utils.register_class(ExportEHM)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)

def unregister():
    bpy.utils.unregister_class(ExportEHM)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()
    bpy.ops.export.ehm('INVOKE_DEFAULT')
