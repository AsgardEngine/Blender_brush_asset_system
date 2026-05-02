import bpy, bmesh, math, mathutils
from enum import IntFlag, auto
from mathutils import Vector
from bpy_extras import view3d_utils
from ..config import __addon_name__
from ..preference.AddonPreferences import GridmapAddonPreferences


class Mode(IntFlag):
    NONE = 0
    DEFAULT = auto()
    DRAW = auto()
    ERASE = auto()
    SELECT = auto()
    ROTATE = auto()
    FLOOR = auto()


class GridMapOperator(bpy.types.Operator):
    bl_idname = "object.gridmap_op"
    bl_label = "Grid Map"
    bl_options = {'REGISTER', 'UNDO'}

    mode: Mode = Mode.DEFAULT
    placeholder_name = "Placeholder"
    collection_placeholders = None
    collection_draw = None
    obj_draw = None
    bm_draw = None
    collection_index = 0
    occupied = set()
    z = 0

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        # setup
        self.prefs = context.preferences.addons[__addon_name__].preferences
        
        # Get active collection
        coll = context.collection
        if not coll or not coll.name.startswith("GM_"):
            self.report({'ERROR'}, "Active collection must start with 'GM_'")
            return {'CANCELLED'}

        name = coll.name[3:]
        brush_name = f"GM_{name}_brushs"
        link_name = f"GM_{name}_link"
        place_name = f"GM_{name}_placeholders"
        self.placeholder_name = f"GM_{name}_Placeholder"
        # Validate sub-collections exist
        if any(n not in bpy.data.collections for n in (brush_name, link_name, place_name)):
            self.report({'ERROR'}, "Collection must contain brushs, link, and placeholders sub-collections")
            return {'CANCELLED'}

        self.collection_placeholders = bpy.data.collections[place_name]
        layer = bpy.context.view_layer.layer_collection.children[f"GM_{name}"].children
        layer[f"GM_{name}_brushs"].hide_viewport = True
        layer[f"GM_{name}_link"].hide_viewport = False
        layer[f"GM_{name}_placeholders"].hide_viewport = True

        self.placeholder = bpy.data.objects[f"GM_{name}_placeholders"]

        self._configure_placeholder()
        self._load_collections()
        self._bind_keys(context)
        
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        etype, evalue = event.type, event.value
        if etype == 'ESC':
            self._link(self.collection_placeholders)
            return {'CANCELLED'}

        # toggle select/rotate
        if etype in {'B','R', 'F'} and evalue=='PRESS':
            self.mode = Mode.SELECT if etype=='B' else Mode.ROTATE
            self.mode = Mode.FLOOR if etype=='F' else self.mode
            return {'RUNNING_MODAL'}

        # draw/erase start/stop
        if etype in {'LEFTMOUSE','RIGHTMOUSE'} and evalue in {'PRESS','RELEASE'}:
            m = Mode.DRAW if etype=='LEFTMOUSE' else Mode.ERASE
            self.mode = self.mode | m if evalue=='PRESS' else self.mode & ~m
            self.painting = (evalue=='PRESS')
            return self._paint() if self.painting else {'RUNNING_MODAL'}

        # wheel: select/rotate
        if etype.startswith('WHEEL'):
            if Mode.SELECT in self.mode:
                self._cycle_collection(etype)
            elif Mode.ROTATE in self.mode:
                self._rotate_placeholder(etype)
            elif Mode.FLOOR in self.mode:
                self._floor_elevation(context, event, etype)
            return {'RUNNING_MODAL'}

        # mouse move: update
        if etype=='MOUSEMOVE':
            self._update_placeholder(context, event)
            if getattr(self, 'painting', False):
                return self._paint()
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    # helpers

    def _configure_placeholder(self):
        p = self.placeholder
        p.show_in_front = True; p.display_type='WIRE'; p.hide_select=True

    def _load_collections(self):
        children = self.collection_placeholders.children
        self.collection_draw = children[0] if children else None        

        self._cache(); self._link(self.collection_draw); self._base_mesh()
        
    def _bind_keys(self, context):
        km = context.window_manager.keyconfigs.user.keymaps['3D View']
        self._rotate_kmis = [k for k in km.keymap_items if k.idname=='view3d.rotate']

    def _cache(self):
        self.occupied = {self._key(o.location) for o in self.collection_draw.objects if o.name!=self.placeholder_name}
    
    def _cache(self):
        # ensure mesh is up-to-date
        self._base_mesh()

        mesh = self.obj_draw.data
        verts = mesh.vertices

        occupied = set()
        for poly in mesh.polygons:
            # compute local-space centroid of this face
            centroid = mathutils.Vector((0.0, 0.0, 0.0))
            for vid in poly.vertices:
                centroid += verts[vid].co
            centroid /= len(poly.vertices)

            # turn it into your integer key
            occupied.add(self._key(centroid))

        self.occupied = occupied

    def _link(self, col):
        for c in self.placeholder.users_collection[:]: c.objects.unlink(self.placeholder)
        col.objects.link(self.placeholder)
        
    def _base_mesh(self):
        if self.bm_draw:
            self.bm_draw.free()
        self.obj_draw = bpy.data.objects[self.collection_draw.name]
        self.bm_draw = bmesh.new()
        self.bm_draw.from_mesh(self.obj_draw.data)

    def _cycle_collection(self, wheel):
        self.collection_index = (self.collection_index + (-1 if wheel=='WHEELUPMOUSE' else 1)) % len(self.collection_placeholders.children)
        self.collection_draw = self.collection_placeholders.children[self.collection_index]
        self._cache(); self._link(self.collection_draw); self._base_mesh()

    def _update_placeholder(self, ctx, evt):
        r, v = ctx.region, ctx.space_data.region_3d
        co = view3d_utils.region_2d_to_vector_3d(r,v,(evt.mouse_region_x,evt.mouse_region_y))
        org = view3d_utils.region_2d_to_origin_3d(r,v,(evt.mouse_region_x,evt.mouse_region_y))
        pt = mathutils.geometry.intersect_line_plane(org,org+co*10000,Vector((0,0,self.z)),Vector((0,0,1)))
        if pt:
            s = self.prefs.snapping; self.placeholder.location = Vector((round(pt.x/s)*s,round(pt.y/s)*s,self.z))

    def _paint(self):
        loc = self.placeholder.location; key = self._key(loc)
        if Mode.DRAW in self.mode and key not in self.occupied: self._add(loc)
        if Mode.ERASE in self.mode and key in self.occupied: self._remove(loc)
        return {'RUNNING_MODAL'}

    def _add(self, loc):
        self._base_mesh()
        s = self.prefs.snapping
        x, y, z = loc
        corners = [
        Vector((x - s/2, y - s/2, z)),
        Vector((x + s/2, y - s/2, z)),
        Vector((x + s/2, y + s/2, z)),
        Vector((x - s/2, y + s/2, z)),
        ]
        verts = [self.bm_draw.verts.new(c) for c in corners]
        bm_face = None
        try:
            bm_face = self.bm_draw.faces.new(verts)
        except ValueError:
            #self.report({'ERROR'}, f"Errrrrr")
            pass
        
        self.bm_draw.to_mesh(self.obj_draw.data)
        if bm_face.is_valid:
            data = self.obj_draw.data
            if "face_rotation" not in data.attributes:
                data.attributes.new(
                    name="face_rotation",   # your attribute name
                    type='FLOAT',           # store a single float
                    domain='FACE'           # per‐face (polygon) data
                )
            
            angle_z = self.placeholder.rotation_euler.z
            rot_attr = data.attributes["face_rotation"]
            rot_attr.data[bm_face.index].value = angle_z
        else:
            self.report({'ERROR'}, "BM Face index not valid!")

        self.occupied.add(self._key(loc))

    def _remove(self, loc):
        self._base_mesh()
        for f in self.bm_draw.faces:
            cx = sum(v.co.x for v in f.verts)/len(f.verts)
            cy = sum(v.co.y for v in f.verts)/len(f.verts)
            k = (round(cx/self.prefs.snapping), round(cy/self.prefs.snapping), f.verts[0].co.z)
            if k == self._key(loc):
                bmesh.ops.delete(self.bm_draw, geom=[f], context='FACES')
                self.occupied.discard(self._key(loc))
                self.bm_draw.to_mesh(self.obj_draw.data)
                break
        '''for o in list(self.collection_draw.objects):
            if o.location==loc and o.name!=self.placeholder_name:
                bpy.data.objects.remove(o,do_unlink=True); self.occupied.discard(self._key(loc)); break'''

    def _rotate_placeholder(self, wheel):
        step = math.radians(self.prefs.rotation_step)
        d = -step if wheel=='WHEELDOWNMOUSE' else step
        r = self.placeholder.rotation_euler; r.z=(r.z+d)%(2*math.pi)

    def _floor_elevation(self, context, event, wheel):
        self.z += -1 if wheel=='WHEELDOWNMOUSE' else 1
        self._update_placeholder(context, event)

    def _key(self, v):
        s = self.prefs.snapping
        return (round(v.x/s), round(v.y/s), v.z)
