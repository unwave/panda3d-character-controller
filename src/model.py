import os
import import_scripts

# is needed for pickling from inside a module that is not available to import
# serialized module fails if module is not in PYTHONPATH · Issue #123 · uqfoundation/dill
# https://github.com/uqfoundation/dill/issues/123
__name__ = '__main__'

def conform_file_system_case_sensitivity():
    if os.path.exists(os.path.__file__.lower()) and os.path.exists(os.path.__file__.upper()):
        from panda3d import core
        core.load_prc_file_data("", "vfs-case-sensitive 0")

# when you rewrite files on windows, it does not change their names letter case
# so changing final files name letter case will raise an error
# the files are untracked, there is no reliable way to conform the letter case other than updating the converters
# or just conform the case sensitive of the panda3d's files system with the OS one
conform_file_system_case_sensitivity()

def get_path(path: str, start: str = os.path.dirname(os.path.abspath(__file__))):
    return os.path.abspath(os.path.join(start, path))

from blend_converter import Bam, Egg


ACTOR_BLEND_PATH = get_path('../doc/srcModels/actor/Fox.blend')
ACTOR_DIR = get_path('../models/actor')

fox = Egg(ACTOR_BLEND_PATH, ACTOR_DIR)
fox.settings_yabee.from_actions = True
fox.stem = 'Fox'

fox.attach_pre_script(import_scripts.set_use_nodes_for_all_materials)
fox.attach_pre_script(import_scripts.use_backface_culling)
fox.attach_post_script(import_scripts.remove_spec_rgba)


LEVEL_BLEND_PATH = get_path('../doc/srcModels/level/level.blend')
LEVEL_PATH = get_path('../models/level')

level = Bam(LEVEL_BLEND_PATH, LEVEL_PATH)
level.stem = 'level_new'

level.attach_pre_gltf_script(import_scripts.use_backface_culling)
level.attach_pre_gltf_script(import_scripts.convert_properties)
level.attach_pre_gltf_script(import_scripts.set_rigid_body)

# attach_post_bam_script uses current interpreter
level.attach_post_bam_script(import_scripts.fix_collisions, level.os_path_target)
level.attach_post_bam_script(import_scripts.set_transparency, level.os_path_target)

## dill testing: https://pypi.org/project/dill/

GLOBAL_VAR = 'I AM A GLOBAL VARIABLE'
import inspect

def do_i_need_it(something):

    # the try/except byte code seems incompatible between 3.9 and 3.10
    frame = inspect.currentframe()
    if frame:
        print(frame.f_code.co_name, 'not really')

    print(something)

    print(GLOBAL_VAR)

script = level.attach_pre_gltf_script(import_scripts.dill_testing_func, 'hello world 2', 234.888, True, k = 15, my_dict = {"a": 1, "b": 3}, my_func = do_i_need_it)
script.add_module_from_file(import_scripts.__file__)
script.use_dill = True



FLOATING_PLATFORM_PATH = get_path('../doc/srcModels/level/FloatingPlatform.blend')

floating_platform = Egg(FLOATING_PLATFORM_PATH, LEVEL_PATH)
floating_platform.settings_yabee.apply_obj_transform = True
floating_platform.settings_yabee.apply_coll_tag = True

floating_platform.attach_pre_script(import_scripts.set_use_nodes_for_all_materials) # fix a prpee bug

# fixes a physics bug
script = floating_platform.attach_post_script(import_scripts.delete_BFace)
script.add_module_from_file(import_scripts.__file__)

