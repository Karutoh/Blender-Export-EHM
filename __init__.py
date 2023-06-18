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
    
def FindBIndexByGIndex(mesh, gi, skeletons):
    for s in skeletons:
        for bi, b in enumerate(s.data.bones):
            if mesh.vertex_groups.find(b.name) == gi:
                return bi
            
    return 0xFF

def WriteMat4(bytes, mat):
    for x in range(4):
        for y in range(4):
            bytes.extend(struct.pack("<f", mat[y][x]))
            
def WriteMeshes(bytes, meshes, skeletons, exportIndices):
    #Mesh Count
    bytes.extend(struct.pack("<Q", len(meshes)))
    
    for mesh in meshes:
        vertBuff = []
        uvBuff   = []
        faceBuff = []
        
        Triangulate(mesh)
        
        #Mesh Name Count
        bytes.extend(struct.pack("<Q", len(mesh.name)))
        
        #Mesh Name
        bytes.extend(str.encode(mesh.name))
        
        #CloneMesh(mesh)
        for i, loop in enumerate(mesh.data.loops):
            thisVertex = mesh.data.vertices[loop.vertex_index]
            thisUV = mesh.data.uv_layers.active.data[i].uv
            
            #check if already in the list
            found = 0
            for i in range(len(vertBuff)):
                if(abs(vertBuff[i].co.x - thisVertex.co.x) <= max(1e-09 * max(abs(vertBuff[i].co.x), abs(thisVertex.co.x)), 0.0)):
                    if(abs(vertBuff[i].co.y - thisVertex.co.y) <= max(1e-09 * max(abs(vertBuff[i].co.y), abs(thisVertex.co.y)), 0.0)):
                        if(abs(vertBuff[i].co.z - thisVertex.co.z) <= max(1e-09 * max(abs(vertBuff[i].co.z), abs(thisVertex.co.z)), 0.0)):
                            if(abs(uvBuff[i].x - thisUV.x) <= max(1e-09 * max(abs(uvBuff[i].x), abs(thisUV.x)), 0.0)):
                                if(abs(uvBuff[i].y - thisUV.y) <= max(1e-09 * max(abs(uvBuff[i].y), abs(thisUV.y)), 0.0)):
                                    faceBuff.append(int(i))
                                    found = 1
                                    break
            
            #otherwise stash a new vertex
            if found == 0:
                faceBuff.append(len(vertBuff)) #index
                vertBuff.append(thisVertex)    #vertex obj
                uvBuff.append(thisUV)          #float, float
        
        #Vertex Count            
        bytes.extend(struct.pack("<Q", len(vertBuff)))
        
        for i in range(len(vertBuff)):
            #Coordinate
            bytes.extend(struct.pack("<f", vertBuff[i].co.x))
            bytes.extend(struct.pack("<f", vertBuff[i].co.y))
            bytes.extend(struct.pack("<f", vertBuff[i].co.z))
            
            #Normal
            bytes.extend(struct.pack("<f", vertBuff[i].normal.x))
            bytes.extend(struct.pack("<f", vertBuff[i].normal.y))
            bytes.extend(struct.pack("<f", vertBuff[i].normal.z))
            
            #UV
            bytes.extend(struct.pack("<f", uvBuff[i].x))
            bytes.extend(struct.pack("<f", 1.0 - uvBuff[i].y))
            
            #Vertex Bones/Weights
            for gi in range(4):
                if gi < len(vertBuff[i].groups):
                    bytes.extend(struct.pack("<B", FindBIndexByGIndex(mesh, vertBuff[i].groups[gi].group, skeletons)))
                else:
                    bytes.extend(struct.pack("<B", 0xFF))
            
            for gi in range(4):
                if gi < len(vertBuff[i].groups):
                    bytes.extend(struct.pack("<f", vertBuff[i].groups[gi].weight))
                else:
                    bytes.extend(struct.pack("<f", 0.0))
            
            
        #Index Count
        bytes.extend(struct.pack("<Q", len(faceBuff)))
        
        for i in faceBuff:
            bytes.extend(struct.pack("<I", i))
        
        if len(skeletons) >= 1:
            #Bone Count
            bytes.extend(struct.pack("<B", len(skeletons[0].data.bones)))
            for b in skeletons[0].data.bones:
                bytes.extend(struct.pack("<Q", len(b.name)))
                bytes.extend(str.encode(b.name))
                
                if b.parent is None:
                    bytes.extend(struct.pack("<B", 0xFF))
                else:
                    bytes.extend(struct.pack("<B", skeletons[0].data.bones.find(b.parent.name)))
                    
                WriteMat4(bytes, b.matrix_local)
        else:
            bytes.extend(struct.pack("<B", 0))

def Write(context, filepath, selectionOnly, exportIndices):
    f = open(filepath, "wb")
    
    bytes = bytearray()
    
    
    #Version
    bytes.extend(struct.pack("<I", 1))
    bytes.extend(struct.pack("<I", 0))
    bytes.extend(struct.pack("<I", 0))
    
    meshes = []
    skeletons = []
    
    if selectionOnly:
        for obj in context.selected_objects:
            if obj.type == "MESH":
                meshes.append(obj)
            elif obj.type == "ARMATURE":
                skeletons.append(obj)
    else:
        for obj in context.scene.objects:
            if obj.type == "MESH":
                meshes.append(obj)
            elif obj.type == "ARMATURE":
                skeletons.append(obj)
    
    WriteMeshes(bytes, meshes, skeletons, exportIndices)
            
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
