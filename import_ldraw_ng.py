# -*- coding: utf-8 -*-
###### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
###### END GPL LICENSE BLOCK #####

'''
bublible:
=========
Hey, guys, please: try to comment every single line of your code - as I did myself - so one know immediately "what line does what"...for God's sake! :-D // <<-- fun intended
'''

### define info part of the script
bl_info = {
	"name": "LDR Importer NG",
	"description": "Import LDraw models in .ldr and .dat format",
	"author": "The LDR Importer Developers and Contributors",
	"version": (0, 1),
	"blender": (2, 69, 0),
	#"api": 31236,
	"location": "File > Import",
	"warning": "No materials!",
	"wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/Import-Export/LDRAW_Importer",  # noqa
	"tracker_url": "https://github.com/le717/LDR-Importer/issues",
	"category": "Import-Export"
}

### import all that is needed for the script to work properly
import os
from time import strftime
import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty, FloatProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper
from mathutils import Matrix, Vector
from struct import unpack

### global variables
mat_list = {}
colors = {}

'''
bublible:
=========
This is my "kind-of-debugger" cos normal way for some strange reasons do not work for me :-(
'''
### define function: DEBUGGER
def dbg(txt, m):
	### create/open external text file
	f = open("blender.log", m)
	### write data to the file
	f.write(str(txt)+"\n")
	### close the file
	f.close()
	### 
	return None

### 
def debugPrint(*myInput):
	"""Debug print with identification timestamp"""
	### 
	myOutput = [str(say) for say in myInput]
	### 
	print("\n[LDR Importer] {0} - {1}\n".format(" ".join(myOutput), strftime("%H:%M:%S")))

### 
def checkEncoding(filePath):
	"""Check the encoding of a file"""
	# Open it, read just the area containing a possible byte mark
	with open(filePath, "rb") as encodeCheck:
		### 
		fileEncoding = encodeCheck.readline(3)
	
	# The file uses UCS-2 (UTF-16) Big Endian encoding
	if fileEncoding == b"\xfe\xff\x00":
		### 
		return "utf_16_be"
	
	# The file uses UCS-2 (UTF-16) Little Endian
	# There seem to be two variants of UCS-2LE that must be checked for
	elif fileEncoding in (b"\xff\xfe0", b"\xff\xfe/"):
		### 
		return "utf_16_le"
	
	# Use LDraw model standard UTF-8
	else:
		### 
		return "utf_8"

### 
class LDRImporterPreferences(AddonPreferences):
	"""LDR Importer Preferences"""
	### 
	bl_idname = __name__
	### 
	ldraw_library_path = StringProperty(name="LDraw Library path", subtype="DIR_PATH")
	
	### 
	def draw(self, context):
		### 
		layout = self.layout
		### 
		layout.prop(self, "ldraw_library_path")

### 
class LDRImporterOperator(bpy.types.Operator, ImportHelper):
	"""LDR Importer Operator"""
	### 
	bl_idname = "import_scene.ldraw_ng"
	### 
	bl_description = "Import an LDraw model (.ldr/.dat)"
	### 
	bl_label = "Import LDraw Model - NG"
	### 
	bl_space_type = "PROPERTIES"
	### 
	bl_region_type = "WINDOW"
	### 
	bl_options = {'REGISTER', 'UNDO', 'PRESET'}
	### 
	filename_ext = ".ldr"
	
	### 
	filter_glob = StringProperty(
		default="*.ldr;*.dat",
		options={'HIDDEN'}
	)
	
	### 
	scale = FloatProperty(
		name="Scale",
		description="Use a specific scale for each brick",
		default=0.05
	)
	
	### 
	resPrims = EnumProperty(
		name="Resolution of part primitives",
		description="Resolution of part primitives",
		items=(
			("Standard", "Standard primitives", "Import primitives using standard resolution"),
			("48", "High resolution primitives", "Import primitives using high resolution"),
			("8", "Low resolution primitives", "Import primitives using low resolution")
		)
	)
	
	### 
	mergeParts = EnumProperty(
		# Leave `name` blank for better display
		name="Merge parts",
		description="Merge the models from the subfiles into one mesh",
			items=(
				("MERGE_TOPLEVEL_PARTS", "Merge top-level parts", "Merge the children of the base model with all their children"),
				("NO_MERGE", "No merge", "Do not merge any meshes"),
				#("MERGE_EVERYTHING", "Merge everything", "Merge the whole model into one mesh")
			)
		)
	
	"""
	cleanUpModel = EnumProperty(
		name="Model Cleanup Options",
		description="Model Cleanup Options",
		items=cleanupOptions
	)
	"""
	### 
	def draw(self, context):
		"""Display import options"""
		### 
		layout = self.layout
		### 
		box = layout.box()
		### 
		box.label("Import Options", icon='SCRIPTWIN')
		### 
		box.prop(self, "scale")
		### 
		box.label("Primitives", icon='MOD_BUILD')
		### 
		box.prop(self, "resPrims", expand=True)
		### 
		box.label("Merge parts", icon='MOD_BOOLEAN')
		### 
		box.prop(self, "mergeParts", expand=True)
		### 
		#box.label("Model Cleanup", icon='EDIT')
		#box.prop(self, "cleanUpModel", expand=True)
	
	### 
	def findLDrawDir(self, context):
		"""
		Attempt to detect Parts Library location
		and populate set proper part search folders.
		"""
		### 
		user_preferences = context.user_preferences
		### 
		addon_prefs = user_preferences.addons[__name__].preferences
		### 
		chosen_path = addon_prefs.ldraw_library_path
		### 
		library_path = ""
		
		### 
		if chosen_path.strip() != "":
			### 
			if os.path.isfile(os.path.join(chosen_path, "LDConfig.ldr")):
				### 
				library_path = chosen_path
			### 
			else:
				### 
				self.report({"ERROR"},
					### 
					"Specified path {0} does not exist".format(hosen_path))
				### 
				return
		### 
		else:
			### 
			path_guesses = [
				r"C:\LDraw",
				r"C:\Program Files\LDraw",
				r"C:\Program Files (x86)\LDraw",
				os.path.expanduser("~/ldraw"),
				os.path.expanduser("~/LDraw"),
				"/usr/local/share/ldraw",
				"/opt/ldraw",
				"/Applications/LDraw",
				"/Applications/ldraw",
			]
			
			### 
			for guess in path_guesses:
				### 
				if os.path.isfile(os.path.join(guess, "LDConfig.ldr")):
					### 
					library_path = guess
					### 
					break
			
			### 
			if not library_path:
				### 
				return
		
		### 
		subdirs = ["models", "parts", "p"]
		### 
		unofficial_path = os.path.join(library_path, "unofficial")
		
		### 
		if os.path.isdir(unofficial_path):
			### 
			subdirs.append(os.path.join("unofficial", "parts"))
			### 
			subdirs.append(os.path.join("unofficial", "p"))
			### 
			subdirs.append(os.path.join("unofficial", "p", str(self.resPrims)))
		
		### 
		subdirs.append(os.path.join("p", str(self.resPrims)))
		### 
		return [os.path.join(library_path, component) for component in subdirs]
	
	### 
	def execute(self, context):
		###
		global colors
		global mat_list
		
		### 
		self.complete = True
		### 
		self.no_mesh_errors = True
		# Part cache - keys = filenames, values = LDrawPart subclasses
		### 
		self.part_cache = {}
		### 
		self.search_paths = self.findLDrawDir(context)
		
		### 
		if not self.search_paths:
			### 
			self.report(
				{"ERROR"},
				("Could not find LDraw Parts Library"
				" after looking in common locations."
				" Please check the addon preferences!")
			)
			### 
			return {"CANCELLED"}
		
		### 
		self.report({"INFO"}, "Search paths are {0}".format(self.search_paths))
		### 
		self.search_paths.insert(0, os.path.dirname(self.filepath))
		### get all LDraw materials
		scanLDConfig(self)
		### 
		model = self.parse_part(self.filepath)()
		
		# Rotate model to proper LDraw orientation
		model.obj.matrix_world = Matrix((
			(1.0,  0.0, 0.0, 0.0),  # noqa
			(0.0,  0.0, 1.0, 0.0),  # noqa
			(0.0, -1.0, 0.0, 0.0),
			(0.0,  0.0, 0.0, 1.0)   # noqa
		)) * self.scale
		
		### 
		if not self.complete:
			### 
			self.report({"WARNING"}, ("Not all parts could be found. "
						"Check the console for a list."))
		
		### 
		if not self.no_mesh_errors:
			### 
			self.report({"WARNING"}, "Some of the meshes loaded contained errors.")
		
		'''
		bublible:
		=========
		I've moved the function here from LDRImporterPreferences class
		cos your original code was unable to call it from there
		...so now merging works OK as it should ;-)
		'''
		### define function
		def emptyToMesh(obj, emptyMesh):
			"""Replace Empty with blank mesh"""
			### create name
			name = obj.name
			### create new object
			obj_replacement = bpy.data.objects.new(name=name, object_data=emptyMesh)
			### set its coordinates according to old (original) object's matrix
			obj_replacement.matrix_local = obj.matrix_local
			### set parent
			obj_replacement.parent = obj.parent
			### put new object to the scene
			bpy.context.scene.objects.link(obj_replacement)
			
			### iterate thru all objects childs
			for child in obj.children:
				### replace children's parent
				child.parent = obj_replacement
				
			### remove old object from the scene
			bpy.context.scene.objects.unlink(obj)
			### replace old object
			obj = obj_replacement
			### set new name
			obj.name = name
			### return new object
			return obj
		
		### iterate thru all boject's childs
		for child in model.obj.children:
			'''
			bublible:
			=========
			I've deleted your original function in LDRImporterPreferences class
			and instead put its code here as it was not used anywhere else in the script
			(as there is a little chance it will be in the future as import itself is working and no additional stuff is needed...probably :D)
			+ it again did not work calling it from here as it was in your original code guys, but now it also works ;-)
			'''
			### create new empty mesh
			emptyMesh = bpy.data.meshes.new(name=child.name)
			### set active object
			bpy.context.scene.objects.active = child
			### select all children of the object
			bpy.ops.object.select_grouped(type="CHILDREN_RECURSIVE", extend=False)
			### sign all selected objects as those ones that needs to be merged together as one final object
			to_merge = bpy.context.selected_objects
			
			### if child type is "EMPTY"
			if child.type == "EMPTY":
				### create empty mesh
				child = emptyToMesh(child, emptyMesh)
			
			### iterate thru all objects that needs to be merged inyo one
			for obj in to_merge:
				### if actually iterated object type is "EMPTY"
				if obj.type == "EMPTY":
					### make empty mesh
					obj = emptyToMesh(obj, emptyMesh)
			
				### select actually iterated object
				obj.select = True
			
			### set actualy iterated object as active
			bpy.context.scene.objects.active = child
			### select object
			child.select = True
			### join all selected objects into one final object
			bpy.ops.object.join()
			### 
			bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
			### set name of the final merged object according to real brick name (!!!)
			child.name = model.obj.name
			
			#dbg(model.obj.name, "a")
		
		'''
		if str(self.mergeParts) == "MERGE_TOPLEVEL_PARTS":
			for child in model.obj.children:
				flattenHierarchy(child)
		elif str(self.mergeParts) == "MERGE_EVERYTHING":
			flattenHierarchy(model.obj)
		'''
		#dbg(mat_list, "a")
		### 
		return {"FINISHED"}
	
	### define function
	def findParsePart(self, filename):
		# Use OS native path separators
		if "\\" in filename:
			### 
			filename = filename.replace("\\", os.path.sep)
		
		# Remove possible colons in filenames
		#TODO: Expand to use a regex search for all illegal characters on Windows
		### 
		if ":" in filename:
			### 
			filename = filename.replace(":", os.path.sep)
		
		### 
		if filename in self.part_cache:
			### 
			return self.part_cache[filename]
		
		### 
		for testpath in self.search_paths:
			### 
			path = os.path.join(testpath, filename)
			### 
			if os.path.isfile(path):
				### 
				LoadedPart = self.parse_part(path)
				### 
				self.part_cache[filename] = LoadedPart
				### 
				return LoadedPart
		"""
		If we haven't returned by now, the part hasn't been found.
		We will therefore send a warning, create a class for the missing
		part, put it in the cache, and return it.

		The object created by this class will be an empty, because its mesh
		attribute is set to None.
		"""
		### 
		self.report({"WARNING"}, "Could not find part {0}".format(filename))
		### 
		self.complete = False
		
		### define class
		class NonFoundPart(LDrawPart):
			### define name
			part_name = filename + ".NOTFOUND"
			### define meash
			mesh = None
			### initiate array
			subpart_info = []
		
		### add non-existent part to array of cached (=already iterated) parts
		self.part_cache[filename] = NonFoundPart
		### return non-existent part
		return NonFoundPart
	
	### define function: CREATE EVERY PART/SUBPART
	def parse_part(self, filename):
		''' filename = name of actual LDraw part/subpart '''
		### if actually iterated part was already iterated sometime before
		if filename in self.part_cache:
			### return its previously iterated instance from array
			return self.part_cache[filename]
		
		# Points are Vector instances
		# Faces are tuples of 3/4 point indices
		# Lines are tuples of 2 point indices
		# Subpart info contains tuples of the form
		#    (LDrawPart subclass, Matrix instance)
		### initiate arrays
		loaded_points = []
		loaded_faces = []
		loaded_materials = []
		_subpart_info = []
		_eng = bpy.context.scene.render.engine
		
		### define function
		def element_from_points(length, values):
			### initiate empty array
			indices = []
			### 
			values = [float(s) for s in values]
			
			### if number of values is less than...
			if len(values) < length * 3:
				#### set error info for user
				raise ValueError("Not enough values for {0} points".format(length))
			
			#### iterate thru all values
			for point_n in range(length):
				#### define vars
				x, y, z = values[point_n * 3:point_n * 3 + 3]
				### 
				indices.append(len(loaded_points))
				### add vector values into array
				loaded_points.append(Vector((x, y, z)))
				
			### return needed value
			return indices
		
		### read data from actual part/subpart .dat file
		with open(filename, "rt", encoding=checkEncoding(filename)) as f:
			#dbg(filename, "a")
			### iterate thru all .dat data:
			### lineno = number of actual line being iterated
			### line = actual line being iterated
			### f = filename = actual part/subpart .dat data being readed
			for lineno, line in enumerate(f, start=1):
				### array of every element (=value) in actual line
				split = [item.strip() for item in line.split()]
				
				# Skip blank lines
				if len(split) == 0:
					### 
					continue
				
				#TODO: BIG: Error case handling.
				# - Line has too many elements => warn user? Skip line?
				# - Line has too few elements => skip line and warn user
				# - Coordinates cannot be converted to float => skip line
				#     and warn user
				# - (for subfiles) detect and skip circular references,
				#     including indirect ones...
				
				### if value of array elemnt equals given value: SET PART
				if split[0] == "1":
					# If we've found a subpart, append to _subpart_info
					# !!! We need to handle circular references here !!!
					### 
					if len(split) < 15:
						### 
						continue
					
					### 
					translation = Vector([float(s) for s in split[2:5]])
					### 
					m_row1 = [float(s) for s in split[5:8]]
					### 
					m_row2 = [float(s) for s in split[8:11]]
					### 
					m_row3 = [float(s) for s in split[11:14]]
					### 
					matrix = Matrix((m_row1, m_row2, m_row3)).to_4x4()
					### set object location
					matrix.translation = translation
					### set filename according to array element of given index
					filename = split[14]
					### 
					part_class = self.findParsePart(filename)
					### 
					_subpart_info.append((part_class, matrix))
				
				### if value of array elemnt equals given value: MAKE TRIs
				elif split[0] == "3":
					### 
					try:
						### 
						tri = element_from_points(3, split[2:11])
					### 
					except ValueError:
						### 
						self.no_mesh_errors = False
						### 
						continue
					### 
					loaded_faces.append(tri)
					
					# #############################################################################
					loaded_materials.append(split[1])
					# #############################################################################
				
				### if value of array elemnt equals given value: MAKE QUADs
				elif split[0] == "4":
					### 
					try:
						### 
						quad = element_from_points(4, split[2:14])
					### 
					except ValueError:
						### 
						self.no_mesh_errors = False
						### 
						continue
					### 
					loaded_faces.append(quad)
					
					# #############################################################################
					loaded_materials.append(split[1])
					# #############################################################################
		
		### if there are some faces to create
		if len(loaded_faces) > 0:
			### create new mesh
			loaded_mesh = bpy.data.meshes.new(filename)
			### make its "face" from data values
			loaded_mesh.from_pydata(loaded_points, [], loaded_faces)
			### 
			loaded_mesh.validate()
			### 
			loaded_mesh.update()
			
			# ####################################################################################
			### itterate thru all polygons of the mesh
			for i, f in enumerate(loaded_mesh.polygons):
				### 
				_n = loaded_materials[i]
				
				### if we are using CYCLES as renderer
				if _eng == 'CYCLES':
					### create material accordingly to this renderer
					_mat = getCyclesMaterial(_n)
				### if we are using some else renderer
				else:
					### create material accordingly to that renderer
					_mat = getMaterial(_n)
				
				### if material was created
				if _mat is not None:
					#dbg(_mat.name, "a")
					### and this ,aterial is not yet assigned to mesh
					if loaded_mesh.materials.get(_mat.name) is None:
						### assign it
						loaded_mesh.materials.append(_mat)
					
					### 
					f.material_index = loaded_mesh.materials.find(_mat.name)
			# ####################################################################################
		### if there ar eno faces to create
		else:
			### 
			loaded_mesh = None
		
		### 
		if len(_subpart_info) > 0 or loaded_mesh:
			# Create a new part class and return it.
			### 
			class LoadedPart(LDrawPart):
				"""Create a new part class, put it in the cache, and return it."""
				### 
				mesh = loaded_mesh
				# Take off the file extensions
				### 
				part_name = ".".join(filename.split(".")[:-1])
				### 
				subpart_info = _subpart_info
			
			### 
			return LoadedPart
		### 
		else:
			### 
			return NullPart

def scanLDConfig(self):
	"""Scan LDConfig to get the material color info."""
	# LDConfig.ldr does not exist for some reason
	
	'''
	bublible:
	=========
	As you can see I have "hardcoded" path to LDraw here as I was unable to understand you code enough up to level of using you function for this... :-(
	...so feel free to change it accordingly to your function... ;-)
	
	'''
	### open LDConfig.ldr
	with open(os.path.join("C:\Program Files (x86)\LDraw", "LDConfig.ldr"), "rt", encoding="utf_8") as ldconfig:
		### read its lines one-by-one
		ldconfig_lines = ldconfig.readlines()
		
		### iterate thru every line
		for line in ldconfig_lines:
			### if line has more than 3 letters/spaces
			if len(line) > 3:
				### if 3th and 4th letters quals to value belove
				if line[2:4].lower() == '!c':
					### make array from the line
					line_split = line.split()
					### get material's name (e.g. "Blue") from the array
					name = line_split[2]
					### get material's code (e.g. "1") from the array
					code = line_split[4]
					### make new object "color" with attributes
					color = {
						"name": name,
						"color": hex_to_rgb(line_split[6][1:]),
						"alpha": 1.0,
						"luminance": 0.0,
						"material": "BASIC"
					}
					
					### if actual color type is ALPHA
					if hasColorValue(line_split, "ALPHA"):
						### 
						color["alpha"] = int(getColorValue(line_split, "ALPHA")) / 256.0
					
					### if actual color type is LUMINANCE
					if hasColorValue(line_split, "LUMINANCE"):
						### 
						color["luminance"] = int(getColorValue(line_split, "LUMINANCE"))
					
					### if actual color type is CHROME
					if hasColorValue(line_split, "CHROME"):
						### 
						color["material"] = "CHROME"
					
					### if actual color type is PEARLESCENT
					if hasColorValue(line_split, "PEARLESCENT"):
						### 
						color["material"] = "PEARLESCENT"
					
					### if actual color type is RUBBER
					if hasColorValue(line_split, 'RUBBER'):
						### 
						color["material"] = "RUBBER"
					
					### if actual color type is METAL
					if hasColorValue(line_split, "METAL"):
						### 
						color["material"] = "METAL"
					
					### if actual color type is MATERIAL
					if hasColorValue(line_split, "MATERIAL"):
						### 
						subline = line_split[line_split.index("MATERIAL"):]
						### 
						color["material"] = getColorValue(subline, "MATERIAL")
						### 
						color["secondary_color"] = getColorValue(subline, "VALUE")[1:]
						### 
						color["fraction"] = getColorValue(subline, "FRACTION")
						### 
						color["vfraction"] = getColorValue(subline, "VFRACTION")
						### 
						color["size"] = getColorValue(subline, "SIZE")
						### 
						color["minsize"] = getColorValue(subline, "MINSIZE")
						### 
						color["maxsize"] = getColorValue(subline, "MAXSIZE")
					
					### add new color to the list
					colors[code] = color

### define function
def hasColorValue(line, value):
	"""Check if the color value is present"""
	### 
	return value in line

### 
def getColorValue(line, value):
	### 
	if value in line:
		### 
		n = line.index(value)
		### 
		return line[n + 1]

def hex_to_rgb(rgb_str):
	"""Convert color hex value to RGB value"""
	### 
	int_tuple = unpack('BBB', bytes.fromhex(rgb_str))
	### 
	return tuple([val / 255 for val in int_tuple])

### define function: MAKE CYCLES MATERIAL
def getCyclesMaterial(colour):
	"""Get Cycles Material Values"""
	#dbg("CYCLES", "a")
	
	### if material exists already
	if colour in colors:
		### 
		if not (colour in mat_list):
			### 
			col = colors[colour]
			### 
			if col["name"] == "Milky_White":
				### 
				mat = getCyclesMilkyWhite("Mat_{0}_".format(colour), col["color"])
			### 
			elif (col["material"] == "BASIC" and col["luminance"]) == 0:
				### 
				mat = getCyclesBase("Mat_{0}_".format(colour), col["color"], col["alpha"])
			### 
			elif col["luminance"] > 0:
				### 
				mat = getCyclesEmit("Mat_{0}_".format(colour), col["color"], col["alpha"], col["luminance"])
			### 
			elif col["material"] == "CHROME":
				### 
				mat = getCyclesChrome("Mat_{0}_".format(colour), col['color'])
			### 
			elif col["material"] == "PEARLESCENT":
				### 
				mat = getCyclesPearlMetal("Mat_{0}_".format(colour), col["color"], 0.2)
			### 
			elif col["material"] == "METAL":
				### 
				mat = getCyclesPearlMetal("Mat_{0}_".format(colour), col["color"], 0.5)
			### 
			elif col["material"] == "RUBBER":
				### 
				mat = getCyclesRubber("Mat_{0}_".format(colour), col["color"], col["alpha"])
			### 
			else:
				### 
				mat = getCyclesBase("Mat_{0}_".format(colour), col["color"], col["alpha"])
			### 
			mat_list[colour] = mat
		### 
		return mat_list[colour]
	### if material is not in materials yet
	else:
		### 
		mat_list[colour] = getCyclesBase("Mat_{0}_".format(colour), (1, 1, 0), 1.0)
		### 
		return mat_list[colour]
	
	### 
	return None

### 
def getCyclesBase(name, diff_color, alpha):
	#dbg("diff_color="+str(diff_color), "a")
	"""Base Material, Mix shader and output node"""
	### 
	mat = bpy.data.materials.new(name)
	### 
	mat.use_nodes = True
	
	# Set viewport color to be the same as material color
	mat.diffuse_color = diff_color
	
	### 
	nodes = mat.node_tree.nodes
	### 
	links = mat.node_tree.links
	
	### 
	for n in nodes:
		### 
		nodes.remove(n)
	
	### 
	mix = nodes.new('ShaderNodeMixShader')
	### 
	mix.location = 0, 90
	
	### 
	out = nodes.new('ShaderNodeOutputMaterial')
	### 
	out.location = 290, 100
	
	### 
	if alpha == 1.0:
		### 
		mix.inputs['Fac'].default_value = 0.05
		### 
		node = nodes.new('ShaderNodeBsdfDiffuse')
		### 
		node.location = -242, 154
		### 
		node.inputs['Color'].default_value = diff_color + (1.0,)
		### 
		node.inputs['Roughness'].default_value = 0.0
	### 
	else:
		"""
		The alpha transparency used by LDraw is too simplistic for Cycles,
		so I'm not using the value here. Other transparent colors
		like 'Milky White' will need special materials.
		"""
		### 
		mix.inputs['Fac'].default_value = 0.05
		### 
		node = nodes.new('ShaderNodeBsdfGlass')
		### 
		node.location = -242, 154
		### 
		node.inputs['Color'].default_value = diff_color + (1.0,)
		### 
		node.inputs['Roughness'].default_value = 0.01

		# The IOR of LEGO brick plastic is 1.46
		node.inputs['IOR'].default_value = 1.46
	
	### 
	aniso = nodes.new('ShaderNodeBsdfGlossy')
	### 
	aniso.location = -242, -23
	### 
	aniso.inputs['Roughness'].default_value = 0.05
	
	### 
	links.new(mix.outputs[0], out.inputs[0])
	### 
	links.new(node.outputs[0], mix.inputs[1])
	### 
	links.new(aniso.outputs[0], mix.inputs[2])
	
	### 
	return mat

### 
def getCyclesEmit(name, diff_color, alpha, luminance):
	### 
	mat = bpy.data.materials.new(name)
	### 
	mat.use_nodes = True
	
	### 
	nodes = mat.node_tree.nodes
	### 
	links = mat.node_tree.links
	
	### 
	for n in nodes:
		### 
		nodes.remove(n)
	
	### 
	mix = nodes.new('ShaderNodeMixShader')
	### 
	mix.location = 0, 90
	### 
	mix.inputs['Fac'].default_value = luminance / 100
	
	### 
	out = nodes.new('ShaderNodeOutputMaterial')
	### 
	out.location = 290, 100
	
	"""
	NOTE: The alpha value again is not making much sense here.
	I'm leaving it in, in case someone has an idea how to use it.
	"""
	
	### 
	trans = nodes.new('ShaderNodeBsdfTranslucent')
	### 
	trans.location = -242, 154
	### 
	trans.inputs['Color'].default_value = diff_color + (1.0,)
	
	### 
	emit = nodes.new('ShaderNodeEmission')
	### 
	emit.location = -242, -23
	
	### 
	links.new(mix.outputs[0], out.inputs[0])
	### 
	links.new(trans.outputs[0], mix.inputs[1])
	### 
	links.new(emit.outputs[0], mix.inputs[2])
	
	### 
	return mat

### 
def getCyclesChrome(name, diff_color):
	"""Cycles Chrome Material"""
	### 
	mat = bpy.data.materials.new(name)
	### 
	mat.use_nodes = True
	
	### 
	nodes = mat.node_tree.nodes
	### 
	links = mat.node_tree.links
	
	### 
	for n in nodes:
		### 
		nodes.remove(n)
	
	### 
	out = nodes.new('ShaderNodeOutputMaterial')
	### 
	out.location = 290, 100
	
	### 
	glass = nodes.new('ShaderNodeBsdfGlossy')
	### 
	glass.location = -242, 154
	### 
	glass.inputs['Color'].default_value = diff_color + (1.0,)
	### 
	glass.inputs['Roughness'].default_value = 0.05
	
	### 
	links.new(glass.outputs[0], out.inputs[0])
	
	### 
	return mat

### 
def getCyclesPearlMetal(name, diff_color, roughness):
	### 
	mat = bpy.data.materials.new(name)
	### 
	mat.use_nodes = True
	
	### 
	nodes = mat.node_tree.nodes
	### 
	links = mat.node_tree.links
	
	### 
	for n in nodes:
		### 
		nodes.remove(n)
	
	### 
	mix = nodes.new('ShaderNodeMixShader')
	### 
	mix.location = 0, 90
	### 
	mix.inputs['Fac'].default_value = 0.4
	
	### 
	out = nodes.new('ShaderNodeOutputMaterial')
	### 
	out.location = 290, 100
	
	### 
	glossy = nodes.new('ShaderNodeBsdfGlossy')
	### 
	glossy.location = -242, 154
	### 
	glossy.inputs['Color'].default_value = diff_color + (1.0,)
	### 
	glossy.inputs['Roughness'].default_value = 3.25
	
	### 
	aniso = nodes.new('ShaderNodeBsdfDiffuse')
	### 
	aniso.location = -242, -23
	### 
	aniso.inputs['Roughness'].default_value = 0.0
	
	### 
	links.new(mix.outputs[0], out.inputs[0])
	### 
	links.new(glossy.outputs[0], mix.inputs[1])
	### 
	links.new(aniso.outputs[0], mix.inputs[2])
	
	### 
	return mat

### 
def getCyclesRubber(name, diff_color, alpha):
	"""Cycles Rubber Material"""
	### 
	mat = bpy.data.materials.new(name)
	### 
	mat.use_nodes = True
	
	### 
	nodes = mat.node_tree.nodes
	### 
	links = mat.node_tree.links
	
	### 
	for n in nodes:
		### 
		nodes.remove(n)
	
	### 
	mix = nodes.new('ShaderNodeMixShader')
	### 
	mix.location = 0, 90
	
	### 
	out = nodes.new('ShaderNodeOutputMaterial')
	### 
	out.location = 290, 100
	
	### 
	if alpha == 1.0:
		### 
		mix.inputs['Fac'].default_value = 0.05
		### 
		node = nodes.new('ShaderNodeBsdfDiffuse')
		### 
		node.location = -242, 154
		### 
		node.inputs['Color'].default_value = diff_color + (1.0,)
		### 
		node.inputs['Roughness'].default_value = 0.3
	### 
	else:
		"""
		The alpha transparency used by LDraw is too simplistic for Cycles,
		so I'm not using the value here. Other transparent colors
		like 'Milky White' will need special materials.
		"""
		### 
		mix.inputs['Fac'].default_value = 0.1
		### 
		node = nodes.new('ShaderNodeBsdfGlass')
		### 
		node.location = -242, 154
		### 
		node.inputs['Color'].default_value = diff_color + (1.0,)
		### 
		node.inputs['Roughness'].default_value = 0.01
		### 
		node.inputs['IOR'].default_value = 1.5191
	
	### 
	aniso = nodes.new('ShaderNodeBsdfAnisotropic')
	### 
	aniso.location = -242, -23
	### 
	aniso.inputs['Roughness'].default_value = 0.5
	### 
	aniso.inputs['Anisotropy'].default_value = 0.02
	
	### 
	links.new(mix.outputs[0], out.inputs[0])
	### 
	links.new(node.outputs[0], mix.inputs[1])
	### 
	links.new(aniso.outputs[0], mix.inputs[2])
	
	### 
	return mat

### 
def getCyclesMilkyWhite(name, diff_color):
	
	### 
	mat = bpy.data.materials.new(name)
	### 
	mat.use_nodes = True
	### 
	nodes = mat.node_tree.nodes
	### 
	links = mat.node_tree.links
	
	### 
	for n in nodes:
		### 
		nodes.remove(n)
	
	### 
	mix = nodes.new('ShaderNodeMixShader')
	### 
	mix.location = 0, 90
	### 
	mix.inputs['Fac'].default_value = 0.1
	
	### 
	out = nodes.new('ShaderNodeOutputMaterial')
	### 
	out.location = 290, 100
	
	### 
	trans = nodes.new('ShaderNodeBsdfTranslucent')
	### 
	trans.location = -242, 154
	### 
	trans.inputs['Color'].default_value = diff_color + (1.0,)
	
	### 
	diff = nodes.new('ShaderNodeBsdfDiffuse')
	### 
	diff.location = -242, -23
	### 
	diff.inputs['Color'].default_value = diff_color + (1.0,)
	### 
	diff.inputs['Roughness'].default_value = 0.1
	
	### 
	links.new(mix.outputs[0], out.inputs[0])
	### 
	links.new(trans.outputs[0], mix.inputs[1])
	### 
	links.new(diff.outputs[0], mix.inputs[2])
	
	### 
	return mat

### define function: MAKE BLENDER MATERIAL
def getMaterial(colour):
	"""Get Blender Internal Material Values"""
	#dbg("BLENDER", "a")
	### 
	if colour in colors:
		### 
		if not (colour in mat_list):
			### 
			mat = bpy.data.materials.new("Mat_{0}_".format(colour))
			### 
			col = colors[colour]
			### 
			mat.diffuse_color = col["color"]
			### 
			alpha = col["alpha"]
			
			### 
			if alpha < 1.0:
				### 
				mat.use_transparency = True
				### 
				mat.alpha = alpha
			### 
			mat.emit = col["luminance"] / 100
			
			### 
			if col["material"] == "CHROME":
				### 
				mat.specular_intensity = 1.4
				### 
				mat.roughness = 0.01
				### 
				mat.raytrace_mirror.use = True
				### 
				mat.raytrace_mirror.reflect_factor = 0.3
			### 
			elif col["material"] == "PEARLESCENT":
				### 
				mat.specular_intensity = 0.1
				### 
				mat.roughness = 0.32
				### 
				mat.raytrace_mirror.use = True
				### 
				mat.raytrace_mirror.reflect_factor = 0.07
			### 
			elif col["material"] == "RUBBER":
				### 
				mat.specular_intensity = 0.19
			### 
			elif col["material"] == "METAL":
				### 
				mat.specular_intensity = 1.473
				### 
				mat.specular_hardness = 292
				### 
				mat.diffuse_fresnel = 0.93
				### 
				mat.darkness = 0.771
				### 
				mat.roughness = 0.01
				### 
				mat.raytrace_mirror.use = True
				### 
				mat.raytrace_mirror.reflect_factor = 0.9
			#elif col["material"] == "GLITTER":
				#slot = mat.texture_slots.add()
				#tex = bpy.data.textures.new("GlitterTex", type = "STUCCI")
				#tex.use_color_ramp = True
				#slot.texture = tex
			### 
			else:
				### 
				mat.specular_intensity = 0.2
				### 
				mat_list[colour] = mat
		### 
		return mat_list[colour]
	
	### 
	return None
### 
class LDrawPart:
	"""
	Base class for parts/models/subfiles.
	Should not be instantiated directly!
	"""
	### 
	def __init__(self, parent=None, depth=0, transform=Matrix()):
		### 
		self.obj = bpy.data.objects.new(name=self.part_name, object_data=self.mesh)
		### 
		self.obj.parent = parent
		### 
		self.obj.matrix_local = transform
		### 
		self.subparts = []
		
		### 
		if len(self.subpart_info) >= 1:
			### 
			for subpart, subpart_matrix in self.subpart_info:
				### 
				self.subparts.append(
					subpart(
						parent=self.obj,
						depth=depth + 1,
						transform=subpart_matrix
					)
				)
		### 
		bpy.context.scene.objects.link(self.obj)

### 
class NullPart(LDrawPart):
	"""Empty part, used for parts containing no tris, no quads and no subfiles"""
	### 
	def __init__(self, parent=None, depth=0, transform=Matrix()):
		### 
		pass

### 
def menuItem(self, context):
	"""Import menu listing"""
	### 
	self.layout.operator(LDRImporterOperator.bl_idname, text="LDraw - NG (.ldr/.dat)")

### 
def register():
	"""Register menu misting"""
	### 
	bpy.utils.register_module(__name__)
	### 
	bpy.types.INFO_MT_file_import.append(menuItem)

### 
def unregister():
	"""Unregister menu listing"""
	### 
	bpy.utils.unregister_module(__name__)
	### 
	bpy.types.INFO_MT_file_import.remove(menuItem)

### 
if __name__ == "__main__":
	### 
	register()
