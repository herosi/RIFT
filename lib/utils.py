"""Helper functions."""

import logging
import os
import random
import string
from ar import Archive
import shutil
import subprocess
import json

LOGGER_NAME = "RIFT_LOGGER"



def replace_extension(basename, new_ext):
    fname = os.path.splitext(basename)[0]
    fname = fname + new_ext
    return fname


def delete_loggers():
    logging.getLogger(LOGGER_NAME).handlers.clear()
    logging.getLogger(LOGGER_NAME).filters.clear()
     

def get_logger(filename=None, verbose=False):
    """Initialize a basic logging object."""

    level = logging.INFO
    if verbose:
        level = logging.DEBUG

    delete_loggers()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(LOGGER_NAME)

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    sh.setLevel(level)
    logger.addHandler(sh)

    if filename is not None:
        fh = logging.FileHandler(filename)
        fh.setFormatter(formatter)
        fh.setLevel(level)
        logger.addHandler(fh)

    logger.setLevel(level)
    return logger


def remove_illegal_ida_chars(name):

    illegal_ida_chars = str.maketrans({
        "<": "_",
        ">": "_",
        " ": "_",
        "*": "",
        "`": "",
        ".": "_"
    })
    return name.translate(illegal_ida_chars)

def read_json(path):
    with open(path, "r") as f:
        data = json.load(f)
    return data


def write_json(path, json_data):
    with open(path, "w+") as f:
        f.write(json.dumps(json_data))


def has_files(folder):
    """Return True if files are in the specific folder."""
    return os.path.isdir(folder) and len(os.listdir(folder)) > 0


def get_files_from_dir(folder, extension):
    """Gets file paths with a specific extension from a directory. Returns list with absolute paths."""
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(extension)]


def copy_files_by_ext(folder, extension, dst):
    files = get_files_from_dir(folder, extension)
    for file in files:
        shutil.copy(file, dst)


def gen_random_name(length):
    """Generate a random name with length characters."""
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))


def remove_line(file_path, line_number):
    """Remove the specific line from the file. Co-Pilot generated."""
    with open(file_path, 'r') as file:
        lines = file.readlines()

    if line_number < 1 or line_number > len(lines):
        raise ValueError("Line number is out of range")

    with open(file_path, 'w') as file:
        for i, line in enumerate(lines, start=1):
            if i != line_number:
                file.write(line)


def unpack_rlib(rlib_file, dest_folder):
    """Takes path to rlib file, moves it to dest_folder, renames to ar and unpacks it to the given destination."""
    
    # Check if the file has .rlib extension, copy the file to temp folder
    if not rlib_file.endswith('.rlib'):
        raise ValueError("The file must have a .rlib extension")
    tmp_path = os.path.join(dest_folder, os.path.basename(rlib_file))
    shutil.copy2(rlib_file, tmp_path)
    # extract all entries and return dest_folder
    with open(tmp_path, "rb") as f:
        archive = Archive(f)
        for entry in archive:
            fname = os.path.basename(entry.name)
            output_path = os.path.join(dest_folder, fname)
            if os.path.isdir(output_path):
                continue
            with open(output_path, "wb") as out_file:
                content = archive.open(entry, "rb").read()
                out_file.write(content)

    return dest_folder


def cleanup_folder(folder_path):
    """Deletes all files in folder."""
    # Check if the folder exists
    if not os.path.exists(folder_path):
        raise ValueError("The specified folder does not exist")
    
    # Iterate over all files in the folder
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        # Check if it is a file and delete it
        if os.path.isfile(file_path):
            os.remove(file_path)


def order_by_libname(file_paths):
    """Orders a list of files by its specific libname."""
    lib_dict = {}
    
    for path in file_paths:
        # Split the file name by "." and take the first value
        lib_name = os.path.basename(path).split(".")[0]
        
        # Add the file path to the dictionary under the corresponding lib_name
        if lib_name not in lib_dict:
            lib_dict[lib_name] = []
        lib_dict[lib_name].append(path)
    
    return lib_dict


def exec_cmd(cmd, capture_output=False, check=True):
    """
    Execute a specific command and capture the output if necessary.
    Returns a triple with returncode, stdout and stderr.
    """
    if not capture_output:
        result = subprocess.run(cmd, check=check)
        return (result.returncode, None, None)
    else:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return (result.returncode, result.stdout, result.stderr)


def downgrade_version(version):
    """Downgrade a specific version. Co-Pilot generated function."""
    # Split the version string into parts
    parts = list(map(int, version.split('.')))
    
    # Handle different lengths of version parts
    if len(parts) == 3:
        major, minor, patch = parts
    elif len(parts) == 2:
        major, minor = parts
        patch = 0
    elif len(parts) == 1:
        major = parts
        minor = 0
        patch = 0
    else:
        raise ValueError("Invalid version format")

    # Decrement the version
    if patch > 0:
        patch -= 1
    else:
        if minor > 0:
            minor -= 1
            patch = 99
        else:
            if major > 0:
                major -= 1
                minor = 99
                patch = 99
            else:
                return version

    # Return the downgraded version string
    return f"{major}.{minor}.{patch}".rstrip('.0').rstrip('.0')