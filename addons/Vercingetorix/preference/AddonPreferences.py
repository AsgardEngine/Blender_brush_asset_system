import os

import bpy
from bpy.props import StringProperty, IntProperty, BoolProperty, PointerProperty
from bpy.types import AddonPreferences

from ..config import __addon_name__

class GridmapAddonPreferences(AddonPreferences):
    # this must match the add-on name (the folder name of the unzipped file)
    bl_idname = __addon_name__
    
    # https://docs.blender.org/api/current/bpy.props.html
    # The name can't be dynamically translated during blender programming running as they are defined
    # when the class is registered, i.e. we need to restart blender for the property name to be correctly translated.
    filepath: StringProperty(
        name="Resource Folder",
        default=os.path.join(os.path.expanduser("~"), "Documents", __addon_name__),
        subtype='DIR_PATH',
    ) # type: ignore
    collection_name: StringProperty(
        name="Collection",
        description="Name of the collection to use",
        default="",
    ) # type: ignore
    snapping: IntProperty(
        name="Snapping distance",
        default=1,
    ) # type: ignore
    rotation_step: IntProperty(
        name="Rotation step",
        default=90,
    ) # type: ignore
    boolean: BoolProperty(
        name="Boolean Config",
        default=False,
    ) # type: ignore

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.label(text="Add-on Preferences View")
        layout.prop(self, "filepath")
        layout.prop_search(self, "collection_name")
        layout.prop(self, "snapping")
        layout.prop(self, "rotation_step")
        layout.prop(self, "boolean")
