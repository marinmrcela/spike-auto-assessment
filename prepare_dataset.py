from cf import get_paths, directory_dialog, get_project
import glob
import json
import os
from tqdm import tqdm
import concurrent.futures


class LLSPProcessor:
    # Expects folder containing folders named after student IDs containing their snapshots.
    # The snapshots will be parsed into json files for fast assessment and feature collection.
    def __init__(self, _path, _out_folder_name):
        self.path = _path
        self.folders_all = glob.glob(f'{_path}/*/')
        self.folders = []
        self.projects = {}
        self.out_folder = os.path.normpath(_out_folder_name)

    def process_folders(self):
        for folder in self.folders_all:
            folder_files = os.listdir(folder)
            if folder_files:
                first_file_extension = os.path.basename(folder_files[0]).split(".")[-1]
                if first_file_extension in ("llsp", "llsp3"):
                    self.folders.append(folder)

    @staticmethod
    def get_project_with_tqdm(llsp_file, pbar):
        project = get_project(llsp_file)
        pbar.update()
        return project

    def process_files(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Create a list of file paths to process
            llsp_files = []
            for folder in self.folders:
                llsp_files += list(glob.glob(f"{folder}/*.llsp")) + list(glob.glob(f"{folder}/*.llsp3"))
            # Create a dictionary to store the future objects
            with tqdm(total=len(llsp_files),
                      bar_format='Processing files:  {l_bar}{bar}|  {n_fmt}/{total_fmt}') as pbar:
                future_to_file = {executor.submit(self.get_project_with_tqdm, file, pbar): file for file in llsp_files}
                for future in concurrent.futures.as_completed(future_to_file):
                    file = future_to_file[future]
                    try:
                        # Extract the folder name and file name from the file path
                        folder_name = os.path.basename(os.path.dirname(file))
                        file_name = os.path.basename(file)
                        # Add the project information to the projects dictionary
                        if folder_name not in self.projects:
                            self.projects[folder_name] = {}
                        self.projects[folder_name][file_name] = future.result()
                    except Exception as exc:
                        print(f'{file} generated an exception: {exc}')

    def create_output_folder(self):
        if not os.path.isdir(self.out_folder):
            os.makedirs(self.out_folder)

    def save_folder_output(self, folder_name):
        out_file = f"{self.out_folder}/{folder_name}.json"
        sorted_primary_keys = sorted(list(self.projects[folder_name].keys()))
        primary_sorted_project = {key: self.projects[folder_name][key] for key in sorted_primary_keys}
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(primary_sorted_project, f, indent=2)

    def save_output(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_folder = {executor.submit(self.save_folder_output, folder): folder for folder in
                                self.projects.keys()}
            for future in tqdm(concurrent.futures.as_completed(future_to_folder), total=len(future_to_folder),
                               bar_format='Saving output:     {l_bar}{bar}|  {n_fmt}/{total_fmt}'):
                folder = future_to_folder[future]
                try:
                    future.result()
                except Exception as exc:
                    print(f'{folder} generated an exception: {exc}')

    def run(self):
        self.create_output_folder()
        self.process_folders()
        self.process_files()
        self.save_output()
        print(f"\nDone.\nOutput path: {self.out_folder}")


if __name__ == "__main__":
    paths = get_paths(r"paths.yml")
    path = directory_dialog(title="Choose the folder with project snapshots sorted into folders by ID")
    out_folder_name = os.path.expanduser(paths["projectsdir"])
    processor = LLSPProcessor(path, out_folder_name)
    processor.run()
