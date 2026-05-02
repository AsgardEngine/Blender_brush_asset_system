import bpy
from ..config import __addon_name__
from ..preference.AddonPreferences import GridmapAddonPreferences

class GmCollectionOperator(bpy.types.Operator):
    bl_idname = "object.gridmap_collection_op"
    bl_label = "Grid Map Collection"
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
        name = self.prefs.collection_name
        if not name:
            self.report({'ERROR'}, "Name cannot be empty")
            return {'CANCELLED'}

        # Root collection
        root_name = f"GM_{name}"
        root_coll = None
        if root_name in bpy.data.collections:
            self.report({'WARNING'}, f"Collection '{root_name}' already exists")
            root_coll = bpy.data.collections[root_name]
        else:
            root_coll = bpy.data.collections.new(root_name)
            context.scene.collection.children.link(root_coll)

        # Sub-collections
        suffixes = ['brushs', 'link', 'placeholders']
        for suffix in suffixes:
            col_name = f"GM_{name}_{suffix}"
            if col_name not in bpy.data.collections:
                sub_coll = bpy.data.collections.new(col_name)
                root_coll.children.link(sub_coll)

        if not f"GM_{name}_{suffixes[2]}" in bpy.data.objects:
            mesh = bpy.data.meshes.new(f"GM_{name}_{suffixes[2]}")
            verts = [(-0.5, -0.5, 0), (0.5, -0.5, 0), (0.5, 0.5, 0), (-0.5, 0.5, 0)]
            faces = [(0, 1, 2, 3)]
            mesh.from_pydata(verts, [], faces)
            obj = bpy.data.objects.new(f"GM_{name}_{suffixes[2]}", mesh)
            root_coll.objects.link(obj)
        else:
            self.report({'INFO'}, f"Already Exist GM_{name}_{suffixes[2]}")
        self.report({'INFO'}, f"Created hierarchy under '{root_name}'")
        return {'FINISHED'}