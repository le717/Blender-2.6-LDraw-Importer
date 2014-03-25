import os
import bpy

import math
import mathutils

from collections import namedtuple

from io_ldraw.meshbuilder import MeshBuilder

class LDrawParser:
    def __init__(self, modelpath):
        self.color = 16
        self.basepath = "c:\\ldraw"
        self.scale = 1.0
        self.subfolders = ["Unofficial/parts", "Unofficial/p", "parts", "p"]
        self.modelpath = modelpath
        self.material_slots = []

    def parse(self, filename, matrix = mathutils.Matrix.Identity(4), parent_matrix = mathutils.Matrix.Identity(4)):

        model = self.__parse(filename)

        s = os.path.splitext(os.path.basename(filename))[0]
        mb = MeshBuilder(s, self.scale)
        mb.matrix = matrix

        for l in model:
            if l.cmd.typ == "PartTypeComment":
                mb.is_part = l.cmd.parttype == "Part" or l.cmd.parttype == "Unofficial_Part"
            elif l.cmd.typ == "Comment":
                pass
            elif l.cmd.typ == "SubPart":
                p = LDrawParser(self.modelpath)
                p.basepath = self.basepath
                p.scale = self.scale
                p.material_slots = self.material_slots

                if l.cmd.color == 16:
                    p.color = self.color
                else:
                    p.color = l.cmd.color
                    if not p.color in self.material_slots:
                        self.material_slots.append(p.color)

                mat = [[l.cmd.matrix[0], l.cmd.matrix[1], l.cmd.matrix[2], l.cmd.pos[0]],
                          [l.cmd.matrix[3], l.cmd.matrix[4], l.cmd.matrix[5], l.cmd.pos[1]],
                          [l.cmd.matrix[6], l.cmd.matrix[7], l.cmd.matrix[8], l.cmd.pos[2]],
                          [0, 0, 0, 1]]

                smb = p.parse(l.cmd.filename, mathutils.Matrix(mat), parent_matrix * mb.matrix)

                if smb.is_part:
                    mesh = smb.build(self.material_slots)

                    if (len(mesh.vertices) > 0):
                        import io_ldraw.materials

                        for col in self.material_slots:
                            material = io_ldraw.materials.getMaterial(str(col))
                            mesh.materials.append(material)

                        obj = bpy.data.objects.new(smb.name, mesh)
                        bpy.context.scene.objects.link(obj)
                        # obj.select = True
                        # bpy.context.scene.objects.active = obj
                        # bpy.ops.object.mode_set(mode='OBJECT')
                        # bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
                        obj.matrix_basis = mathutils.Matrix.Rotation(math.radians(-90), 4, 'X') * parent_matrix * mb.matrix * smb.matrix
                        smb.finish(obj)
                else:
                    mb.submeshes.append(smb)
            elif l.cmd.typ == "Line":
                mb.addEdge(l.cmd)
            elif l.cmd.typ == "Triangle":
                if not l.cmd.color in self.material_slots:
                    self.material_slots.append(l.cmd.color)
                mb.addFace([l.cmd.v1, l.cmd.v2, l.cmd.v3])
                mb.colors.append(l.cmd.color if l.cmd.color != 16 else self.color)
            elif l.cmd.typ == "Quad":
                if not l.cmd.color in self.material_slots:
                    self.material_slots.append(l.cmd.color)
                mb.addQuad([l.cmd.v1, l.cmd.v2, l.cmd.v3, l.cmd.v4])
                mb.colors.append(l.cmd.color if l.cmd.color != 16 else self.color)

        return mb

    def __parse(self, filename):
        import csv

        ret = []

        Part = namedtuple("Part", ["cmd"])
        Comment = namedtuple("Comment", ["code", "typ", "text"])
        PartTypeComment = namedtuple("PartTypeComment", ["code", "typ", "parttype"])
        SubPart = namedtuple("SubPart", ["code", "typ", "color", "pos", "matrix", "filename"])
        Triangle = namedtuple("Triangle", ["code", "typ", "color", "v1", "v2", "v3"])
        Quad = namedtuple("Triangle", ["code", "typ", "color", "v1", "v2", "v3", "v4"])

        f = ""
        try:
            f = self.locate_file(filename)
        except:
            print("File not found: ", filename)
            return ret

        with open(f, "r") as file:
            reader = csv.reader(file, delimiter=' ', skipinitialspace=True)
            cmd = None

            for line in reader:
                if (len(line) == 0):
                    continue
                if line[0] == '0':
                    if (len(line) > 1) and line[1] == '!LDRAW_ORG':
                        cmd = PartTypeComment("0", "PartTypeComment", line[2])
                    else:
                        cmd = Comment("0", "Comment", " ".join(line[1:]))
                elif line[0] == '1':
                    cmd = SubPart("1", "SubPart", int(line[1], 0), [float(x) for x in line[2:5]], [float(x) for x in line[5:14]], " ".join(line[14:]))
                elif line[0] == '2':
                    pass
                elif line[0] == '3':
                    cmd = Triangle("3", "Triangle", int(line[1], 0), [float(x) for x in line[2:5]], [float(x) for x in line[5:8]], [float(x) for x in line[8:11]])
                elif line[0] == '4':
                    cmd = Quad("4", "Quad", int(line[1], 0), [float(x) for x in line[2:5]], [float(x) for x in line[5:8]], [float(x) for x in line[8:11]], [float(x) for x in line[11:14]])

                part = Part(cmd)
                ret.append(part)

        return ret

    def locate_file(self, filename):
        if (os.path.isfile(filename)):
            return filename

        f = os.path.join(self.modelpath, filename)
        if (os.path.isfile(f)):
            return f

        for folder in self.subfolders:
            f = os.path.join(self.basepath, folder, filename)
            if os.path.isfile(f):
                return f

        raise FileNotFoundError(filename)