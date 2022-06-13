import bpy
import math
import mathutils
import time
import numpy as np
from mathutils import Matrix
from random import randint
from math import radians
import os
import json
from bpy_extras.io_utils import ImportHelper

bl_info = {
    "name": "Import 3DScannerApp Camera",
    "category": "Import-Export",
    "version": (1, 0, 0),
    "blender": (2, 80, 0),
    'description': 'import Camera and its animation from a 3DScannerApp™ Full Data Folder.',
    'tracker_url': "https://github.com/userId/project/issues/",
    'isDraft': False,
    'developer': "stmaccarelli", 
    'url': 'https://stefano-maccarelli.com', 
}

# ------------------------------------------------------------------------
#    OPERATOR
# ------------------------------------------------------------------------

class TDSA_OT_import_cam(bpy.types.Operator):
    """Import Camera and Animation from 3DscannerApp Full Data Folder"""
    bl_idname = "import_camera.3dscannerapp_camera"
    bl_label = "Import Camera"
    bl_options = {'REGISTER'}
    
   # Define this to tell 'fileselect_add' that we want a directoy
    directory : bpy.props.StringProperty(
        name="Path",
        description="3DscannerApp Full Data Folder"
        )

    rotation : bpy.props.FloatProperty(
        name="Rotation",
        description="rotation",
        default=90
        )

    def load_frames( self, json_base_path ):

        print( json_base_path )
        json_files = list(sorted(filter(lambda s : 'frame_' in s and '.json' in s, os.listdir(json_base_path))))
        json_files = list(map(lambda s: os.path.join(json_base_path, s) , json_files))
        
        frames = []
    
        for json_file in json_files:
            info = json.load(open(json_file))
            pose = np.array( info["cameraPoseARFrame"] ).reshape((4,4))
            timestamp = info.get("time", -1)
            frame = dict(pose=pose.copy(), time=timestamp)
            frames.append(frame)
            
            
        if not frames:
            self.report({"ERROR"}, "No camera info found in the selected folder")
            return -1
        
        first_time = frames[0]["time"]
        
        if first_time >= 0:
            for f in frames:
                f["time"] -= first_time     
        
        return frames 


    def look_at(self, obj_camera, point):
        loc_camera = obj_camera.matrix_world.to_translation()
        direction = point - loc_camera
        # point the cameras '-Z' and use its 'Y' as up
        rot_quat = direction.to_track_quat('-Z', 'Y')
        # assume we're using euler rotation
        obj_camera.rotation_euler = rot_quat.to_euler()


    def eraseAllKeyframes(self, scene, passedOB = None):

        if passedOB != None:

            ad = passedOB.animation_data

            if ad != None:
                print ('ad=',ad)
                passedOB.animation_data_clear()

                #scene.update()
                

    def insert_keyframes(self, obj, frames, scene_fps=30.0, frame_offset=0):
        
        # insert animation keyframes for the given 'obj' for each frame pose
        
        self.eraseAllKeyframes(bpy.context.scene, obj)
        
        for i in range(len(frames)):
            
            frame = frames[i]
            
            pose = frame['pose']
                
            y_rows = pose[1, :].copy()
            z_rows = pose[2, :].copy()
            
            pose[1, :] = z_rows * -1.0
            pose[2, :] = y_rows 
                    
            frame_idx = round(frame["time"] * float(scene_fps))
            frame_idx += frame_offset
            
            bpy.context.scene.frame_set(frame_idx)
            
            obj.matrix_world = Matrix(pose)
            
            #rotate cam 90 degrees
            obj.rotation_euler.rotate_axis("Z", radians( self.rotation ) )
            
            obj.keyframe_insert('rotation_euler', index=-1)
            obj.keyframe_insert('location', index=-1)
    
        return frame_idx

    def draw ( self, context ):
        layout = self.layout
        col = layout.box().column()
        col.label(text="TrueDepth scans should use")
        col.label(text="'optimized_poses' folder:")  

        col = layout.box().column()
        col.label(text='Rotation:', icon='EMPTY_DATA')
        col.prop(self, 'rotation')
      
    def execute(self, context):
        
        # Set scan path to a LiDAR scan:
        # scan_path = "/Users/cc/Downloads/2022_01_09_12_54_15"

        # TrueDepth scans should use 'optimized_poses' folder
        #scan_path = "/Users/cc/Downloads/2022_01_09_12_54_15/optimized_poses"

        scene = bpy.context.scene #bpy.data.scenes["Scene"]
        scan_path = self.directory

        frames = self.load_frames(scan_path)
        
        if frames == -1:
            self.report({"ERROR"}, "No frames found")
            return {'CANCELLED'}
        
        else:
            # create the first camera
            cam = bpy.data.cameras.new("3DSA.Camera")
            cam.lens = 18

            # create the first camera object
            cam_obj = bpy.data.objects.new("3DSA.Camera", cam)
            cam_obj.location = (0,0,0)
            cam_obj.rotation_euler = (0,0,0)
            scene.collection.objects.link(cam_obj)

            scene.frame_start = 0

            # blender camera looks down -Z , +Y is up , +X right 

            last_frame_idx = self.insert_keyframes(cam_obj, frames, frame_offset=0)

            bpy.context.scene.frame_set(0)

            scene.frame_end = last_frame_idx
            
            self.report({"INFO"}, "Imported 3DScannerApp™ Camera with "+ str(len(frames)) +" frames")
            return {'FINISHED'}

    def invoke(self, context, event):
        # Open browser, take reference to 'self' read the path to selected
        # file, put path in predetermined self fields.
        # See: https://docs.blender.org/api/current/bpy.types.WindowManager.html#bpy.types.WindowManager.fileselect_add
        context.window_manager.fileselect_add(self)
        # Tells Blender to hang on for the slow user input
        return {'RUNNING_MODAL'}

# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------

# class TDSA_CAM_Panel(bpy.types.Panel):
#     bl_idname = "TDSA_CAM_Panel"
#     bl_label = "Import Camera"
#     bl_space_type = "VIEW_3D"   
#     bl_region_type = "UI"
#     bl_category = "3DScannerApp"
#     bl_context = "objectmode"

#     def draw(self, context):
#         layout = self.layout
#         scn = context.scene
#         col = layout.column(align=True)
#         col.prop(scn.scan_cam, "path", text="")

#         row = layout.row()
#         row.prop( scn.scan_cam, 'rotation', text="rotation")

#         row = layout.row()
#         row.operator(TDSA_OT_import_cam.bl_idname)


# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

# Add to a menu
def menu_func_import(self, context):
    self.layout.operator(TDSA_OT_import_cam.bl_idname, text="3DScannerApp Camera")


def register():
    if bpy.app.version >= (2, 80, 0):
        bpy.utils.register_class(TDSA_OT_import_cam)
        bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    else:
        bpy.utils.register_module(__name__)
        bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister():
    if bpy.app.version >= (2, 80, 0):
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
        bpy.utils.unregister_class(TDSA_OT_import_cam)
    else:
        bpy.utils.unregister_module(__name__)
        bpy.types.INFO_MT_file_import.remove(menu_func_import)


if __name__ == '__main__':
    register()
