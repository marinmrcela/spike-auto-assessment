# Some common functions for the programs.

def directory_dialog(title='Choose the directory:'):
    import tkinter
    from tkinter.filedialog import askdirectory
    root = tkinter.Tk()
    root.withdraw()
    root.call('wm', 'attributes', '.', '-topmost', True)
    directory = askdirectory(parent=root, title=title)
    return directory


def get_paths(paths_file):
    import yaml

    with open(paths_file, 'r') as file:
        params = yaml.safe_load(file)

    params = {k.lower(): v for k, v in params.items()}  # Case-insensitive

    return params


def get_params(params_path):
    import yaml

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
