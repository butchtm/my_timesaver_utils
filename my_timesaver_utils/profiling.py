# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/01_profiling.ipynb (unless otherwise specified).

__all__ = ['profile_call', 'print_prof_data', 'clear_prof_data', 'get_prof_data', 'start_record', 'end_record',
           'save_prof_data', 'load_prof_data']

# Internal Cell
import time
import warnings
from functools import wraps

PROF_DATA = {}

# Cell
def profile_call(fn):
    'decorator to profile a method - stores data in PROF_DATA'
    @wraps(fn)
    def with_profiling(*args, **kwargs):
        start_time = time.time()
        ret = fn(*args, **kwargs)
        elapsed_time = time.time() - start_time

        if fn.__name__ not in PROF_DATA:
            PROF_DATA[fn.__name__] = [0, [],0]
        PROF_DATA[fn.__name__][0] += 1
        PROF_DATA[fn.__name__][1].append(elapsed_time)

        return ret

    return with_profiling

def _print_data(fname, data):
    max_time = max(data[1])
    avg_time = sum(data[1]) / len(data[1])
    print(f'Function {fname} called {data[0]} times.')
    print(f'Execution time max: {max_time:.3f}, average: {avg_time:.3f}')

def print_prof_data(fname=None):
    'print out profile data'
    if fname is not None:
        if fname not in PROF_DATA:
            warnings.warn(f'Function {fname} has no profile data')
            return
        _print_data(fname, PROF_DATA[fname])
        return

    for fname, data in PROF_DATA.items():
        _print_data(fname, data)

def clear_prof_data():
    'clear out profile data'
    global PROF_DATA
    PROF_DATA = {}

def get_prof_data(name):
    'get profile data for name'
    return None if name not in PROF_DATA else PROF_DATA[name][1]

# Cell
def start_record(name):
    'start recording time for name'
    start_time = time.time()
    if name not in PROF_DATA:
        PROF_DATA[name] = [0, [],0]
    if PROF_DATA[name][2] != 0:
        warnings.warn(f'function {name} start time not recorded because start time has already been recorded')
        return
    PROF_DATA[name][2] = start_time

def end_record(name):
    'end recording time and add elapsed time to profile data'
    if name not in PROF_DATA:
        warnings.warn(f'function {name} end time not recorded because start time not found')
        return
    start_time = PROF_DATA[name][2]
    elapsed_time = time.time() - start_time
    PROF_DATA[name][2] = 0
    PROF_DATA[name][0] += 1
    PROF_DATA[name][1].append(elapsed_time)



# Cell
import pickle
import pathlib

def save_prof_data(file_name, overwrite_file=True):
    'save profile data to `file_name`, `overwrite_file=True` overwrites existing file'
    if not isinstance(file_name, pathlib.Path):
        file_name = pathlib.Path(file_name)

    if file_name.is_dir():
        warnings.warn(f'File not saved, {filename} is an existing directory')
        return

    if not overwrite_file and file_name.is_file():
        warnings.warn(f'File not saved, {filename} already exists')
        return

    with open(file_name,'wb') as f:
        try:
            pickle.dump(PROF_DATA,f)
        except pickle.PickeError as e:
            warnings.warn(f'Error in saving {file_name}, exception triggered {e}')
    f.close()

def load_prof_data(file_name, overwrite_prof_data=True):
    'load profile data from `file_name`, `overwrite_prof_data` overwrites existing profile data'
    if not isinstance(file_name, pathlib.Path):
        file_name = pathlib.Path(file_name)
    if file_name.is_dir():
        warnings.warn(f'File {filename} is a directory, not a file')
        return

    if not file_name.is_file():
        warnings.warn(f'File {filename} does not exist')
        return

    with open(file_name, 'rb') as f:
        try:
            file_prof_data = pickle.load(f)
        except pickle.PickleError as e:
            warnings.warn(f'Unpickling {file_name} triggered an exception {e}')
            return
        for k,v in file_prof_data.items():
            if k not in PROF_DATA or overwrite_prof_data:
                PROF_DATA[k] = file_prof_data[k]