# Spike Auto Assessment
Automatic assessment and data mining of projects built in Lego Spike app. Projects are evaluated through comparison with established, correct solutions. Parameters of evaluation and distance to the correct solution are adjustable. 
## Project files preparation
Initial dataset preparation is performed using **prepare_dataset.py**. Choosing a folder containing snapshots of the workshop sorted into folders by student IDs will produce student files in the **Projects** folder in the working directory. 
## Assessment and data mining
For each task a set of correct solutions must be created and put inside a folder that will be used by **gt_parser.py**, where parameters for evaluation are chosen. Results are displayed and stored in tables in the working directory.
