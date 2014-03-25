import bpy
import os

colors = {}
mat_list = {}
is_cycles = False

def scanLDConfig(path):
    """Scan LDConfig to get the material color info."""
    # LDConfig.ldr does not exist for some reason
    if not os.path.exists(os.path.join(path, "LDConfig.ldr")):
        raise FileNotFoundError("Could not find LDConfig.ldr at", path)

    with open(os.path.join(path, "LDConfig.ldr"), "rt") as ldconfig:
        ldconfig_lines = ldconfig.readlines()

    for line in ldconfig_lines:
        if len(line) > 3:
            if line[2:4].lower() == '!c':
                line_split = line.split()

                name = line_split[2]
                code = line_split[4]

                color = {
                    "name": name,
                    "color": hex_to_rgb(line_split[6][1:]),
                    "alpha": 1.0,
                    "luminance": 0.0,
                    "material": "BASIC"
                }

                #if len(line_split) > 10 and line_split[9] == 'ALPHA':
                if hasColorValue(line_split, "ALPHA"):
                    color["alpha"] = int(
                        getColorValue(line_split, "ALPHA")) / 256.0

                if hasColorValue(line_split, "LUMINANCE"):
                    color["luminance"] = int(
                        getColorValue(line_split, "LUMINANCE"))

                if hasColorValue(line_split, "CHROME"):
                    color["material"] = "CHROME"

                if hasColorValue(line_split, "PEARLESCENT"):
                    color["material"] = "PEARLESCENT"

                if hasColorValue(line_split, 'RUBBER'):
                    color["material"] = "RUBBER"

                if hasColorValue(line_split, "METAL"):
                    color["material"] = "METAL"

                if hasColorValue(line_split, "MATERIAL"):
                    subline = line_split[line_split.index("MATERIAL"):]

                    color["material"] = getColorValue(subline, "MATERIAL")
                    color["secondary_color"] = getColorValue(subline, "VALUE")[1:]
                    color["fraction"] = getColorValue(subline, "FRACTION")
                    color["vfraction"] = getColorValue(subline, "VFRACTION")
                    color["size"] = getColorValue(subline, "SIZE")
                    color["minsize"] = getColorValue(subline, "MINSIZE")
                    color["maxsize"] = getColorValue(subline, "MAXSIZE")

                colors[code] = color


def getMaterial(colour):
    """Get Blender Internal Material Values"""
    if colour in colors:
        if not (colour in mat_list):
            mat = bpy.data.materials.new("Mat_{0}_".format(colour))
            col = colors[colour]

            mat.diffuse_color = col["color"]

            alpha = col["alpha"]
            if alpha < 1.0:
                mat.use_transparency = True
                mat.alpha = alpha

            mat.emit = col["luminance"] / 100

            if col["material"] == "CHROME":
                mat.specular_intensity = 1.4
                mat.roughness = 0.01
                mat.raytrace_mirror.use = True
                mat.raytrace_mirror.reflect_factor = 0.3

            elif col["material"] == "PEARLESCENT":
                mat.specular_intensity = 0.1
                mat.roughness = 0.32
                mat.raytrace_mirror.use = True
                mat.raytrace_mirror.reflect_factor = 0.07

            elif col["material"] == "RUBBER":
                mat.specular_intensity = 0.19

            elif col["material"] == "METAL":
                mat.specular_intensity = 1.473
                mat.specular_hardness = 292
                mat.diffuse_fresnel = 0.93
                mat.darkness = 0.771
                mat.roughness = 0.01
                mat.raytrace_mirror.use = True
                mat.raytrace_mirror.reflect_factor = 0.9

            #elif col["material"] == "GLITTER":
            #    slot = mat.texture_slots.add()
            #    tex = bpy.data.textures.new("GlitterTex", type = "STUCCI")
            #    tex.use_color_ramp = True
            #
            #    slot.texture = tex

            else:
                mat.specular_intensity = 0.2

            if is_cycles:
                getCyclesMaterial(mat, colour)
            mat_list[colour] = mat

        return mat_list[colour]
    else:
        # Support for direct colors 0x2RRGGBB
        mat = bpy.data.materials.new("Mat_{0}_".format(colour))
        hexstr = hex(int(colour))[3:].upper()
        col = hex_to_rgb(hexstr)
        mat.diffuse_color = col
        mat.specular_intensity = 0.2
        getCyclesBase(mat, col, 1.0)
        mat_list[colour] = mat
        return mat_list[colour]

    return None


def getCyclesMaterial(material, colour):
    """Get Cycles Material Values"""
    if colour in colors:
        if not (colour in mat_list):
            col = colors[colour]

            if col["name"] == "Milky_White":
                mat = getCyclesMilkyWhite(material, col["color"])

            elif (col["material"] == "BASIC" and col["luminance"]) == 0:
                mat = getCyclesBase(material, col["color"], col["alpha"])

            elif col["luminance"] > 0:
                mat = getCyclesEmit(material, col["color"], col["alpha"], col["luminance"])

            elif col["material"] == "CHROME":
                mat = getCyclesChrome(material, col['color'])

            elif col["material"] == "PEARLESCENT":
                mat = getCyclesPearlMetal(material, col["color"], 0.2)

            elif col["material"] == "METAL":
                mat = getCyclesPearlMetal(material, col["color"], 0.5)

            elif col["material"] == "RUBBER":
                mat = getCyclesRubber(material, col["color"],  col["alpha"])

            else:
                mat = getCyclesBase(material, col["color"], col["alpha"])

            mat_list[colour] = mat

        return mat_list[colour]
    else:
        mat = bpy.data.materials.new("Mat_{0}_".format(colour))
        mat_list[colour] = getCyclesBase(mat, (1, 1, 0), 1.0)
        return mat_list[colour]

    return None


def getCyclesBase(mat, diff_color, alpha):
    """Base Material, Mix shader and output node"""
    mat.use_nodes = True

    # Set viewport color to be the same as material color
    mat.diffuse_color = diff_color

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    if alpha == 1.0:
        mix.inputs['Fac'].default_value = 0.05
        node = nodes.new('ShaderNodeBsdfDiffuse')
        node.location = -242, 154
        node.inputs['Color'].default_value = diff_color + (1.0,)
        node.inputs['Roughness'].default_value = 0.0

    else:
        """
        The alpha transparency used by LDraw is too simplistic for Cycles,
        so I'm not using the value here. Other transparent colors
        like 'Milky White' will need special materials.
        """
        mix.inputs['Fac'].default_value = 0.05
        node = nodes.new('ShaderNodeBsdfGlass')
        node.location = -242, 154
        node.inputs['Color'].default_value = diff_color + (1.0,)
        node.inputs['Roughness'].default_value = 0.01

        # The IOR of LEGO brick plastic is 1.46
        node.inputs['IOR'].default_value = 1.46

    aniso = nodes.new('ShaderNodeBsdfGlossy')
    aniso.location = -242, -23
    aniso.inputs['Roughness'].default_value = 0.05

    links.new(mix.outputs[0], out.inputs[0])
    links.new(node.outputs[0], mix.inputs[1])
    links.new(aniso.outputs[0], mix.inputs[2])

    return mat


def getCyclesEmit(mat, diff_color, alpha, luminance):
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90
    mix.inputs['Fac'].default_value = luminance / 100

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    """
    NOTE: The alpha value again is not making much sense here.
    I'm leaving it in, in case someone has an idea how to use it.
    """

    trans = nodes.new('ShaderNodeBsdfTranslucent')
    trans.location = -242, 154
    trans.inputs['Color'].default_value = diff_color + (1.0,)

    emit = nodes.new('ShaderNodeEmission')
    emit.location = -242, -23

    links.new(mix.outputs[0], out.inputs[0])
    links.new(trans.outputs[0], mix.inputs[1])
    links.new(emit.outputs[0], mix.inputs[2])

    return mat


def getCyclesChrome(mat, diff_color):
    """Cycles Chrome Material"""
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    glass = nodes.new('ShaderNodeBsdfGlossy')
    glass.location = -242, 154
    glass.inputs['Color'].default_value = diff_color + (1.0,)
    glass.inputs['Roughness'].default_value = 0.05

    links.new(glass.outputs[0], out.inputs[0])

    return mat


def getCyclesPearlMetal(mat, diff_color, roughness):
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90
    mix.inputs['Fac'].default_value = 0.4

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    glossy = nodes.new('ShaderNodeBsdfGlossy')
    glossy.location = -242, 154
    glossy.inputs['Color'].default_value = diff_color + (1.0,)
    glossy.inputs['Roughness'].default_value = 3.25

    aniso = nodes.new('ShaderNodeBsdfDiffuse')
    aniso.location = -242, -23
    aniso.inputs['Roughness'].default_value = 0.0

    links.new(mix.outputs[0], out.inputs[0])
    links.new(glossy.outputs[0], mix.inputs[1])
    links.new(aniso.outputs[0], mix.inputs[2])

    return mat


def getCyclesRubber(mat, diff_color, alpha):
    """Cycles Rubber Material"""
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    if alpha == 1.0:
        mix.inputs['Fac'].default_value = 0.05
        node = nodes.new('ShaderNodeBsdfDiffuse')
        node.location = -242, 154
        node.inputs['Color'].default_value = diff_color + (1.0,)
        node.inputs['Roughness'].default_value = 0.3

    else:
        """
        The alpha transparency used by LDraw is too simplistic for Cycles,
        so I'm not using the value here. Other transparent colors
        like 'Milky White' will need special materials.
        """
        mix.inputs['Fac'].default_value = 0.1
        node = nodes.new('ShaderNodeBsdfGlass')
        node.location = -242, 154
        node.inputs['Color'].default_value = diff_color + (1.0,)
        node.inputs['Roughness'].default_value = 0.01
        node.inputs['IOR'].default_value = 1.5191

    aniso = nodes.new('ShaderNodeBsdfAnisotropic')
    aniso.location = -242, -23
    aniso.inputs['Roughness'].default_value = 0.5
    aniso.inputs['Anisotropy'].default_value = 0.02

    links.new(mix.outputs[0], out.inputs[0])
    links.new(node.outputs[0], mix.inputs[1])
    links.new(aniso.outputs[0], mix.inputs[2])

    return mat


def getCyclesMilkyWhite(mat, diff_color):
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90
    mix.inputs['Fac'].default_value = 0.1

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    trans = nodes.new('ShaderNodeBsdfTranslucent')
    trans.location = -242, 154
    trans.inputs['Color'].default_value = diff_color + (1.0,)

    diff = nodes.new('ShaderNodeBsdfDiffuse')
    diff.location = -242, -23
    diff.inputs['Color'].default_value = diff_color + (1.0,)
    diff.inputs['Roughness'].default_value = 0.1

    links.new(mix.outputs[0], out.inputs[0])
    links.new(trans.outputs[0], mix.inputs[1])
    links.new(diff.outputs[0], mix.inputs[2])

    return mat

def hasColorValue(line, value):
    """Check if the color value is present"""
    return value in line


def getColorValue(line, value):

    if value in line:
        n = line.index(value)
        return line[n + 1]

def hex_to_rgb(rgb_str):
    """Convert color hex value to RGB value"""
    try:
        from struct import unpack
        int_tuple = unpack('BBB', bytes.fromhex(rgb_str))
        return tuple([val / 255 for val in int_tuple])
    except:
        print("Wong color value: ", rgb_str)
        return (0.61, 0.6, 0.6)