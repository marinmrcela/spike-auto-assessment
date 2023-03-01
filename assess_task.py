import concurrent.futures
import csv
import glob
import json
import os.path
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from tkinter.filedialog import asksaveasfile

import Levenshtein
import pandas as pd
from anytree import RenderTree, Node
from tqdm import tqdm

from cf import get_params, get_paths, get_project


def block_classifier(blocks, block_parts):
    # Sorts blocks into categories.

    keyword = {"Motors": 0,
               "Movement": 0,
               "Light": 0,
               "Sound": 0,
               "Events": 0,
               "Control": 0,
               "Sensors": 0,
               "Operators": 0,
               "Variables": 0,
               "My Blocks": 0}

    inv_keyword = {"motor": "Motors",
                   "move": "Movement",
                   "display": "Light",
                   "light": "Light",
                   "sound": "Sound",
                   "event": "Events",
                   "control": "Control",
                   "sensors": "Sensors",
                   "operator": "Operators",
                   "data": "Variables",
                   "procedures": "My Blocks"}

    primary_keys = set(blocks.keys())
    secondary_keys = set()

    for sublist in block_parts.values():
        for item in sublist:
            secondary_keys.add(item)

    primary_keys -= secondary_keys

    for primary_key in primary_keys:
        opcode = blocks[primary_key]["opcode"]
        opcode_start = opcode.split("_")[0]

        check = True
        for keyw in inv_keyword.keys():
            if keyw in opcode_start:
                keyword[inv_keyword[keyw]] += 1
                check = False
                break
        if check:
            raise Exception(f"Error categorizing block {opcode_start} ({opcode}).")

        condition = blocks[primary_key].get("condition", None)
        if condition:
            condition_opcode = blocks[condition]["opcode"]
            condition_opcode_start = condition_opcode.split("_")[0]

            check = True
            for keyw in inv_keyword.keys():
                if keyw in condition_opcode_start:
                    keyword[inv_keyword[keyw]] += 1
                    check = False
                    break
            if check:
                raise Exception(f"Error categorizing block {condition_opcode_start} ({condition_opcode}).")

    return keyword


def tree_builder_fast(blocks, cleanup=False, onlykeep=None):
    # Builds a tree equivalent of the graphical solution.

    # Set of all block keys (unique).
    all_keys = set(blocks.keys())
    # Keys that are kept if onlykeys is used.
    onlykeep_keys = set(all_keys)
    # Keys of the primary blocks
    primary_keys = set(all_keys)
    # Key: value
    # primary block: list of its parts.
    block_parts = dict()

    # Roots are the first blocks in stacks.
    # Key: value
    # root block key: distance from the centre of the coordinate system.
    roots = dict()
    # Key: value
    # block key: block key of the next block.
    nexts = dict()
    # Key: value
    # block key: block key of the first block in its substack.
    substacks = dict()
    # substacks 2 is used for the "else" part of the "if-else" statement.
    # Key: value
    # block key: block key of the first block in the second (e.g. else) substack.
    substacks2 = dict()

    if onlykeep:
        onlykeep_keys = set()
        for key in all_keys:
            if blocks[key]["opcode"] in onlykeep:
                onlykeep_keys.add(key)
        primary_keys = set(onlykeep_keys)

    for key in onlykeep_keys:
        parts = blocks[key].get("parts", list())
        # Remove parts that are no longer kept (onlykeep).
        parts = [element for element in parts if element in onlykeep_keys]
        if parts:
            block_parts[key] = parts
            parts_set = set(parts)
            primary_keys -= parts_set

    for primary_key in primary_keys:
        block = blocks[primary_key]
        toplevel = block.get("topLevel", None)
        nextb = block.get("next", None)
        substack = block.get("substack", None)
        substack2 = block.get("substack2", None)

        if toplevel:
            if cleanup:
                if "event" in blocks[primary_key]["opcode"]:
                    roots[primary_key] = blocks[primary_key]["distance"]
            else:
                roots[primary_key] = blocks[primary_key]["distance"]
        if nextb:
            nexts[primary_key] = nextb
        if substack:
            substacks[primary_key] = substack  # Key is at the second place
        if substack2:
            substacks2[primary_key] = substack2

    # List of sorted roots.
    # Roots are sorted based on their distance from the centre of the coordinate system,
    # which is in this project defined as the location of the initial block.
    if len(roots) > 1:
        sorted_roots = sorted(roots, key=lambda x: roots[x])
    else:
        sorted_roots = list(roots.keys())

    # Create tree

    tree = dict()
    tree['root'] = Node('root')
    for primary_key in primary_keys:
        tree[primary_key] = Node(primary_key)
    tree['root'].children = tuple(tree[root] for root in sorted_roots)

    for key, value in substacks.items():
        # Value can be none in case of an empty substack
        if value:
            s_children = list()
            if value in onlykeep_keys:
                s_children.append(tree[value])
            nxt = blocks[value].get("next", None)
            while nxt:
                if nxt in onlykeep_keys:
                    s_children.append(tree[nxt])
                nxt = blocks[nxt].get("next", None)
            tree[key].children = tuple(s_children)

    for key, value in substacks2.items():
        if value:
            s_children = list(tree[key].children)
            if value in onlykeep_keys:
                s_children.append(tree[value])
            nxt = blocks[value].get("next", None)
            while nxt:
                if nxt in onlykeep_keys:
                    s_children.append(tree[nxt])
                nxt = blocks[nxt].get("next", None)
            tree[key].children = tuple(s_children)

    for root in sorted_roots:
        r_children = list()
        nxt = blocks[root].get("next", None)
        while nxt:
            if nxt in onlykeep_keys:
                r_children.append(tree[nxt])
            nxt = blocks[nxt].get("next", None)
        tree[root].children = tuple(r_children)

    return tree, block_parts


def tree_visualizer(blocks, block_parts, tree, flexible):
    # Converts tree to plain text.

    tree_str = "\n"
    log_sup = block_params(blocks, flexible)
    for pre, fill, node in RenderTree(tree['root']):
        if node.name == "root":
            tree_str += f"{pre}root\n"
        else:
            tree_str += f"{pre}{blocks[node.name]['opcode']}{log_sup[node.name]}"
            # If the node (block) has parts:
            if node.name in block_parts:
                for part in block_parts[node.name]:
                    tree_str += f" | {blocks[part]['opcode']}{log_sup[part]}"
                    # If the part has parts (subparts):
                    if part in block_parts:
                        for subpart in block_parts[part]:
                            tree_str += f" | {blocks[subpart]['opcode']}{log_sup[subpart]}"
            tree_str += "\n"

    return tree_str


def block_params(blocks, flexible):
    # Filters block parameters by removing unused_attributes,
    # block keys and all non-string values.
    # Returns a dictionary in which for each block as a key
    # the value is a list of its parameters.

    out = dict()

    for block in blocks:
        if flexible and blocks[block]['opcode'] in flexible:
            ls = ["FLEXIBLE"]
        else:

            inputs = blocks[block].get('inputs', list())
            fields = blocks[block].get('fields', list())

            ls = inputs + fields

            # Sorting ports alphabetically
            if ls and 'port-selector' in blocks[block]['opcode']:
                ls[0] = ''.join(sorted(ls[0]))

        out[block] = ls

    return out


def get_distinct_blocks(blocks):
    opcodes = list()
    for val in blocks.values():
        opcodes.append(val["opcode"])
    return set(opcodes)


class TreeBuilder:
    # Loads parsed project json files and creates textual trees.
    # Results are saved as json files named after the loaded files.
    def __init__(self, _path, _out_folder_name, _path_params=None):
        self.path_params = _path_params
        self.out_folder_name = _out_folder_name
        self.path = _path
        self.input_files = glob.glob(f'{self.path}/*.json')
        self.out_folder = os.path.normpath(self.out_folder_name)
        if not os.path.isdir(self.out_folder):
            os.makedirs(self.out_folder)
        self.cleanup = False
        self.onlykeep = None
        self.flexible = None
        self.get_parameters()

    def get_parameters(self):
        if os.path.isfile(self.path_params):
            try:
                self.cleanup, self.onlykeep, self.flexible = get_params(self.path_params)
            except ImportError as e:
                print(f"Import error:\n{e}")
                raise
            except Exception as e:
                print(f"Error reading parameters:\n{e}\n")

    def create_tree_from_file(self, input_file, out_file, folder_files):

        folder_files[out_file] = dict()

        with open(input_file, 'r', encoding='utf-8') as f:
            student_files = json.load(f)

        for student_file_name, student_file_content in student_files.items():
            blocks = student_file_content["blocks"]
            tree, block_parts = tree_builder_fast(blocks, self.cleanup, self.onlykeep)
            tree_str = tree_visualizer(blocks, block_parts, tree, self.flexible)
            folder_files[out_file][student_file_name] = tree_str

    def create_trees(self):
        folder_files = dict()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.create_tree_from_file, input_file,
                                       f"{self.out_folder}/{os.path.basename(input_file)}", folder_files)
                       for input_file in self.input_files]
            for _ in tqdm(concurrent.futures.as_completed(futures), total=len(futures),
                          bar_format='Creating trees:  {l_bar}{bar}|  {n_fmt}/{total_fmt}'):
                pass

        self.save_output(folder_files)
        print(f"\nTrees path: {self.out_folder}")

    def save_output(self, folder_files):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self._save_output_file, out_file, folder_files[out_file])
                       for out_file in folder_files]
            for _ in tqdm(concurrent.futures.as_completed(futures), total=len(futures),
                          bar_format='Saving results:  {l_bar}{bar}|  {n_fmt}/{total_fmt}'):
                pass

    @staticmethod
    def _save_output_file(out_file, output_data):
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, sort_keys=True)


class TextMatching:
    # Evaluates each snapshots based on the Levenshtein distance from the ground truth examples.
    # Each student's nearest snapshot is saved in the "distances" table.
    def __init__(self, _path_gt, _path_pr, _out_folder, _out_file):
        self.path_gt = _path_gt
        self.path_pr = _path_pr
        self.out_folder = os.path.normpath(_out_folder)
        self.out_file = os.path.normpath(_out_file)
        self.files_gt = None
        self.students = dict()
        self.results = dict()

    def create_output_folder(self):
        if not os.path.isdir(self.out_folder):
            os.makedirs(self.out_folder)

    def load_ground_truth(self):
        if not os.path.exists(self.path_gt):
            raise Exception("Ground truth path error")
        with open(self.path_gt, 'r', encoding='utf-8') as f:
            self.files_gt = json.load(f)

    def load_project_files(self):
        if not os.path.exists(self.path_pr):
            raise Exception("Project path error")
        for student_file in glob.glob(self.path_pr + r"/*.json"):
            with open(student_file, 'r', encoding='utf-8') as f:
                self.students[student_file] = json.load(f)

    def compare_texts(self):
        for student_file in self.students:
            student = os.path.basename(student_file).split(".")[0].split(" ")[-1]
            self.results[student] = [0, 0, "", ""]
        for student_file in tqdm(self.students.keys(), total=len(self.students),
                                 bar_format='Finding distance:  {l_bar}{bar}|  {n_fmt}/{total_fmt}'):
            student = os.path.basename(student_file).split(".")[0].split(" ")[-1]
            for file_pr, text_pr in self.students[student_file].items():
                for file_gt_name, file_gt_text in self.files_gt.items():
                    lr = Levenshtein.ratio(file_gt_text, text_pr)
                    if lr > self.results[student][0]:
                        ld = Levenshtein.distance(file_gt_text, text_pr)
                        file_pr_short = os.path.basename(file_pr)
                        self.results[student] = [lr, ld, file_gt_name, file_pr_short]
                    if lr == 1:
                        break

    def save_to_csv(self):
        header = ["Student", "Ratio", "Distance", "GT File", "Student File"]
        f = open(self.out_file, 'w', newline='')
        writer = csv.writer(f)
        writer.writerow(header)
        for student_file in self.students:
            student = os.path.basename(student_file).split(".")[0].split(" ")[-1]
            row = [student]
            for el in self.results[student]:
                if isinstance(el, float):
                    el = round(el, 4)
                row.append(el)
            writer.writerow(row)
        f.close()

    def print_exact_matches(self):
        matches = 0
        for value in self.results.values():
            if value[0] == 1:
                matches += 1
        print(f"\nFound {matches} exact matches.\n{self.out_file}")

    def run(self):
        self.create_output_folder()
        self.load_ground_truth()
        self.load_project_files()
        self.compare_texts()
        self.save_to_csv()
        self.print_exact_matches()


class DataMiner:
    # Extracts features of the project by each student
    # and saves them in the "info" table.
    def __init__(self, _path_projects, _input_csv, _output_folder,
                 _output_csv, _max_distance, _last_file_only, _header):
        self.path_projects = _path_projects
        self.input_csv = os.path.normpath(_input_csv)
        self.out_folder = os.path.normpath(_output_folder)
        if not os.path.isdir(self.out_folder):
            os.makedirs(self.out_folder)
        self.output_csv = os.path.normpath(_output_csv)
        self.max_distance = _max_distance
        self.last_file_only = _last_file_only
        self.header = _header
        if self.input_csv:
            if self.last_file_only:
                self.last_file_text = "Only classifying blocks from the solution"
            else:
                self.last_file_text = "Classifying all blocks from start to solution"
        else:
            if self.last_file_only:
                self.last_file_text = "Only classifying blocks from the last step"
            else:
                self.last_file_text = "Classifying all blocks from start to end"

    @staticmethod
    def get_count_fast(file):
        len_blocks = len(file["blocks"])
        return len_blocks

    @staticmethod
    def get_last_block_data(file):
        blocks = file["blocks"]
        tree, block_parts = tree_builder_fast(blocks)
        categorized_blocks = block_classifier(blocks, block_parts)
        count_blocks = sum(categorized_blocks.values())
        count_programming_stacks = len(tree['root'].children)
        categorized_blocks["All Blocks"] = count_blocks
        categorized_blocks["Stacks"] = count_programming_stacks
        return categorized_blocks

    def get_vector(self, gv_path_pr, gv_student, gv_last_file):
        removals = 0
        additions = 0
        adjustments = 0

        student_json = os.path.normpath(f"{gv_path_pr}/Lego Spike {gv_student}.json")
        if not os.path.exists(student_json):
            raise Exception("Path does not exist")
        with open(student_json, 'r', encoding='utf-8') as _f:
            student_project = json.load(_f)

        file_names_all = list(student_project.keys())
        last_file_index = file_names_all.index(gv_last_file)
        file_names = file_names_all[0:last_file_index + 1]
        if file_names[-1] != gv_last_file:
            raise Exception("Last file mismatch")

        time_ff = float(file_names[0].split(" ")[0]) / (10 ** 8)
        time_lf = float(file_names[-1].split(" ")[0]) / (10 ** 8)
        time_secs = round(time_lf - time_ff)

        for file_name in file_names[0:-1]:
            file_A = student_project[file_name]
            next_file_name = file_names[file_names.index(file_name) + 1]
            file_B = student_project[next_file_name]
            count_A = self.get_count_fast(file_A)
            count_B = self.get_count_fast(file_B)

            if count_A > count_B:
                removals += 1
            elif count_A < count_B:
                additions += 1
            else:
                adjustments += 1

        if self.last_file_only:
            last_file = student_project[file_names[-1]]
            last_block_data = self.get_last_block_data(last_file)
        else:
            last_block_data = self.get_last_block_data(student_project[file_names[0]])
            for i in range(1, len(file_names)):
                block_data = self.get_last_block_data(student_project[file_names[i]])
                for key in last_block_data:
                    last_block_data[key] += block_data[key]

        last_block_data["Steps"] = last_file_index + 1
        last_block_data["Seconds"] = time_secs
        last_block_data["Additions"] = additions
        last_block_data["Removals"] = removals
        last_block_data["Adjustments"] = adjustments

        return last_block_data

    def run(self):

        # If input_csv is not None
        if self.input_csv:
            print(f"Using:\n{self.input_csv}\t as input table,\n{self.max_distance}\t as maximum distance,"
                  f"\n{self.last_file_text}\n")
            df = pd.read_csv(self.input_csv)
            corr = df.loc[df['Distance'] <= self.max_distance]

        # Else create a table for all students with all files
        else:
            print(f"Using all steps from all students\n{self.last_file_text}\n")
            temp_table = [["Student", "Student File", "GT File"]]
            all_st = glob.glob(self.path_projects + r"/*.json")
            for json_file in tqdm(all_st, total=len(all_st),
                                  bar_format='Creating a temporary table:  {l_bar}{bar}|  {n_fmt}/{total_fmt}'):
                with open(json_file, 'r', encoding='utf-8') as f:
                    lf = sorted(list(json.load(f).keys()))[-1]
                st_id = os.path.basename(json_file).split(".")[0].split(" ")[-1]
                # Student id, last file, GT File replacement
                temp_table.append([st_id, lf, "All Files"])
            # Set the first row as the header
            corr = pd.DataFrame(temp_table[1:], columns=temp_table[0])

        print(f"There are {len(corr.index)} matches.\n")
        results = list()

        for ind in tqdm(corr.index, total=len(corr.index),
                        bar_format='Getting project data:        {l_bar}{bar}|  {n_fmt}/{total_fmt}'):
            student_id = corr['Student'][ind]
            student_file = corr['Student File'][ind]
            gt_file = corr['GT File'][ind]
            vector = self.get_vector(self.path_projects, student_id, student_file)
            vector["Student"] = student_id
            vector["Student File"] = student_file
            vector["GT File"] = gt_file
            results.append([vector[key] for key in self.header])

        with open(self.output_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.header)
            writer.writerows(results)

        print(f"\nResults: {self.output_csv}")


class VerticalScrolledFrame(ttk.Frame):
    # Default frames are not scrollable
    def __init__(self, parent, *args, **kw):
        ttk.Frame.__init__(self, parent, *args, **kw)

        # Create a canvas object and a vertical scrollbar for scrolling it
        vscrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL)
        vscrollbar.pack(fill=tk.Y, side=tk.RIGHT, expand=tk.FALSE)
        canvas = tk.Canvas(self, bd=0, highlightthickness=0,
                           yscrollcommand=vscrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=tk.TRUE)
        vscrollbar.config(command=canvas.yview)

        # Reset the view
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

        # Create a frame inside the canvas which will be scrolled with it
        self.interior = interior = ttk.Frame(canvas)
        interior_id = canvas.create_window(0, 0, window=interior,
                                           anchor=tk.NW)

        # Track changes to the canvas and frame width and sync them,
        # also updating the scrollbar
        def _configure_interior(event):
            # Update the scrollbars to match the size of the inner frame
            size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
            # noinspection PyTypeChecker
            canvas.config(scrollregion="0 0 %s %s" % size)
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # Update the canvas's width to fit the inner frame
                canvas.config(width=interior.winfo_reqwidth())
        interior.bind('<Configure>', _configure_interior)

        def _configure_canvas(event):
            if interior.winfo_reqwidth() != canvas.winfo_width():
                # Update the inner frame's width to fill the canvas
                canvas.itemconfigure(interior_id, width=canvas.winfo_width())
        canvas.bind('<Configure>', _configure_canvas)


class GTParser:
    # GUI
    def __init__(self, _root, _paths):
        self.entry = None
        self.gt_file = ""
        self.params_file = ""
        self.cleanup = tk.BooleanVar()
        self.cleanup.set(True)
        self.onlykeep = tk.BooleanVar()
        self.onlykeep.set(True)
        self.checkbox_all_st = tk.BooleanVar()
        self.checkbox_last_only = tk.BooleanVar()
        self.block_parts = dict()
        self.tree = dict()
        self.project = dict()
        self.flexible = list()
        self.llsp_files = list()
        self.flexible_values = dict()
        self.distinct_opcodes = set()
        self.max_width = 154  # Fits 1366x768
        self.max_height = 42
        self.trees_dict = dict()
        self.root = _root
        self.root.title("Ground Truth Parser")
        # self.root.resizable(False, False)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.paths = _paths

        # Button for choosing folder
        self.choose_folder_button = tk.Button(self.root, text="Choose Folder", command=self.choose_folder)
        self.choose_folder_button.grid(row=0, column=1, sticky="we")

        # Checkbox frame
        self.checkbox_frame = VerticalScrolledFrame(self.root)
        self.checkbox_frame.grid(row=1, column=0, sticky="ns")

        # Scrollbars
        self.h_scrollbar = tk.Scrollbar(self.root, orient="horizontal")
        self.h_scrollbar.grid(row=2, column=1, sticky="we")
        self.v_scrollbar = tk.Scrollbar(self.root, orient="vertical")
        self.v_scrollbar.grid(row=1, column=2, sticky="ns")

        # Text window
        self.text_window = tk.Text(self.root, wrap="none",
                                   xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)
        self.text_window.grid(row=1, column=1, sticky="nsew")
        self.text_window.config(height=self.max_height)
        self.text_window.config(font=("Consolas", 9))

        self.h_scrollbar.config(command=self.text_window.xview)
        self.v_scrollbar.config(command=self.text_window.yview)

        # Button for saving to file
        self.save_button = tk.Button(self.root, text="Save", command=self.save_to_file)
        self.save_button.grid(row=2, column=0, sticky="we")
        self.save_button["state"] = "disabled"

        # Spacer
        tk.Label(self.root, text="").grid(row=3, column=0, sticky="we")

    def save_to_file(self):

        if self.onlykeep.get():
            onlykeep_txt = ""
            for opcode in self.distinct_opcodes:
                onlykeep_txt += f"\n  - {opcode}"
        else:
            onlykeep_txt = "null"

        flexible_txt = ""
        for key, value in self.flexible_values.items():
            if value.get():
                flexible_txt += f"\n  - {key}"
        if not flexible_txt:
            flexible_txt = "null"

        out_str = f"cleanUp: {str(self.cleanup.get())}\nonlyKeep: {onlykeep_txt}\nflexible: {flexible_txt}"
        print(out_str)

        file_format = [("YAML files", "*.yml")]
        files_name = ""

        parameters_dir = os.path.expanduser(self.paths["parametersdir"])
        if not os.path.isdir(parameters_dir):
            os.makedirs(parameters_dir)

        out_file = asksaveasfile(title="Save file as...", filetypes=file_format, defaultextension=".yml",
                                 initialdir=parameters_dir)
        if out_file:
            files_name = out_file.name.split(".yml")[0]

        if files_name:
            self.params_file = f"{files_name}.yml"
            self.gt_file = f"{files_name}.json"
            with open(self.params_file, "w", encoding="utf-8") as f:
                f.write(out_str)
            with open(self.gt_file, "w", encoding="utf-8") as f:
                json.dump(self.trees_dict, f, indent=2)

            self.secondary_window()

    def secondary_window(self):
        # Open a new window to show success message
        self.root.withdraw()
        secondary_window = tk.Toplevel(self.root)
        secondary_window.title("Get data")

        tk.Label(secondary_window, text="").pack()

        checkbox1 = tk.Checkbutton(secondary_window, text="Use data from all students",
                                   variable=self.checkbox_all_st)
        checkbox1.pack(anchor="w")
        checkbox2 = tk.Checkbutton(secondary_window, text="Categorize last data point only",
                                   variable=self.checkbox_last_only)
        checkbox2.pack(anchor="w")
        tk.Label(secondary_window, text="Maximum distance:").pack()
        self.entry = tk.Entry(secondary_window)
        self.entry.pack()
        tk.Label(secondary_window, text="").pack()
        close_button = tk.Button(secondary_window, text="Get data", command=self.get_data)
        close_button.pack()
        tk.Label(secondary_window, text="").pack()
        secondary_window.protocol("WM_DELETE_WINDOW", lambda: self.root.deiconify())

    def get_data(self):
        all_st = self.checkbox_all_st.get()
        last_file_only = self.checkbox_last_only.get()
        max_distance = 0

        try:
            max_distance = int(self.entry.get())
        except ValueError:
            # Remains 0
            pass

        self.root.destroy()

        print("\nCreating trees...")
        tree_params = self.params_file
        if tree_params:
            tree_params_name = os.path.basename(tree_params).split(".yml")[0]
        else:
            tree_params_name = "Default"
        projects_path = os.path.expanduser(self.paths["projectsdir"])
        out_folder_name = os.path.expanduser(f"{self.paths['treesdir']}/{tree_params_name}")
        builder = TreeBuilder(projects_path, out_folder_name, tree_params)
        builder.create_trees()

        print("\nFinding distances...")
        gt_json = self.gt_file
        if gt_json:
            gt_name = os.path.basename(gt_json).split(".")[0]
        else:
            gt_name = "Default"
        path_trees = os.path.expanduser(f"{self.paths['treesdir']}/{gt_name}")
        out_folder = os.path.expanduser(self.paths['distancesdir'])
        dist_out_file = os.path.expanduser(f"{self.paths['distancesdir']}/Distances {gt_name}.csv")
        text_matching = TextMatching(gt_json, path_trees, out_folder, dist_out_file)
        text_matching.run()

        print("\nGetting data...")

        projects_path = os.path.expanduser(self.paths["projectsdir"])

        input_csv = dist_out_file
        table_name = os.path.basename(input_csv).split(".csv")[0].replace("Distances ", "")

        if all_st:
            input_csv = None
            table_name = "All"

        output_folder = os.path.expanduser(self.paths['infodir'])
        output_csv = os.path.expanduser(f"{self.paths['infodir']}/Info {table_name}.csv")

        # Order of columns may be edited
        # and columns may be omitted,
        # but column names are tied to the data
        header = ("Student", "GT File", "Student File", "Steps", "Additions",
                  "Adjustments", "Removals", "Control", "Events",
                  "Light", "Motors", "Movement", "My Blocks",
                  "Operators", "Sensors", "Sound", "Variables",
                  "All Blocks", "Stacks", "Seconds")

        checker = DataMiner(projects_path, input_csv, output_folder, output_csv, max_distance, last_file_only, header)
        checker.run()

    def text_window_refresh(self):
        self.text_window.delete("1.0", tk.END)
        self.text_window.config(width=self.max_width)
        for key, value in self.trees_dict.items():
            self.text_window.insert(tk.INSERT, f"\n{key}{value}")

    def checkbox_tick(self, *args):
        self.flexible = list()
        for key, value in self.flexible_values.items():
            if value.get():
                self.flexible.append(key)
        self.refresh_trees()
        self.text_window_refresh()

    def refresh_trees(self):
        for file in self.llsp_files:
            self.project = get_project(file)
            file_short = os.path.basename(file)
            # self.project["blocks"] = filter_attributes(self.project["blocks"])
            self.tree, self.block_parts = tree_builder_fast(self.project["blocks"])
            tree_str = tree_visualizer(self.project["blocks"], self.block_parts,
                                       self.tree, flexible=self.flexible)

            self.trees_dict[file_short] = tree_str

    def initialize_trees(self):
        self.trees_dict = dict()
        self.distinct_opcodes = set()
        for file in self.llsp_files:
            self.project = get_project(file)
            # self.project["blocks"] = filter_attributes(self.project["blocks"])
            file_short = os.path.basename(file)
            self.distinct_opcodes = set(list(get_distinct_blocks(self.project["blocks"])) + list(self.distinct_opcodes))
            self.tree, self.block_parts = tree_builder_fast(self.project["blocks"])
            tree_str = tree_visualizer(self.project["blocks"], self.block_parts,
                                       self.tree, flexible=self.flexible)

            self.trees_dict[file_short] = tree_str

        self.distinct_opcodes = sorted(list(self.distinct_opcodes))

        # Checkboxes for self.distinct_opcodes
        cleanup_cb = tk.Checkbutton(self.checkbox_frame.interior, text="Clean up", variable=self.cleanup)
        cleanup_cb.grid(row=0, column=0, sticky="w")
        onlykeep_cb = tk.Checkbutton(self.checkbox_frame.interior, text="Only keep present blocks ",
                                     variable=self.onlykeep)
        onlykeep_cb.grid(row=1, column=0, sticky="w")
        # Spacer
        tk.Label(self.checkbox_frame.interior, text="").grid(row=2, column=0, sticky="w")
        tk.Label(self.checkbox_frame.interior, text="Flexible:").grid(row=3, column=0, sticky="we")
        self.flexible_values = {}
        label_text = ""
        i = 4
        for opcode in self.distinct_opcodes:
            self.flexible_values[opcode] = tk.BooleanVar()
            self.flexible_values[opcode].trace("w", self.checkbox_tick)
            opcode_start = opcode.split("_")[0]
            opcode_end = opcode[len(opcode_start) + 1:] + " "
            if opcode_start != label_text:
                label_text = opcode_start
                # Spacer
                tk.Label(self.checkbox_frame.interior, text="").grid(row=i, column=0, sticky="w")
                i += 1
                label = tk.Label(self.checkbox_frame.interior, text=label_text)
                label.grid(row=i, column=0, sticky="w")
                i += 1
            checkbox = tk.Checkbutton(self.checkbox_frame.interior, text=opcode_end,
                                      variable=self.flexible_values[opcode])
            checkbox.grid(row=i, column=0, sticky="w")
            i += 1
        # Spacer
        tk.Label(self.checkbox_frame.interior, text="").grid(row=i, column=0, sticky="w")

    def choose_folder(self):
        # Open file dialog to choose folder
        folder_path = filedialog.askdirectory(title="Choose the ground truth folder")
        self.llsp_files = list(glob.glob(f"{folder_path}/*.llsp")) + list(glob.glob(f"{folder_path}/*.llsp3"))
        self.choose_folder_button["state"] = "disabled"
        self.save_button["state"] = "normal"
        self.initialize_trees()
        self.text_window_refresh()
        self.root.eval('tk::PlaceWindow . center')


if __name__ == "__main__":
    paths = get_paths(r"paths.yml")
    tk_root = tk.Tk()
    app = GTParser(tk_root, paths)
    tk_root.mainloop()
