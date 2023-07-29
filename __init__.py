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

class KeyFrame:
    def __init__(self, num, timeStamp):
        self.num = num
        self.timeStamp = timeStamp
        self.pos = mathutils.Vector((0.0, 0.0, 0.0))
        self.rot = mathutils.Quaternion()
        self.scale = mathutils.Vector((0.0, 0.0, 0.0))

class BoneAnimation:
    def __init__(self, id):
        self.id = id
        self.keyFrames = []
        
    def GetKeyFrame(self, num):
        for frame in self.keyFrames:
            if frame.num == num:
                return frame
            
        return None
    
    def AddKeyFrame(self, keyFrame):
        if self.GetKeyFrame(keyFrame.num) != None:
            return None
        
        self.keyFrames.append(keyFrame)
        
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
            
            
            flipMatrix = axis_conversion(from_forward='Y', from_up='Z', to_forward='Z', to_up='Y').to_4x4()
            
            if b.parent is None:
                bytes.extend(struct.pack("<B", 0xFF))
                WriteMat4(bytes, flipMatrix @ b.matrix_local);
            else:
                bytes.extend(struct.pack("<B", skeletons[0].data.bones.find(b.parent.name)))
                WriteMat4(bytes, flipMatrix @ (b.parent.matrix_local.inverted() @ b.matrix_local));
            
            WriteMat4(bytes, (flipMatrix @ b.matrix_local).inverted());
    else:
        #Bone Count
        bytes.extend(struct.pack("<B", 0))
        
def ExportAnimations(bytes, skeletons, animations):
    if len(skeletons) >= 1:
        fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
        
        #Animation Count
        bytes.extend(struct.pack("<Q", len(animations)))
        
        for a in animations:
            bpy.context.view_layer.objects.active = skeletons[0]
            bpy.context.object.animation_data_create()
            bpy.context.object.animation_data.action = a
            
            #Animation Name
            bytes.extend(struct.pack("<Q", len(a.name)))
            bytes.extend(str.encode(a.name))
            
            duration = 0.0
            boneAnims = []
            
            for i, b in enumerate(skeletons[0].data.bones):
                for f in a.fcurves:
                    if f.data_path == f'pose.bones["{b.name}"].location':
                        result = None
                        
                        for ba in boneAnims:
                            if ba.id == i:
                                result = ba
                        
                        if result == None:
                            boneAnims.append(BoneAnimation(i))
                            result = boneAnims[len(boneAnims) - 1]
                            
                        for k in f.keyframe_points:
                            keyFrame = result.GetKeyFrame(k.co.x)
                            if keyFrame == None:
                                keyFrame = result.AddKeyFrame(KeyFrame(k.co.x, k.co.x / fps))
                                if keyFrame.timeStamp > duration:
                                    duration = keyFrame.timeStamp
                                    
                            if f.array_index == 0:
                                keyFrame.pos.x = k.co.y
                            elif f.array_index == 1:
                                keyFrame.pos.z = k.co.y
                            elif f.array_index == 2:
                                keyFrame.pos.y = k.co.y
                            
                    elif f.data_path == f'pose.bones["{b.name}"].scale':
                        result = None
                        
                        for ba in boneAnims:
                            if ba.id == i:
                                result = ba
                        
                        if result == None:
                            boneAnims.append(BoneAnimation(i))
                            result = boneAnims[len(boneAnims) - 1]
                            
                        for k in f.keyframe_points:
                            keyFrame = result.GetKeyFrame(k.co.x)
                            if keyFrame == None:
                                keyFrame = result.AddKeyFrame(KeyFrame(k.co.x, k.co.x / fps))
                                if keyFrame.timeStamp > duration:
                                    duration = keyFrame.timeStamp
                                    
                            if f.array_index == 0:
                                keyFrame.scale.x = k.co.y
                            elif f.array_index == 1:
                                keyFrame.scale.z = k.co.y
                            elif f.array_index == 2:
                                keyFrame.scale.y = k.co.y
                            
                    elif f.data_path == f'pose.bones["{b.name}"].rotation_quaternion':
                        result = None
                        
                        for ba in boneAnims:
                            if ba.id == i:
                                result = ba
                        
                        if result == None:
                            boneAnims.append(BoneAnimation(i))
                            result = boneAnims[len(boneAnims) - 1]
                        
                        for k in f.keyframe_points:
                            keyFrame = result.GetKeyFrame(k.co.x)
                            if keyFrame == None:
                                keyFrame = result.AddKeyFrame(KeyFrame(k.co.x, k.co.x / fps))
                                if keyFrame.timeStamp > duration:
                                    duration = keyFrame.timeStamp
                                
                            if f.array_index == 0:
                                keyFrame.rot.w = k.co.y
                            elif f.array_index == 1:
                                keyFrame.rot.x = -k.co.y
                            elif f.array_index == 2:
                                keyFrame.rot.y = k.co.y
                            elif f.array_index == 3:
                                keyFrame.rot.z = -k.co.y
                            
            #Duration
            bytes.extend(struct.pack("<f", duration))
                            
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
                    
                    #Key Frame Time Stamp
                    bytes.extend(struct.pack("<f", kf.timeStamp))
                    
                    #Position
                    bytes.extend(struct.pack("<f", kf.pos.x))
                    bytes.extend(struct.pack("<f", kf.pos.y))
                    bytes.extend(struct.pack("<f", kf.pos.z))
                    
                    #Rotation
                    bytes.extend(struct.pack("<f", kf.rot.w))
                    bytes.extend(struct.pack("<f", kf.rot.x))
                    bytes.extend(struct.pack("<f", kf.rot.y))
                    bytes.extend(struct.pack("<f", kf.rot.z))
                    
                    #Scale
                    bytes.extend(struct.pack("<f", kf.scale.x))
                    bytes.extend(struct.pack("<f", kf.scale.y))
                    bytes.extend(struct.pack("<f", kf.scale.z))
    else:
        bytes.extend(struct.pack("<Q", 0))

def WriteMat4(bytes, mat):
    for x in range(4):
        for y in range(4):
            bytes.extend(struct.pack("<f", mat[y][x]))
            
def WriteMeshes(bytes, meshes, skeletons, animations):
    origTrans = axis_conversion(from_forward='Z', from_up='Y', to_forward='Y', to_up='Z').to_4x4()
    newTrans = axis_conversion(from_forward='Y', from_up='Z', to_forward='Z', to_up='Y').to_4x4()
    
    #Mesh Count
    bytes.extend(struct.pack("<Q", len(meshes)))
    
    for mesh in meshes:
        mesh.data.transform(newTrans)
        
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
        
        mesh.data.transform(origTrans)

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
