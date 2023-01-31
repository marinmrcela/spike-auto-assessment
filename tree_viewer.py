import json
import os.path
import tkinter as tk
from tkinter import filedialog
from datetime import datetime


class TreeViewer:
    def __init__(self, _root):
        self.show_key_label = None
        self.open_file_label = None
        self.yscrollbar = None
        self.key_entry = None
        self.show_key_button = None
        self.show_key_text = tk.StringVar()
        self.key_var = tk.StringVar()
        self.data = None
        self.text_widget = None
        self.open_file_button = None
        self.open_file_text = tk.StringVar()
        self.root = _root
        self.root.title("Tree Viewer")
        self.root.resizable(False, False)
        self.root.eval('tk::PlaceWindow . center')
        self.create_widgets()

    def create_widgets(self):
        self.open_file_button = tk.Button(self.root, text="Open File", command=self.open_file)
        self.open_file_button.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        self.open_file_label = tk.Label(self.root, textvariable=self.open_file_text)
        self.open_file_label.grid(row=1, column=0, columnspan=2)

        self.key_entry = tk.Entry(self.root, textvariable=self.key_var, width=40)
        self.key_entry.grid(row=2, column=0, sticky="e", padx=5, pady=5)

        self.show_key_button = tk.Button(self.root, text="Search", command=self.show_key)
        self.show_key_button["state"] = "disabled"
        self.show_key_button.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        self.show_key_label = tk.Label(self.root, textvariable=self.show_key_text)
        self.show_key_label.grid(row=3, column=0, columnspan=2)

        self.text_widget = tk.Text(self.root, wrap="none")
        self.text_widget.grid(row=4, column=0, columnspan=2)

        self.yscrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.text_widget.yview)
        self.yscrollbar.grid(row=4, column=2, sticky="ns")
        self.text_widget.config(yscrollcommand=self.yscrollbar.set)

        spacer = tk.Label(self.root, text="")
        spacer.grid(row=5)

    def open_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON files", ".json")])
        filename = os.path.basename(filepath)
        with open(filepath, 'r') as f:
            json_data = json.load(f)
        if not isinstance(json_data[list(json_data.keys())[0]], dict):  # Differentiates project from tree
            # if not (any(isinstance(i, dict) for i in json_data.values())):
            self.open_file_label.config(fg="black")
            self.open_file_text.set(filename)
            self.data = json_data
            formatted_json_data = ""
            counter = 0
            for _key, _value in json_data.items():
                counter += 1
                try:
                    timestamp = float(_key.split(" ")[0]) / (10 ** 8)
                    dt = datetime.fromtimestamp(timestamp)
                except ValueError:
                    dt = ""
                formatted_json_data += f"#{counter}\n{dt}\n{_key}:{_value}\n\n"
            max_width = max([len(line) for line in formatted_json_data.split("\n")])
            self.text_widget.config(width=max_width)
            self.text_widget.config(height=32)
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert(tk.INSERT, formatted_json_data)
            self.show_key_text.set("")
            self.show_key_button["state"] = "normal"
            self.root.eval('tk::PlaceWindow . center')
        else:
            self.open_file_label.config(fg="red")
            self.open_file_text.set("Invalid tree file")
            self.show_key_button["state"] = "disabled"
            self.text_widget.delete("1.0", tk.END)

    def show_key(self):
        key = str(self.key_var.get())

        line_num = self.text_widget.search(key, "1.0", tk.END)
        if line_num:
            self.text_widget.tag_remove("highlight", "1.0", tk.END)
            self.text_widget.tag_add("highlight", line_num, line_num + "+1line")
            self.text_widget.tag_config("highlight", background="yellow")

            line = int(line_num.split(".")[0]) - 1
            lines = self.text_widget.index(tk.END).split(".")[0]
            pos = line / int(lines)

            self.text_widget.yview_moveto(pos)
            self.show_key_label.config(fg="black")
            self.show_key_text.set(f"Text found in line {line_num.split('.')[0]}")

        else:
            self.text_widget.tag_remove("highlight", "1.0", tk.END)
            self.show_key_label.config(fg="red")
            self.show_key_text.set("Text not found")


if __name__ == '__main__':
    root = tk.Tk()
    app = TreeViewer(root)
    root.mainloop()
