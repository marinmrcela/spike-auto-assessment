# Snapshots collecting tool for Lego Spike workshops.
# If the default Spike directory isn't found,
# a window for choosing the directory pops up.
# However, this is not expected and the reason might be
# the Spike app hasn't yet created the directory,
# since the directory is created when the first
# project is created.
# The output path where all the snapshots are archived
# into a zip file is defined as snapshots_path
# in the main part of the program.

# Spike modifies all the project files in its directory
# at every start, therefore, those files will also be
# included if this tool is started before Spike.
# For some changes, Spike modifies the file multiple times,
# twice for example for block removals.


from subprocess import Popen
from pathlib import Path
from time import time, sleep
from shutil import copyfile
from zipfile import ZipFile
from random import choice
from string import ascii_lowercase

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from tkinter import Tk, Button, Label, StringVar
from tkinter.filedialog import askdirectory


def zero_fill(in_s):
    # Insert zeros at the end of a string
    final_length = 18
    ad_s = "0" * (final_length-len(in_s))
    out_s = in_s + ad_s
    return out_s


def random_string(ln):
    ls = ascii_lowercase
    res = ""
    for i in range(ln):
        res += choice(ls)
    return res


def directory_dialog():

    root = Tk()
    root.withdraw()
    root.call('wm', 'attributes', '.', '-topmost', True)
    dd = askdirectory(parent=root, title='Choose the Spike working directory')

    return dd


def file_accessible(fp):
    # Check if file can be accessed.
    fa = False
    try:
        with open(fp):
            fa = True
    except:
        pass
    return fa


class MyHandler(FileSystemEventHandler):

    def __init__(self, _snapshots_path):
        self.counter = 0
        self.file_prev = None
        self.snapshots_path = _snapshots_path

    def on_modified(self, event):
        # When a file is modified
        file_path = Path(event.src_path)
        file_extension = file_path.suffix

        if file_extension == ".llsp" or file_extension == ".llsp3":

            file_name = file_path.stem

            while not file_accessible(file_path):
                # Wait until file is closed
                sleep(0.01)

            with open(file_path, 'rb') as f:
                file_curr = f.read()

            if file_curr != self.file_prev:
                self.counter += 1
                self.file_prev = file_curr
                tstamp = zero_fill(str(time()).replace('.', ''))
                copyfile(file_path, self.snapshots_path / str(tstamp + " " + file_name + file_extension))


class GUI:
    def __init__(self, _snapshots_path, _open_when_finished):

        self.snapshots_path = _snapshots_path
        self.open_when_finished = _open_when_finished
        self.zipfile_full_path = None
        default_dir = Path.expanduser(Path('~/Documents/LEGO Education SPIKE'))
        self.event_handler = MyHandler(_snapshots_path=self.snapshots_path)
        self.observer = Observer()  # Watchdog
        if Path.is_dir(default_dir):
            directory = default_dir
        else:
            # If the working directory was not found
            directory = Path(directory_dialog())

        self.subfolder = self.snapshots_path
        self.subfolder.mkdir(parents=True, exist_ok=True)
        self.observer.schedule(self.event_handler, str(directory), recursive=False)
        self.observer.start()

        self.settings = {"exit": False}
        self.root = Tk()
        self.root.title("Lego Spike Logger")
        self.txt_var = StringVar()
        self.txt_var.set("Snapshots count: " + str(self.event_handler.counter))
        instruction = " "*10 + "*** Please do not close this window ***" + " "*10
        Label(self.root, text=instruction).pack()
        Label(self.root, textvariable=self.txt_var).pack()
        Label(self.root, text="").pack()
        Button(self.root, text="Collect snapshots", command=self.make_callback("exit")).pack()
        Label(self.root, text="").pack()
        self.root.iconify()

    def make_callback(self, key):
        def button_var():
            self.settings[key] = True
        return button_var

    def main(self):

        while not self.settings["exit"]:
            sleep(0.05)
            self.txt_var.set("Snapshots count: " + str(self.event_handler.counter))
            self.root.update()

        self.observer.stop()
        self.observer.join()
        self.root.destroy()
        self.root.quit()

        llsp_files = list(self.subfolder.glob('*.llsp')) + list(self.subfolder.glob('*.llsp3'))
        zipfile_name = "Lego Spike " + random_string(16) + ".zip"
        self.zipfile_full_path = self.subfolder / zipfile_name
        with ZipFile(self.zipfile_full_path, mode="a") as archive:
            for file in llsp_files:
                archive.write(filename=file, arcname=file.name)

        if self.open_when_finished:
            Popen(f'explorer /select,"{self.zipfile_full_path}"')


if __name__ == "__main__":
    # "snapshots" folder in the current directory
    snapshots_path = Path().absolute() / "snapshots"
    open_when_finished = True
    g = GUI(snapshots_path, open_when_finished)
    g.main()
