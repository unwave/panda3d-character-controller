def edit_file(file_path, func, encoding = None):
    with open(file_path, 'r+', encoding = encoding) as file:
        data = func(file.read())
        file.seek(0)
        file.write(data)
        file.truncate()

def remove_spec_rgba():
    def edit_file(file_path, func, encoding = None):
        with open(file_path, 'r+', encoding = encoding) as file:
            data = func(file.read())
            file.seek(0)
            file.write(data)
            file.truncate()

    import re
    job = get_job() # type: ignore
    edit_file(job['fname'], lambda data: re.sub(r' *<Scalar> (spec[rgba]).+?}', '', data))

def convert_properties():
    import bpy
    atool_properties = bpy.context.scene.get('atool_properties')
    if atool_properties:
        for object in bpy.data.objects[:]:
            for key, value in list(object.items()):

                prop = atool_properties.get(key)
                if prop == None:
                    continue

                if prop['type'] == 'enum':
                    object.pop(key)
                    object[key] = prop['value'][value]
                if prop['type'] == 'bool':
                    object.pop(key)#
                    object[key] = str(bool(value))

def set_rigid_body():
    import bpy

    for object in bpy.data.objects:
        if object.get('No Collider'):
            continue

        try:
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = object
            object.select_set(True)
            bpy.ops.rigidbody.object_add()
            bpy.context.object.rigid_body.collision_shape = 'MESH'
        except:
            pass
        

def set_use_nodes_for_all_materials():
    import bpy

    for material in bpy.data.materials.values():
        material.use_nodes = True


class Bam_Edit:
    def __init__(self, bam_path: str):
        self.bam_path = bam_path
        
    def __enter__(self):

        from panda3d import core
        import os

        loader: core.Loader = core.Loader.get_global_ptr()
        flags = core.LoaderOptions(core.LoaderOptions.LF_no_cache)

        bam_path = core.Filename.from_os_specific(self.bam_path)
        panda_node = loader.load_sync(bam_path, flags)

        self.root_node = core.NodePath(panda_node)

        return self.root_node
        
    def __exit__(self , type, value, traceback):

        from panda3d import core

        is_success = self.root_node.write_bam_file(core.Filename.from_os_specific(self.bam_path))
        if not is_success:
            raise BaseException(f'Error writing file: {self.bam_path}')

def fix_collisions(bam_path):
    with Bam_Edit(bam_path) as root_node:
        for node in root_node.find_all_matches("**/+CollisionNode"):
            parent = node.get_parent()
            for geom_node in parent.find_all_matches('**/+GeomNode'):
                geom_node.reparent_to(parent)

def set_transparency(bam_path):
    with Bam_Edit(bam_path) as root_node:
        root_node.set_transparency(3)


def delete_BFace():
    """ fixes physics a bug with egg importer """
    import re
    import import_scripts
    job = get_job() # type: ignore
    
    import_scripts.edit_file(job['fname'], lambda data: re.sub(r'.+<BFace>.+', '', data))


def dill_testing_func(*args, **kwargs):
    print(args)

    my_func = kwargs['my_func']
    my_func(kwargs['my_dict'])

def use_backface_culling():
    """ set use_backface_culling to `True` for all the materials """
    
    import bpy
    
    for material in bpy.data.materials:
        material.use_backface_culling = True