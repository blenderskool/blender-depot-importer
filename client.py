import json, re, os, requests, zipfile

def get_addon_info(path):

  with open(path, 'r') as f:
    initData = f.read()
  
  matches = re.findall(r'bl_info[ \t]*=[ \t]*{((.|\n)*?)}', initData)

  if not matches: return {}

  # Add the curly braces, convert tuples to arrays and single quotes to double quotes
  dict_data = ('{' + matches[0][0] + '}').replace('(', '[').replace(')', ']').replace('\'', '"').replace('\\', '').replace('"""', '"');
  # Remove python comments
  dict_data = re.sub(r'#(.*)', '', dict_data)
  # Merge strings which have been split as
  #   "some_prop": "Hello"
  #                "World",
  #   "next_prop": ...
  dict_data = re.sub(r'[\'"]\n\s*[\'"]', '', dict_data)
  # Remove the trailing comma just before the JSON ends
  dict_data = re.sub(r',[ \t \n]*}', '}', dict_data)

  try:
    addon_info = json.loads(dict_data)
  except:
    return {}

  if '__init__.py' in path:
    temp_src = src_path =  os.path.dirname(path)
    src_folder = os.path.basename(src_path)

    while src_folder in ['src', 'dist', 'build']:
      src_folder = os.path.basename(temp_src)
      temp_src = os.path.dirname(temp_src)

    if ':' in src_folder:
      src_folder = src_folder.split(':')[1]

    addon_info['addon_path'] = src_path
    addon_info['addon_folder'] = src_folder
  else:
    addon_info['addon_path'] = path

  return addon_info


def recursive_find(path, packageData, addons=[], depth=0):
  
  # Max directory depth till the function checks
  if depth == 3:
    return
  
  # If depth is 0 then include the paths from the packageData as the folders have similar names as the
  # resource ID in the packageData
  paths = [ a.replace('/', ':') for a in packageData ] if packageData else os.listdir(path)
  
  # List all file paths in the directory
  for file in paths:
    filepath = os.path.join(os.path.dirname(__file__), path, file)
    # Create __init__ file path
    initPath = os.path.join(filepath, '__init__.py')

    # If the __init__ file exists in the path, then extract bl_info
    # This is the case for the single addon - singe repo
    if os.path.exists(initPath):
      # get bl_info
      addon_info = get_addon_info(initPath)
      if addon_info:
        # add the bl_info to the addons list
        addons.append(addon_info)

    # If the path points to a python file, try extracting the addon info
    elif os.path.isfile(filepath) and filepath.endswith('.py'):
      addon_info = get_addon_info(filepath)
      # If the addon info exists, then another addon has been found :D
      if addon_info:
        addons.append(addon_info)

    # If the path points to a directory, start to check inside the directory
    # This is the case for monorepo which holds multiple addons
    elif os.path.isdir(filepath):
      recursive_find(filepath, None, addons, depth+1)


def get_resources(folder, packageData):
  for addon in packageData:
    r = requests.get('https://api.github.com/repos/' + addon + '/zipball');

    filepath = os.path.join(folder, addon.replace('/', '_')+'.zip')

    with open(filepath, 'wb') as f:
      f.write(r.content)

    with zipfile.ZipFile(filepath, 'r') as zf:
      for i, file in enumerate(zf.filelist):
        if i == 0:
          addon_folder = file
          continue

        file.filename = file.filename.replace(addon_folder.filename, '')
        zf.extract(file, os.path.join(folder, addon.replace('/', ':')))

    # Delete the extracted zipfile
    os.remove(filepath)