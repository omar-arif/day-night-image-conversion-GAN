import glob
import os
import sys
import time
import math
import weakref
from queue import Queue
from queue import Empty

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla

rgb_counter = 1
sem_counter = 1

# Sensor callback.
# This is where you receive the sensor data and
# process it as you liked and the important part is that,
# at the end, it should include an element into the sensor queue.
def sensor_callback(sensor_data, sensor_queue, sensor_name, is_night, rec_file):
    global rgb_counter, sem_counter
    # Do stuff with the sensor_data data like save it to disk
    rgb_path = "data/rgb_night_output/" + rec_file.split(".")[0] + "_%d.png" % rgb_counter if is_night else "data/rgb_output/" + rec_file.split(".")[0] + "_%d.png" % rgb_counter
    sem_path = "data/sem_night_output/" + rec_file.split(".")[0] + "_%d.png" % sem_counter if is_night else "data/sem_output/" + rec_file.split(".")[0] + "_%d.png" % sem_counter
    if sensor_name == "rgb_camera":
        sensor_data.save_to_disk(rgb_path)
        rgb_counter += 1
    elif sensor_name == "sem_camera":
        sensor_data.save_to_disk(sem_path, carla.ColorConverter.CityScapesPalette)
        sem_counter += 1
    # Then you just need to add to the queue
    sensor_queue.put((sensor_data.frame, sensor_name))

import argparse
import logging
import random

def main():
    argparser = argparse.ArgumentParser(
        description=__doc__)
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    argparser.add_argument(
        '-n', '--night',
        metavar='N',
        default=False,
        type=bool,
        help='set night/day (default: day)')
    argparser.add_argument(
        '-f', '--file',
        metavar='F',
        default="recording.log",
        type=str,
        help='replay file name (default: recording.log)')
    argparser.add_argument(
        '-w', '--width',
        metavar='W',
        default=1920,
        type=int,
        help='generated image width (default: 1920)')
    argparser.add_argument(
        '-ht', '--height',
        metavar='HT',
        default=1080,
        type=int,
        help='generated image height (default: 1080)')
    args = argparser.parse_args()

    width = args.width
    height = args.height
    is_night = args.night
    rec_file = args.file
    client = carla.Client(args.host, args.port)
    client.set_timeout(10.0)

    try:

        world = client.get_world() 
        ego_vehicle = None
        ego_cam = None
        sem_cam = None

        # We create the sensor queue in which we keep track of the information
        # already received. This structure is thread safe and can be
        # accessed by all the sensors callback concurrently without problem.
        sensor_queue = Queue()

        # --------------
        # Query the recording
        # --------------
        
        # Show the most important events in the recording.
        recorder_info = client.show_recorder_file_info(rec_file,False)
        print(recorder_info)
        # Show actors not moving 1 meter in 10 seconds.  
        #print(client.show_recorder_actors_blocked("~/tutorial/recorder/recording04.log",10,1))
        # Show collisions between any type of actor.  
        #print(client.show_recorder_collisions("~/tutorial/recorder/recording04.log",'v','a'))
        

        # --------------
        # Reenact a fragment of the recording
        # --------------
        
        client.replay_file(rec_file,0,0,0)

        # --------------
        # Set playback simulation conditions
        # --------------

        # ----------------
        # Set World Settings
        # ----------------

        # We need to save the settings to be able to recover them at the end
        # of the script to leave the server in the same state that we found it.
        original_settings = world.get_settings()
        settings = world.get_settings()

        # We set CARLA syncronous mode
        settings.fixed_delta_seconds = 0.05
        settings.synchronous_mode = True
        world.apply_settings(settings)

        #Store the ID from the simulation or query the recording to find out
        for line in recorder_info.split("\n"):
            if "vehicle.tesla.model3" in line:
                vehicule_id = line.split(" ")[2][:-1]

        ego_vehicle = world.get_actor(int(vehicule_id))
        
     
        # --------------
        # Change weather conditions
        # --------------
        
        weather = world.get_weather()
        if is_night:
            weather.sun_altitude_angle = -45
        else:
            weather.sun_altitude_angle = 80

        weather.fog_density = 1
        weather.fog_distance = 0.75
        weather.cloudiness = 0
        world.set_weather(weather)
        

        # --------------
        # Add a RGB camera to ego vehicle.
        # --------------
        
        cam_bp = None
        cam_bp = world.get_blueprint_library().find('sensor.camera.rgb')
        cam_location = carla.Location(2,0,1)
        cam_rotation = carla.Rotation(0,180,0)
        cam_transform = carla.Transform(cam_location,cam_rotation)
        cam_bp.set_attribute("image_size_x",str(width))
        cam_bp.set_attribute("image_size_y",str(height))
        cam_bp.set_attribute("fov",str(105))
        cam_bp.set_attribute("sensor_tick", '1.0')
        ego_cam = world.spawn_actor(cam_bp,cam_transform,attach_to=ego_vehicle, attachment_type=carla.AttachmentType.SpringArm)
        ego_cam.listen(lambda data: sensor_callback(data, sensor_queue, "rgb_camera", is_night, rec_file))        
        
        # --------------
        # Add a new semantic segmentation camera to ego vehicle
        # --------------
        
        sem_cam = None
        sem_bp = world.get_blueprint_library().find('sensor.camera.semantic_segmentation')
        sem_bp.set_attribute("image_size_x",str(width))
        sem_bp.set_attribute("image_size_y",str(height))
        sem_bp.set_attribute("fov",str(105))
        sem_bp.set_attribute("sensor_tick", '1.0')
        sem_location = carla.Location(2,0,1)
        sem_rotation = carla.Rotation(0,180,0)
        sem_transform = carla.Transform(sem_location,sem_rotation)
        sem_cam = world.spawn_actor(sem_bp,sem_transform,attach_to=ego_vehicle, attachment_type=carla.AttachmentType.SpringArm)
        # This time, a color converter is applied to the image, to get the semantic segmentation view
        sem_cam.listen(lambda data: sensor_callback(data, sensor_queue, "sem_camera", is_night, rec_file))

        # --------------
        # Place spectator on ego spawning
        # --------------
        
        spectator = world.get_spectator()
        world.tick()
        spectator.set_transform(ego_vehicle.get_transform())

        # --------------
        # Game loop. Prevents the script from finishing.
        # --------------

        first_frame = world.get_snapshot().frame
        counter = 0
        while True:
            world.tick()
            w_frame = world.get_snapshot().frame
            try:
                s_frame = sensor_queue.get(True, .1)
                counter += 1
                print("    Frame: %d   Sensor: %s" % (s_frame[0], s_frame[1]))
            
            except Empty:
                pass
            if w_frame % 100 == 0:
                print("world's frame: %d" % w_frame)

            if counter == 200 and (w_frame - first_frame) / 20 == 100:
                break

    finally:
        world.apply_settings(original_settings)
        # --------------
        # Destroy actors
        # --------------
        if ego_vehicle is not None:
            if ego_cam is not None:
                ego_cam.stop()
                ego_cam.destroy()
            if sem_cam is not None:
                sem_cam.stop()
                sem_cam.destroy()
            ego_vehicle.destroy()
        print('\nNothing to be done.')


if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        print('\nDone with tutorial_replay.')