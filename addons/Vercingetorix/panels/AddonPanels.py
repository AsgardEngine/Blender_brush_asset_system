import bpy

from addons.Vercingetorix.operators.GmCollectionOperators import GmCollectionOperator
from addons.Vercingetorix.operators.GmLinkOperators import GmLinkOperator

from ..config import __addon_name__
from ..operators.AddonOperators import GridMapOperator
from ....common.i18n.i18n import i18n
from ....common.types.framework import reg_order


class BasePanel(object):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VX_Gridmap"

    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True


@reg_order(0)
class GridmapAddonPanel(BasePanel, bpy.types.Panel):
    bl_label = "Gridmap panel"
    bl_idname = "SCENE_PT_sample"

    def draw(self, context: bpy.types.Context):
        addon_prefs = context.preferences.addons[__addon_name__].preferences

        layout = self.layout

        layout.prop(addon_prefs, "filepath")
        layout.separator()
        
        layout.operator(GridMapOperator.bl_idname)
        
        layout.prop(addon_prefs, "collection_name")
        layout.operator(GmCollectionOperator.bl_idname, text="Setup Collection")
        
        layout.operator(GmLinkOperator.bl_idname, text="Link")

        layout.prop(addon_prefs, "snapping")
        layout.prop(addon_prefs, "rotation_step")



    @classmethod
    def poll(cls, context: bpy.types.Context):
        return True

