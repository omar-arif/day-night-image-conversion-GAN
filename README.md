# Generating pair of images using Carla Simulator.

* Authors: Hamza Benmendil, Omar Khalifa Arif

In order to generate pair of images day/night (also semantic images), we are using carla simulator v 0.9.12, an open source simulator for autonomous driving car.

---

## Pre-requirements
- Carla simulator (requires a GPU with at least 6 Go in memory).
- python (>=3 recommended)
- install dependencies using: `python install -r requirements.txt`

---

## Execution and Image generation
You'll notice that there is two scripts `record_scenario.py` and `replay_scenario.py`, copy and paste them in the directory `PythonAPI/exemples/` from the carla simulatore root directory.

In order to generate the images you need to:
- Execute the Carla server.
- Change the map if you want to, using the script `config.py` (cf. Carla simulator documentation).
- Execute `record_scenario.py` file, he will spawn an autopilot car, record its path and save it in a log file. To choose the name of the file add the option `--file [filename]` to the execution command (by default: `recording.log`).
- Execute `replay_scenario.py` file, he will replay the given scenario in day or night and capture rgb and semantic images every 20 frames utill capturing 100 image. The images are stored in a directory called data. The script can be executed with the following options:
    - `--file [filename]` to replay the scenario in a specific file (`recording.log` by default)
    - `--night [True/False]` to replay the scenario in the night or the day (False which mean day by default).
    - `--width [int]` the width of the captured images (1920 by default).
    - `--height [int]` the height of the captured images (1080 by default).

So, to execute a pair of images day/night you need to record a scenario once, then replay it twice with night option and without it.

---

## Comparaison of images
You'll find also a notebook called `compare_images.ipynb`, it is used to compare generated images by Carla, and see if a pair of images  in the same conditions are identical.

We generated two sets of images from two different execution of the file `replay_scenario.py` with the same conditions (both are in the day) using the same scenario. Then, we constructed a difference image using the difference pixel by pixel of compared images.

The output image seems to have a very small none null pixels. 

### Difference image in the frame 17
![diff image frame 17](diff_imgs_sample/recording00_17.png)

### Difference image in the frame 10
![diff image frame 10](diff_imgs_sample/recording00_10.png)

But we found that ~43% of pixels are not null which is a big percentage.

So, we ploted the distribution of none zero pixels (for the red color) in the difference image and found that the majority of none zero pixels have a value less than 25, and the number of pixels that have a value between 50 and 100 have a peek in 250 pixels which is very negligible.

![distribution frame 17](diff_imgs_sample/recording00_17_dist.png)

![distribution frame 17 from 50](diff_imgs_graphs/recording00_17_dist_from_50.png)

We found the same shape of distribution for an other difference image (frame 10).

![distribution frame 10](diff_imgs_graphs/recording00_10_dist.png)