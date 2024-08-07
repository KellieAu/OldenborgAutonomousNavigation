#!/bin/bash -l

#SBATCH --job-name="TrainPerfectModels-Summer2024Official"
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

# Print the current date for debugging
date
hostname

# Load conda and run the training script
module load miniconda3
conda activate s24

srun --nodes 1 --ntasks 1 --exclusive python training.py PerfectStaticModel Summer2024Official "training off 100k perfect navigator image dataset with MobileNetV4" MobileNetV4 Perfect100kData
srun --nodes 1 --ntasks 1 --exclusive python training.py PerfectRand10Model Summer2024Official "training off 100k perfect navigator every 10 image dataset with MobileNetV4" MobileNetV4 Perfect100kRandEvery10Data
srun --nodes 1 --ntasks 1 --exclusive python training.py PerfectRand50Model Summer2024Official "training off 100k perfect navigator every 50 image dataset with MobileNetV4" MobileNetV4 Perfect100kRandEvery50Data

# Print the finish date for debugging
date