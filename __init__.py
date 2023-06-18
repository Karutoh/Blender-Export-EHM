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

def Triangulate(mesh):
    #mesh.update_from_editmode()
    #mesh.data.calc_normals_split()
    
    edit = bmesh.new()
    edit.from_mesh(mesh.data)
    bmesh.ops.triangulate(edit, faces = edit.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
    edit.to_mesh(mesh.data)
    edit.free()

def WriteMeshes_1(bytes, meshes, exportIndices):
    #newTrans = axis_conversion(from_forward='-Y', from_up='Z', to_forward='Z', to_up='Y').to_4x4()
    
    #Mesh Count
    bytes.extend(struct.pack("<Q", len(meshes)))
    
    for mesh in meshes:
        Triangulate(mesh)
        
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
            for face in mesh.data.polygons:
                for i in face.vertices:
                    indices.append(i)
                    
            for vert in mesh.data.vertices:
                coordinates.append(vert.co)
                normals.append(vert.normal)
                
            for uv in mesh.data.uv_layers.active.data:
                uvs.append(uv.uv)
        else:
            for face in mesh.data.polygons:
                for i in face.vertices:
                    coordinates.append(mesh.data.vertices[i].co)
                    normals.append(mesh.data.vertices[i].normal)
                    uvs.append(mesh.data.uv_layers[0].data[i].uv)
                
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
            bytes.extend(struct.pack("<f", 1.0 - uvs[i].y))
            
        #Index Count
        bytes.extend(struct.pack("<Q", len(indices)))
        
        for i in indices:
            bytes.extend(struct.pack("<I", i))
            
def WriteMeshes_2(bytes, meshes, exportIndices):
    #Mesh Count
    bytes.extend(struct.pack("<Q", len(meshes)))
    
    for mesh in meshes:
        vertBuff = []
        normalBuff = []
        uvBuff   = []
        faceBuff = []
        
        #Mesh Name Count
        bytes.extend(struct.pack("<Q", len(mesh.name)))
        
        #Mesh Name
        bytes.extend(str.encode(mesh.name))
        
        #CloneMesh(mesh)
        for i, loop in enumerate(mesh.data.loops):
            thisVertex = mesh.data.vertices[loop.vertex_index].co
            thisNormal = mesh.data.vertices[loop.vertex_index].normal
            thisUV = mesh.data.uv_layers.active.data[i].uv
            
            #check if already in the list
            found = 0
            for i in range(len(vertBuff)):
                if(abs(vertBuff[i].x - thisVertex.x) <= max(1e-09 * max(abs(vertBuff[i].x), abs(thisVertex.x)), 0.0)):
                    if(abs(vertBuff[i].y - thisVertex.y) <= max(1e-09 * max(abs(vertBuff[i].y), abs(thisVertex.y)), 0.0)):
                        if(abs(vertBuff[i].z - thisVertex.z) <= max(1e-09 * max(abs(vertBuff[i].z), abs(thisVertex.z)), 0.0)):
                            if(abs(uvBuff[i].x - thisUV.x) <= max(1e-09 * max(abs(uvBuff[i].x), abs(thisUV.x)), 0.0)):
                                if(abs(uvBuff[i].y - thisUV.y) <= max(1e-09 * max(abs(uvBuff[i].y), abs(thisUV.y)), 0.0)):
                                    faceBuff.append(int(i))
                                    found = 1
                                    break
                i += 1
            
            #otherwise stash a new vertex
            if found == 0:
                faceBuff.append(len(vertBuff)) #index
                normalBuff.append(thisNormal)      #float, float, float
                vertBuff.append(thisVertex)    #float, float, float
                uvBuff.append(thisUV)          #float, float
        
        #Vertex Count            
        bytes.extend(struct.pack("<Q", len(vertBuff)))
        
        for i in range(len(vertBuff)):
            #Coordinate
            bytes.extend(struct.pack("<f", vertBuff[i].x))
            bytes.extend(struct.pack("<f", vertBuff[i].y))
            bytes.extend(struct.pack("<f", vertBuff[i].z))
            
            #Normal
            bytes.extend(struct.pack("<f", normalBuff[i].x))
            bytes.extend(struct.pack("<f", normalBuff[i].y))
            bytes.extend(struct.pack("<f", normalBuff[i].z))
            
            #UV
            bytes.extend(struct.pack("<f", uvBuff[i].x))
            bytes.extend(struct.pack("<f", 1.0 - uvBuff[i].y))
            
            
        #Index Count
        bytes.extend(struct.pack("<Q", len(faceBuff)))
        
        for i in faceBuff:
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
    
    WriteMeshes_2(bytes, meshes, exportIndices)
            
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
