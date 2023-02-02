
# Spike Auto Assessment
Automatic assessment and data mining of projects built in Lego Spike app. Projects are evaluated through comparison with established, correct solutions. Parameters of evaluation and distance to the correct solution are adjustable. 
## Requirements
The project was built using Python version 3.10. The programs require additional packages: **anytree**, **levenshtein**, **pandas**, **pyyaml**, **tqdm**, **watchdog**. The command **pip install** can be used to install the packages:

    pip install anytree levenshtein pandas pyyaml tqdm watchdog

## Working directories 
Working directories are defined in **paths.yml**. The initial directory is set to **Documents/Spike Data**. The subfolders are:

 - **Projects** which will contain the parsed snapshots inside *json* files named after the student IDs,
 - **Trees** which will contain the tree files adjusted for assessment by the task,
 - **Distances** which will contain *csv* tables showing the minimal distances from the correct solutions by the students and 
 - **Info** which will contain *csv* tables with information about each of the students' solution.

## Snapshots collection
Snapshots are collected by running **collect_snapshots.py** in the background for the duration of the workshop. Snapshots will be packaged into a *zip* file for a convenient transfer.
## Project files preparation
Initial dataset preparation is performed using **prepare_dataset.py**. Choosing a folder containing extracted snapshots of the workshop sorted into folders by student IDs will produce student files in the **Projects** folder in the working directory. 
## Assessment and data mining
For each task a set of correct solutions must be created and put inside a folder that will be used by **assess_task.py**, where parameters for evaluation are chosen. Results are displayed and stored in tables in the working directory.
## Tree viewing
Trees created for assessment from the original snapshots can be viewed using **tree_viewer.py**. 
## Step-by-step solution
graph TD
    A[Collect snapshots in Lego Spike workshops.] 
    A --> B[Unzip each file into a folder named after it,<br />keeping all the folders in one parent folder.]
    B --> C[Prepare the dataset selecting the parent folder.]
    C --> D[Create ground truth solutions for each task, separated into folders.]
    D --> E[Task 01]
    D --> F[Task 02]
    D --> G[...]
    H{Evaluate each task by<br />selecting the corresponding<br />ground truth folder<br />and adjusting parameters.}
    E --> H
    F --> H
    G --> H
    H --> I[Distance tables<br />Info tables<br />per task]
