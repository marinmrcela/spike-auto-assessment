# Functions used by the main programs.

from math import sqrt
import zipfile
import json
import io
import yaml
import tkinter
from tkinter.filedialog import askdirectory


def get_project(llsp_file):
    # Extracts blocks, broadcasts, lists and variables from the project json file.
    # Blocks are filtered for the observed attributes.

    with zipfile.ZipFile(llsp_file, 'r') as zfile_outer:
        scratch = io.BytesIO(zfile_outer.read("scratch.sb3"))
        zfile_inner = zipfile.ZipFile(scratch, 'r')
        project_json = zfile_inner.read("project.json")

    project = json.loads(project_json.decode("utf-8"))

    blocks = project["targets"][0]["blocks"]
    blocks.update(project["targets"][1]["blocks"])
    blocks_filtered = filter_attributes(blocks)

    variables = project["targets"][0]["variables"]
    variables.update(project["targets"][1]["variables"])

    lists = project["targets"][0]["lists"]
    lists.update(project["targets"][1]["lists"])

    broadcasts = project["targets"][0]["broadcasts"]
    broadcasts.update(project["targets"][1]["broadcasts"])

    project_trimmed = dict()
    project_trimmed["blocks"] = blocks_filtered
    project_trimmed["broadcasts"] = broadcasts
    project_trimmed["lists"] = lists
    project_trimmed["variables"] = variables

    return project_trimmed


def filter_attributes(blocks):
    # Extracts the observed attributes of a block.

    filtered_blocks = dict()
    all_keys = set(blocks.keys())
    for block, block_atts in blocks.items():
        filtered_block_atts = dict()

        opcode = block_atts.get('opcode', None)
        _next = block_atts.get('next', None)
        toplevel = block_atts.get('topLevel', None)

        filtered_block_atts['opcode'] = opcode
        if _next:
            filtered_block_atts['next'] = _next
        if toplevel:
            filtered_block_atts['topLevel'] = toplevel
            # Initial block's coordinates are -130,120
            x = block_atts['x'] + 130.0
            y = block_atts['y'] - 120.0
            distance = sqrt(x**2 + y**2)
            filtered_block_atts['distance'] = distance

        block_parts = list()
        inputs = list()
        condition = ""
        substack = ""
        substack2 = ""

        for input_key, input_value in block_atts['inputs'].items():
            if input_key == "CONDITION":
                in_val = input_value[1]
                if in_val:  # Not none
                    condition = in_val
                    # Conditions are treated as parts in visualization,
                    # but they are counted as primary blocks in classification.
                    block_parts.append(condition)
            elif input_key == "SUBSTACK":
                substack = input_value[1]
            elif input_key == "SUBSTACK2":
                substack2 = input_value[1]
            else:
                flat_list = list(flatten_list_fast(input_value))
                for element in flat_list:
                    if len(element) == 20 and element in all_keys:
                        block_parts.append(element)
                    else:
                        inputs.append(element)

        if block_parts:
            filtered_block_atts["parts"] = block_parts
        if inputs:
            filtered_block_atts["inputs"] = inputs
        if condition:
            filtered_block_atts["condition"] = condition
        if substack:
            filtered_block_atts["substack"] = substack
        if substack2:
            filtered_block_atts["substack2"] = substack2

        fields = list(block_atts['fields'].values())
        fields_flat_list = list(flatten_list_fast(fields))
        if fields_flat_list:
            filtered_block_atts["fields"] = fields_flat_list

        filtered_blocks[block] = filtered_block_atts

    return filtered_blocks


def flatten_list_fast(lst):
    # Flattens nested lists keeping only strings.
    # Input lists are be deeper than two levels of nesting,
    # therefore chain.from_iterable() will not work.

    for i in lst:
        if isinstance(i, list):
            for x in flatten_list_fast(i):
                yield x
        else:
            if i and isinstance(i, str):
                yield i


def directory_dialog(title='Choose the directory:'):
    root = tkinter.Tk()
    root.withdraw()
    root.call('wm', 'attributes', '.', '-topmost', True)
    directory = askdirectory(parent=root, title=title)
    return directory


def get_paths(paths_file):
    # Returns paths from a yaml file as a dictionary.

    with open(paths_file, 'r') as file:
        params = yaml.safe_load(file)

    params = {k.lower(): v for k, v in params.items()}  # Case-insensitive

    return params


def get_params(params_path):
    # Returns parameters from a yaml file.

    with open(params_path, 'r') as file:
        params = yaml.safe_load(file)

    params = {k.lower(): v for k, v in params.items()}  # Case-insensitive

    # Defaults
    cleanUp = False
    onlyKeep = None
    flexible = None

    if "cleanup" in params.keys():
        if params['cleanup']:
            cleanUp = True

    if "onlykeep" in params.keys():
        if params['onlykeep']:
            onlyKeep = params['onlykeep']

    if "flexible" in params.keys():
        if params['flexible']:
            flexible = params['flexible']

    return cleanUp, onlyKeep, flexible
