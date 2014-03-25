# -*- coding: utf-8 -*-

import os
import sys
import bpy
from bpy_extras.io_utils import ImportHelper
from io_ldraw.ldrawparser import LDrawParser

bl_info = {
    "name": "LDraw Importer",
    "description": "Import LDraw models.",
    "author": "Banbury",
    "version": (1, 0, 0),
    "blender": (2, 67, 0),
    "api": 31236,
    "location": "File > Import",
    "warning": "Bricksmith and MPD models are not supported.",
    "wiki_url": "",
    #"tracker_url": "maybe"
                #"soon",
    "category": "Import-Export"}

class LDRImporterOps(bpy.types.Operator, ImportHelper):
    """LDR Importer Operator"""
    bl_idname = "import_scene.ldraw"
    bl_description = "Import an LDraw model (.ldr/.dat)"
    bl_label = "Import LDraw Model"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    # File type filter in file browser
    filename_ext = ".ldr"

    filter_glob = bpy.props.StringProperty(
        default="*.ldr;*.dat",
        options={'HIDDEN'}
    )

    ldraw_path = bpy.props.StringProperty(name="LDraw path", default="c:\\ldraw" if sys.platform.startswith("win") else os.path.join(os.path.expanduser("~"), "ldraw"))
    scale = bpy.props.FloatProperty(name="Scale", default=1, min=0, subtype="PERCENTAGE")

    def execute(self, context):
        # Uncomment for profiling
        # import cProfile, pstats, io
        # pr = cProfile.Profile()
        # pr.enable()

        import os
        parser = LDrawParser(os.path.dirname(self.filepath))
        parser.basepath = self.ldraw_path
        parser.scale = self.scale / 100
        parser.parse(self.filepath)

        # Uncomment for profiling
        # pr.disable()
        # s = io.StringIO()
        # sortby = 'cumulative'
        # ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        # ps.print_stats()
        # print(s.getvalue())

        return {'FINISHED'}

def menu_import(self, context):
    """Import menu listing label"""
    self.layout.operator(LDRImporterOps.bl_idname, text="LDraw (.ldr/.dat)")

    import io_ldraw.materials
    io_ldraw.materials.is_cycles = context.scene.render.engine == 'CYCLES'

def register():
    """Register Menu Listing"""
    import io_ldraw.materials
    io_ldraw.materials.scanLDConfig("c:\\ldraw")

    bpy.utils.register_module(__package__)
    bpy.types.INFO_MT_file_import.append(menu_import)


def unregister():
    """Unregister Menu Listing"""
    bpy.utils.unregister_module(__package__)
    bpy.types.INFO_MT_file_import.remove(menu_import)


if __name__ == "__main__":
    register()
