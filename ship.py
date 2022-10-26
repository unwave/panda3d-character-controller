""" creates a zip file with the project with files filtered with filter_func """

import os
import shutil
import tempfile
import typing

DIR = os.path.dirname(__file__)

def filter_func(entry: os.DirEntry):

    if entry.is_dir():

        if entry.name in {'.github', '.git', '__pycache__', 'local'}:
            return False

        if os.path.samefile(entry.path, os.path.join(DIR, 'models')):
            return False
            
    elif entry.is_file():

        if entry.name in {'.gitignore', 'setup.py', 'LICENSE', 'demo.log'}:
            return False

        if '.blend' in entry.name and not str(entry.name).endswith('.blend'):
            return False
            
    else:
        raise BaseException('Is this possible?')

    return True


def get_files(path, filter_func: typing.Callable[[os.DirEntry], bool], recursively = True) -> typing.List[os.DirEntry]:
    list = []

    for item in os.scandir(path):

        if not filter_func(item):
            continue
        
        list.append(item)

        if recursively and item.is_dir():
            list.extend(get_files(item.path, filter_func, recursively))

    return list

def copy_dir_content(dir_path: str, target_dir: str, filter_func: typing.Callable[[os.DirEntry], bool]):

    dir_path = os.path.abspath(dir_path)
    target_dir = os.path.abspath(target_dir)

    def get_new_path(path):
        path = os.path.abspath(path)
        return os.path.join(target_dir, os.path.relpath(path, start = dir_path))
    
    content = get_files(dir_path, filter_func, recursively = True)
    
    dirs = [] # type: typing.List[os.DirEntry]
    files = [] # type: typing.List[os.DirEntry]
    for file in content:
        if file.is_dir():
            dirs.append(file)
        else:
            files.append(file)
  
    new_dirs = [] # type: typing.List[str]
    for dir in dirs:
        new_dir = get_new_path(dir)
        new_dirs.append(new_dir)
        os.makedirs(new_dir, exist_ok = True)
        
    new_files = [] # type: typing.List[str]
    for file in files:
        new_path = get_new_path(file)
        new_dirs.append(new_path)
        shutil.copy2(file, new_path)

    return new_files, new_dirs

base_dir_name = 'panda3d-character-controller'
local_dir = os.path.join(DIR, 'local')


with tempfile.TemporaryDirectory() as temp_dir:

    shipped_dir = os.path.join(temp_dir, base_dir_name)
    copy_dir_content(DIR, shipped_dir, filter_func)
    
    os.chdir(local_dir)
    shutil.make_archive('panda3d-character-controller', 'zip', root_dir = temp_dir, base_dir = base_dir_name)

    os.startfile(shipped_dir)
    os.startfile(local_dir)

    input('press enter to exit, will delete the temp files')
