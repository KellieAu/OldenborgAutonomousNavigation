#!/bin/bash -l

#SBATCH --job-name="TrainTeleportingModels-Summer2024Official"
#SBATCH --time=2-00:00:00
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --mem=40G
#SBATCH --mail-user=tfrw2023@mymail.pomona.edu
#SBATCH --mail-type=ALL

# Steps to run a training script on the cluster:
# 1. Make a copy of this file (eg, cp _launch_template.sh new_launch_script.sh)
#    - come up with a better file name than new_launch_script.sh
#    - maybe something based on the model name, project name, etc.
# 2. Edit the new file and set the
#    - job-name
#    - mail-user
#    - ENVIRONMENT, MODEL_NAME, PROJECT_NAME, description, ARCHITECTURE_NAME, DATA_NAME
#    - python script line
#    - any other changes you deem necessary (eg, a different GPU or more memory)
# 3. Run the sbatch script with: sbatch new_launch_script.sh

# Print the current date and name of the node for debugging
date    
hostname

# Load conda and activate an environment 
module load miniconda3
conda activate s24 

# Run training script
# srun --nodes 1 --ntasks 1 --exclusive python training.py TeleportingStaticModel Summer2024Official "Training Model on Teleporting Static Data with MobileNetV4" MobileNetV4 Teleporting100kData  
srun --nodes 1 --ntasks 1 --exclusive python training.py TeleportingRand10Model Summer2024Official "Training Model on Teleporting Randomized Textures every 10 Data with MobileNetV4" MobileNetV4 Teleporting100kRandEvery10Data
# srun --nodes 1 --ntasks 1 --exclusive python training.py TeleportingRand50Model Summer2024Official "Training Model on Teleporting Randomized Textures every 50 Data  with MobileNetV4" MobileNetV4 Teleporting100kRandEvery50Data

# Print the date again to see how long the job took
date