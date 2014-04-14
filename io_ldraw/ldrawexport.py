import bpy
import os

class LDrawExporter:
    def __init__(self, modelpath, scale):
        self.path = modelpath
        self.scale = scale

    def export(self):
        if bpy.context.active_object is None or bpy.context.active_object.type != 'MESH' or bpy.context.active_object not in bpy.context.selected_objects:
            print("No model selected.")

        self.file = open(self.path, "w")

        import bmesh
        bm = bmesh.new()
        bm.from_mesh(bpy.context.active_object.data)

        for f in bm.faces:
            if len(f.verts) == 3:
                self.write_triangle(f)
            elif len(f.verts) == 4:
                self.write_quad(f)
            else:
                print("Too many vertices.")

        bm.free()

        self.file.close()

    def write_triangle(self, face):
        self.file.write("3 16")
        self.write_verts(face)
        self.file.write("\n")

    def write_quad(self, face):
        self.file.write("4 16")
        self.write_verts(face)
        self.file.write("\n")

    def write_verts(self, face):
        for vert in face.verts:
            v = vert.co
            self.file.write(" {0} {1} {2}".format(round(v.x * self.scale, 5), round(v.y * self.scale, 5), round(v.z * self.scale, 5)))

