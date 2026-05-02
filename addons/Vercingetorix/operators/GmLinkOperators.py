import bpy
from ..config import __addon_name__
from ..preference.AddonPreferences import GridmapAddonPreferences

class GmLinkOperator(bpy.types.Operator):
    bl_idname = "object.gridmap_link_op"
    bl_label = "Grid Map Linker"
    bl_options = {'REGISTER', 'UNDO'}

    prefs = None

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        # setup
        self.prefs = context.preferences.addons[__addon_name__].preferences
        return self.execute(context)

    def execute(self, context):
        # Get active collection
        coll = context.collection
        if not coll or not coll.name.startswith("GM_"):
            self.report({'ERROR'}, "Active collection must start with 'GM_'")
            return {'CANCELLED'}

        name = coll.name[3:]
        brush_name = f"GM_{name}_brushs"
        link_name = f"GM_{name}_link"
        place_name = f"GM_{name}_placeholders"

        # Validate sub-collections exist
        if any(n not in bpy.data.collections for n in (brush_name, link_name, place_name)):
            self.report({'ERROR'}, "Collection must contain brushs, link, and placeholders sub-collections")
            return {'CANCELLED'}

        brush_coll = bpy.data.collections[brush_name]
        link_coll = bpy.data.collections[link_name]
        place_coll = bpy.data.collections[place_name]

        new_p = None
        # Process each brush collection
        for bsub in list(brush_coll.children):
            # 1. Create placeholder collection P_<brush>
            p_name = f"P_{bsub.name}"
            if p_name not in bpy.data.collections:
                new_p = bpy.data.collections.new(p_name)
                place_coll.children.link(new_p)               
            else:
                new_p = bpy.data.collections[p_name]

            if p_name not in bpy.data.objects:
                mesh = bpy.data.meshes.new(p_name)
                obj = bpy.data.objects.new(p_name, mesh)
                new_p.objects.link(obj)
            else :
                self.report({'INFO'}, f"Object '{p_name}' already exists in Placeholders")
            # 2. Create link object L_<brush> in link collection
            obj = None
            obj_name = f"L_{bsub.name}"
            if obj_name in bpy.data.objects:
                self.report({'WARNING'}, f"Object '{obj_name}' already exists")
                obj = bpy.data.objects[obj_name]
            else:
                mesh = bpy.data.meshes.new(f"{obj_name}_mesh")
                obj = bpy.data.objects.new(obj_name, mesh)  # Empty object
                link_coll.objects.link(obj)

            # 3. Add Geometry Nodes modifier
            mod = obj.modifiers.get("GeometryNodes")
            if not mod:
                mod = obj.modifiers.new(name="GeometryNodes", type='NODES')
            # Assign node group
            node_group = bpy.data.node_groups["GM_Linker"]
            if not node_group:
                self.report({'ERROR'}, "Node group 'GM_Linker' not found")
                continue
            mod.node_group = node_group

            # 4. Set modifier inputs
            # Brush socket
            try:
                mod["Socket_2"] = bsub
            except Exception:
                self.report({'WARNING'}, f"Failed to set 'Brush' input for {obj_name}")
            # Placeholder socket
            try:
                mod["Socket_3"] = new_p
            except Exception:
                self.report({'WARNING'}, f"Failed to set 'Placeholder' input for {obj_name}")

        self.report({'INFO'}, "Processed brush collections into placeholders and link objects")
        return {'FINISHED'}