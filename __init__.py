bl_info = {
    "name": "Blender Depot importer",
    "description": "Resources importer from Blender Depot",
    "author": "Akash Hamirwasia",
    "version": (0, 1, 0),
    "blender": (2, 79, 0),
    "location": "User Preferences > Addons > Blender Depot importer",
    "warning": "", # used for warning icon and text in addons panel
    "wiki_url": "https://github.com/blenderskool/blender-depot-importer/wiki/",
    "tracker_url": "https://github.com/blenderskool/blender-depot-importer/issues",
    "support": "COMMUNITY",
    "category": "Import-Export"
}

import bpy, json, os, shutil
from bpy_extras.io_utils import ImportHelper, ExportHelper
from . import client

addons = []

def isntCompatible(addon):
  return tuple(addon['blender']) > bpy.app.version

class ImportPackage(bpy.types.Operator, ImportHelper):
  """Import a Blender Depot package file"""
  bl_idname = "depot.import"
  bl_label = "Import package"

  filter_glob = bpy.props.StringProperty(
                  default="*.json",
                  options={'HIDDEN'},
                )

  def execute(self, context):
    global addons
    addons = []

    with open(self.filepath) as f:
      data = json.load(f)

    # Importer compatibility checks are done here.
    # This is to make sure that only compatible packages from the site and 'tried' to be installed by the addon
    # If the package file is incompatible, then this addon must be updated to support the new package file
    if int(data['min_version'].replace('.', '')) > int(''.join(str(n) for n in bl_info['version'])):
      self.report({'WARNING'}, 'Incompatible package. Download latest version of Blender Depot importer')
      return {'CANCELLED'}

    addons_dir = os.path.join(os.path.dirname(__file__), 'addons')

    client.get_resources(addons_dir, data['addons'])
    client.recursive_find(addons_dir, data['addons'], addons)
    
    return {'FINISHED'}


class ItemToggle(bpy.types.Operator):
  """View more item info"""
  bl_idname = "depot.ui_item_toggle"
  bl_label = 'Toggle Item'

  item = bpy.props.StringProperty()

  def execute(self, context):

    for addon in addons:
      if addon.get('name') + addon.get('author') == self.item:
        addon['show_expanded'] = not addon.get('show_expanded')
        break

    return {'FINISHED'}


class ItemSelect(bpy.types.Operator):
  """Select/Deselect this item"""
  bl_idname = "depot.ui_item_select"
  bl_label = 'Select Item'

  item = bpy.props.StringProperty()

  def execute(self, context):

    for addon in addons:
      if addon.get('name') + addon.get('author') == self.item:
        addon['selected'] = not addon.get('selected')
        break

    return {'FINISHED'}


class GroupSelect(bpy.types.Operator):
  """Select/Deselct All the items"""
  bl_idname = "depot.ui_group_select"
  bl_label = 'Group select'

  all = bpy.props.BoolProperty()

  def execute(self, context):

    for addon in addons:
      if isntCompatible(addon): continue

      addon['selected'] = self.all

    return {'FINISHED'}


class ImportSelected(bpy.types.Operator):
  """Install the selected items"""
  bl_idname = "depot.import_selected"
  bl_label = "Import Selected"

  @classmethod
  def poll(cls, context):
    return len([ addon for addon in addons if addon.get('selected') ])

  def execute(self, context):
    addons_path = bpy.utils.user_resource('SCRIPTS', 'addons')

    for addon in addons:
      if addon.get('selected'):
        src_path = addon['addon_path']
        src_folder = addon.get('addon_folder')

        if os.path.isdir(src_path):
          shutil.copytree(src_path, os.path.join(addons_path, src_folder if src_folder else addon['name'] ))
        elif os.path.isfile(src_path):
          shutil.copyfile(src_path, os.path.join(addons_path, os.path.basename(src_path)))

    # Refresh the addons list
    bpy.ops.wm.addon_refresh()
    self.report({'INFO'}, 'Installed the selected addons')
    return {'FINISHED'}

class ClearCache(bpy.types.Operator):
  """Clear the cached files from previous packages. NOTE: This does not remove installed addons"""
  bl_idname = "depot.clear_cache"
  bl_label = 'Clear cache'

  def execute(self, context):
    global addons
    addons = []

    for folder in ['addons']:
      folder_path = os.path.join(os.path.dirname(__file__), folder)
      # Delete a folder and its contents
      shutil.rmtree(folder_path)
      # Re-create the folder
      os.mkdir(folder_path)


    return {'FINISHED'}

class DepotPrefs(bpy.types.AddonPreferences):
    bl_idname = __name__

    def draw(self, context):
      layout = self.layout
      col = layout.column()
      split = col.split(percentage = 0.8, align = True)
      col = split.column(align = True)
      col.scale_y = 1.5
      col.operator(ImportPackage.bl_idname, text = 'Import package', icon = 'PACKAGE')
      col = split.column(align = True)
      col.scale_y = 1.5
      col.operator(ClearCache.bl_idname, text = 'Clear cache', icon = 'LOAD_FACTORY')

      col = layout.column()

      if addons:
        col.separator()
        col.label(text = 'Found '+str(len(addons))+' addons in the package', icon = 'FILE_TICK')

        row = col.row(align = True)
        row.alignment = 'RIGHT'
        row.operator(GroupSelect.bl_idname, text = 'Select All').all = True
        row.operator(GroupSelect.bl_idname, text = 'Deselect All').all = False

        for addon in addons:
          box = layout.box()
          col = box.column()

          row = col.row()
          row.operator(ItemToggle.bl_idname,
                        text = '',
                        icon = 'TRIA_DOWN' if addon.get('show_expanded') else 'TRIA_RIGHT',
                        emboss = False
                      ).item = addon.get('name') + addon.get('author')

          row.label(text = addon.get('category') + ': ' + addon.get('name'))

          # Check the addon compatibility with user's installation of Blender
          if isntCompatible(addon):
            row = row.row()
            row.alignment = 'RIGHT'
            row.label(text = 'Incompatible addon', icon = 'ERROR')
          else:
            # If addon is compatible, allow user to select
            row.operator(ItemSelect.bl_idname,
              text = '',
              icon = 'CHECKBOX_HLT' if addon.get('selected') else 'CHECKBOX_DEHLT',
              emboss = False,
            ).item = addon.get('name') + addon.get('author')


          if addon.get('show_expanded'):
            col.separator()
            try:
              col.label(text = 'Description: '+addon.get('description'))
              col.label(text = 'Author: '+addon.get('author'))
              col.label(text = 'Version: '+'.'.join(str(n) for n in addon.get('version')))
              col.label(text = 'Compatibility: Blender '+'.'.join(str(n) for n in addon.get('blender'))+' and above')
              # col.label(text = 'Path: '+addon.get('addon_path'))
            except:
              col.label(text = 'There was some problem in showing additional info', icon = 'ERROR')

        row = layout.row()
        row.scale_y = 1.5
        row.alignment = 'CENTER'
        row.operator(ImportSelected.bl_idname, text = 'Install '+ str(len([ a for a in addons if a.get('selected') ])) +' addons', icon = 'APPEND_BLEND')


def register():
  bpy.utils.register_class(DepotPrefs)
  bpy.utils.register_class(ImportPackage)
  bpy.utils.register_class(ItemToggle)
  bpy.utils.register_class(ItemSelect)
  bpy.utils.register_class(GroupSelect)
  bpy.utils.register_class(ImportSelected)
  bpy.utils.register_class(ClearCache)

def unregister():
  bpy.utils.unregister_class(DepotPrefs)
  bpy.utils.unregister_class(ImportPackage)
  bpy.utils.unregister_class(ItemToggle)
  bpy.utils.unregister_class(ItemSelect)
  bpy.utils.unregister_class(GroupSelect)
  bpy.utils.unregister_class(ImportSelected)
  bpy.utils.unregister_class(ClearCache)