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

def WriteMeshesTriangulated(bytes, meshes):
    origRot = axis_conversion(from_forward='Z', from_up='Y', to_forward='-Y', to_up='Z').to_4x4()
    newRot = axis_conversion(from_forward='-Y', from_up='Z', to_forward='Z', to_up='Y').to_4x4()
    
    #Mesh Count
    bytes.extend(struct.pack("<I", len(meshes)))
    
    for mesh in meshes:
        mesh.update_from_editmode()
        mesh.data.calc_normals_split()
        mesh.data.transform(newRot)
        
        result = bmesh.new()
        result.from_mesh(mesh.data)
        bmesh.ops.triangulate(result, faces = result.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
        
        mesh.data.transform(origRot)
        
        #Mesh Name Count
        bytes.extend(struct.pack("<I", len(mesh.name)))
        
        #Mesh Name
        bytes.extend(str.encode(mesh.name))
        
        vertexCount = 0
        
        for face in result.faces:
            vertexCount += len(face.verts)
        
        #Vertex Count
        bytes.extend(struct.pack("<I", vertexCount))
        
        for face in result.faces:
            for vert, loop in zip(face.verts, face.loops):
                #Position
                bytes.extend(struct.pack("<f", vert.co.x))
                bytes.extend(struct.pack("<f", vert.co.y))
                bytes.extend(struct.pack("<f", vert.co.z))
                
                #Normal
                bytes.extend(struct.pack("<f", vert.normal.x))
                bytes.extend(struct.pack("<f", vert.normal.y))
                bytes.extend(struct.pack("<f", vert.normal.z))
                
                #UV
                if result.loops.layers.uv.active is None:
                    bytes.extend(struct.pack("<f", 0.0))
                    bytes.extend(struct.pack("<f", 0.0))
                else:
                    bytes.extend(struct.pack("<f", loop[result.loops.layers.uv.active].uv.x))
                    bytes.extend(struct.pack("<f", loop[result.loops.layers.uv.active].uv.y))
                    
        #Index Count
        bytes.extend(struct.pack("<I", 0))

def WriteMeshes(bytes, meshes):
    origRot = axis_conversion(from_forward='Z', from_up='Y', to_forward='-Y', to_up='Z').to_4x4()
    newRot = axis_conversion(from_forward='-Y', from_up='Z', to_forward='Z', to_up='Y').to_4x4()
    
    #Mesh Count
    bytes.extend(struct.pack("<I", len(meshes)))
    
    for mesh in meshes:
        mesh.update_from_editmode()
        mesh.data.calc_normals_split()
        mesh.data.transform(newRot)
        
        result = bmesh.new()
        result.from_mesh(mesh.data)
        bmesh.ops.triangulate(result, faces = result.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
        
        mesh.data.transform(origRot)
        
        #Mesh Name Count
        bytes.extend(struct.pack("<I", len(mesh.name)))
        
        #Mesh Name
        bytes.extend(str.encode(mesh.name))
        
        indices = []
        coordinates = []
        normals = []
        uvs = []
        
        for face in mesh.data.polygons:
            indices.append(face.vertices[0])
            indices.append(face.vertices[1])
            indices.append(face.vertices[2])
            for i in range(len(face.vertices)):
                normals.append(mesh.data.vertices[face.vertices[i]].normal)
                
        for vert in mesh.data.vertices:
            coordinates.append(vert.co)

        for uv_layer in mesh.data.uv_layers:
            for x in range(len(uv_layer.data)):
                uvs.append(uv_layer.data[x].uv)
                
        #Vertex Count
        bytes.extend(struct.pack("<I", len(coordinates)))
                
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
        bytes.extend(struct.pack("<I", len(indices)))
        
        for i in indices:
            bytes.extend(struct.pack("<I", i))

def Write(context, filepath, selectionOnly, triangulated):
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
    
    if triangulated:
        WriteMeshesTriangulated(bytes, meshes)
    else:
        WriteMeshes(bytes, meshes)
            
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
    
    triangulated: BoolProperty(
        name="Triangulated",
        description="Export selected objects only",
        default=False,
    )

    def execute(self, context):
        return Write(context, self.filepath, self.selectionOnly, self.triangulated)

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