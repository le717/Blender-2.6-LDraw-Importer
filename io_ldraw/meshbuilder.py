import bpy
import bmesh

from mathutils import Vector
from mathutils import Matrix

class MeshBuilder:
    def __init__(self, name, scale):
        self.name = name
        self.vertices = []
        self.faces = []
        self.edges = []
        self.color = 16
        self.colors = []
        self.scale = scale

        self.submeshes = []
        self.matrix = Matrix.Identity(4)
        self.is_part = False

    def addEdge(self, v):
        self.edges.append(v)

    def addFace(self, v):
        f = []
        for i in range(len(v)):
            self.vertices.append(v[i])
            f.append(len(self.vertices)-1)

        self.faces.append(f)

    def addQuad(self, v):
        v1 = Vector((v[0][0], v[0][1], v[0][2]))
        v2 = Vector((v[1][0], v[1][1], v[1][2]))
        v3 = Vector((v[2][0], v[2][1], v[2][2]))
        v4 = Vector((v[3][0], v[3][1], v[3][2]))

        nA = (v2 - v1).cross(v3 - v1)
        nB = (v3 - v2).cross(v4 - v2)

        if nA.dot(nB) < 0:
            self.addFace([v1, v2, v4, v3])
        else:
           self.addFace([v1, v2, v3, v4])

    def build(self, material_slots):
        mesh = bpy.data.meshes.new(name = self.name)

        bm = bmesh.new()

        for v in self.vertices:
            bm.verts.new(tuple(v))

        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        # for e in self.edges:
        #     bm.edges.new((bm.verts.new(((e[0][0], e[0][1], e[0][2]))), bm.verts.new((e[1][0], e[1][1], e[1][2]))))

        for i, f in enumerate(self.faces):
            verts = []
            for n in f:
                verts.append(bm.verts[n])
            bmf = bm.faces.new(tuple(verts))
            if (self.colors[i] <= 512):
                bmf.material_index = material_slots.index(self.colors[i])

        for sm in self.submeshes:
            m = sm.build(material_slots)
            m.transform(sm.matrix)

            sbm = bmesh.new()
            sbm.from_mesh(m)
            for n, f in enumerate(sbm.faces):
                new_verts = []
                for v in f.verts:
                    new_verts.append(bm.verts.new(v.co.to_tuple()))
                nf = bm.faces.new(new_verts)
                nf.material_index = f.material_index

            # for e in sbm.edges:
            #     new_verts = []
            #     for v in e.verts:
            #         new_verts.append(bm.verts.new(v.co.to_tuple()))
            #     bm.edges.new(new_verts)

            bpy.data.meshes.remove(m)

        bm.to_mesh(mesh)

        return mesh

    def finish(self, obj):
        obj.select = True
        bpy.context.scene.objects.active = obj
        if bpy.ops.object.mode_set.poll():
            # Change to edit mode
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')

            # Remove doubles, calculate normals
            bpy.ops.mesh.remove_doubles(threshold=0.01)
            bpy.ops.mesh.normals_make_consistent()
            if bpy.ops.object.mode_set.poll():
                # Go back to object mode
                bpy.ops.object.mode_set(mode='OBJECT')
                # Set smooth shading
                bpy.ops.object.shade_smooth()

        edges = obj.modifiers.new("Edge Split", type='EDGE_SPLIT')
        edges.split_angle = 0.523599

        obj.matrix_basis = Matrix.Scale(self.scale, 4) * obj.matrix_basis

