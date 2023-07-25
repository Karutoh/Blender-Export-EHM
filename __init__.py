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

"""
PropertyChange.type == 0 //X-Axis Position
PropertyChange.type == 1 //Y-Axis Position
PropertyChange.type == 2 //Z-Axis Position
PropertyChange.type == 3 //X-Axis Scale
PropertyChange.type == 4 //Y-Axis Scale
PropertyChange.type == 5 //Z-Axis Scale
PropertyChange.type == 6 //X-Axis Rotation (Quat)
PropertyChange.type == 7 //Y-Axis Rotation (Quat)
PropertyChange.type == 8 //Z-Axis Rotation (Quat)
PropertyChange.type == 9 //W-Axis Rotation (Quat)
"""
class PropertyChange:
    type = 0
    value = 0.0
    
    def __init__(self, type, value):
        self.type = type
        self.value = value

class KeyFrame:
    num = 0
    changes = []
    
    def __init__(self, num):
        self.num = num
        self.changes = []

class BoneAnimation:
    id = 0xFF
    keyFrames = []
    
    def __init__(self, id):
        self.id = id
        self.keyFrames = []
        
    def GetKeyFrame(self, num):
        for frame in self.keyFrames:
            if frame.num == num:
                return frame
            
        self.keyFrames.append(KeyFrame(num))
            
        return self.keyFrames[len(self.keyFrames) - 1]

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

def ExportSkeletons(bytes, skeletons):
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
            
            editBoneI = skeletons[0].data.edit_bones.find(b.name)
            if editBoneI == -1:
                WriteMat4(bytes, mathutils.Matrix.Identity(4))
            else:
                WriteMat4(bytes, skeletons[0].data.edit_bones[editBoneI].matrix)
    else:
        #Bone Count
        bytes.extend(struct.pack("<B", 0))
        
def ExportAnimations(bytes, skeletons, animations):
    if len(skeletons) >= 1:
        #Animation Count
        bytes.extend(struct.pack("<Q", len(animations)))
        
        for a in animations:
            bpy.context.view_layer.objects.active = skeletons[0]
            bpy.context.object.animation_data_create()
            bpy.context.object.animation_data.action = a
            
            #Animation Name
            bytes.extend(struct.pack("<Q", len(a.name)))
            bytes.extend(str.encode(a.name))
            
            boneAnims = []
            
            for i, b in enumerate(skeletons[0].data.bones):
                print(f"Bone Index: {i}")
                print(f"FCurve Count: {len(a.fcurves)}")
                
                for f in a.fcurves:
                    if f.data_path == f'pose.bones["{b.name}"].location':
                        result = None
                        
                        for ba in boneAnims:
                            if ba.id == i:
                                result = ba
                        
                        if result == None:
                            boneAnims.append(BoneAnimation(i))
                            result = boneAnims[len(boneAnims) - 1]
                            
                            
                        print(f"Loc Key Frame Count: {len(f.keyframe_points)}")
                        for k in f.keyframe_points:
                            keyFrame = result.GetKeyFrame(k.co.x)
                            keyFrame.changes.append(PropertyChange(f.array_index, k.co.y))
                            
                    elif f.data_path == f'pose.bones["{b.name}"].scale':
                        result = None
                        
                        for ba in boneAnims:
                            if ba.id == i:
                                result = ba
                        
                        if result == None:
                            boneAnims.append(BoneAnimation(i))
                            result = boneAnims[len(boneAnims) - 1]
                            
                        print(f"Scale Key Frame Count: {len(f.keyframe_points)}")
                        for k in f.keyframe_points:
                            type = 0
                            if f.array_index == 0:
                                type = 3
                            elif f.array_index == 1:
                                type = 4
                            elif f.array_index == 2:
                                type = 5
                            
                            keyFrame = result.GetKeyFrame(k.co.x)
                            keyFrame.changes.append(PropertyChange(type, k.co.y))
                    elif f.data_path == f'pose.bones["{b.name}"].rotation_quaternion':
                        result = None
                        
                        for ba in boneAnims:
                            if ba.id == i:
                                result = ba
                        
                        if result == None:
                            boneAnims.append(BoneAnimation(i))
                            result = boneAnims[len(boneAnims) - 1]
                        
                        print(f"Rot Key Frame Count: {len(f.keyframe_points)}")
                        for k in f.keyframe_points:
                            type = 0
                            if f.array_index == 0:
                                type = 6
                            elif f.array_index == 1:
                                type = 7
                            elif f.array_index == 2:
                                type = 8
                            elif f.array_index == 3:
                                type = 9
                            
                            keyFrame = result.GetKeyFrame(k.co.x)
                            keyFrame.changes.append(PropertyChange(type, k.co.y))
                            
            #Change Count
            bytes.extend(struct.pack("<B", len(boneAnims)))
            
            for ba in boneAnims:
                #Bone Id
                bytes.extend(struct.pack("<B", ba.id))
                
                #Key Frame Count
                bytes.extend(struct.pack("<Q", len(ba.keyFrames)))
                
                for kf in ba.keyFrames:
                    #Key Frame Number
                    bytes.extend(struct.pack("<f", kf.num))
                    
                    print(f"PC Count: {len(kf.changes)}")
                    #Property Change Count
                    bytes.extend(struct.pack("<Q", len(kf.changes)))
                    
                    for pc in kf.changes:
                        #Change Type
                        bytes.extend(struct.pack("<B", pc.type))
                    
                        #Value
                        bytes.extend(struct.pack("<f", pc.value))
    else:
        bytes.extend(struct.pack("<Q", 0))

def WriteMat4(bytes, mat):
    for x in range(4):
        for y in range(4):
            bytes.extend(struct.pack("<f", mat[y][x]))
            
def WriteMeshes(bytes, meshes, skeletons, animations):
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
            
        ExportSkeletons(bytes, skeletons)
        ExportAnimations(bytes, skeletons, animations)

def Write(context, filepath):
    f = open(filepath, "wb")
    
    bytes = bytearray()
    
    
    #Version
    bytes.extend(struct.pack("<I", 1))
    bytes.extend(struct.pack("<I", 0))
    bytes.extend(struct.pack("<I", 0))
    
    meshes = []
    skeletons = []
    animations = bpy.data.actions
    
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            meshes.append(obj)
        elif obj.type == "ARMATURE":
            skeletons.append(obj)
    
    WriteMeshes(bytes, meshes, skeletons, animations)
            
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

    def execute(self, context):
        return Write(context, self.filepath)

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
