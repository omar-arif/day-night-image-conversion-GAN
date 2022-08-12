import glob
import os
import sys
import time

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla

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
        '-f', '--file',
        metavar='F',
        default="recording.log",
        type=str,
        help='name of the log file (default: recording.log)')
    args = argparser.parse_args()

    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

    client = carla.Client(args.host, args.port)
    client.set_timeout(10.0)

    try:
        world = client.get_world()
        ego_vehicle = None
        ego_cam = None
        sem_cam = None

        # ----------------
        # Set World Settings
        # ----------------

        # We need to save the settings to be able to recover them at the end
        # of the script to leave the server in the same state that we found it.

        original_settings = world.get_settings()
        settings = world.get_settings()

        # # We set CARLA syncronous mode
        settings.fixed_delta_seconds = 0.05
        settings.synchronous_mode = True
        world.apply_settings(settings)

        # --------------
        # Spawn ego vehicle
        # --------------
        
        ego_bp = world.get_blueprint_library().find('vehicle.tesla.model3')
        ego_bp.set_attribute('role_name','ego')
        print('\nEgo role_name is set')
        ego_color = random.choice(ego_bp.get_attribute('color').recommended_values)
        ego_bp.set_attribute('color',ego_color)
        print('\nEgo color is set')

        spawn_points = world.get_map().get_spawn_points()
        number_of_spawn_points = len(spawn_points)

        if 0 < number_of_spawn_points:
            random.shuffle(spawn_points)
            ego_transform = spawn_points[0]
            ego_vehicle = world.spawn_actor(ego_bp,ego_transform)
            print('\nEgo is spawned')
        else: 
            logging.warning('Could not found any spawn points')

               
        # --------------
        # Start recording
        # --------------
        
        client.start_recorder(args.file)

        # --------------
        # Place spectator on ego spawning
        # --------------
        
        spectator = world.get_spectator()
        world.tick()
        spectator.set_transform(ego_vehicle.get_transform())

        # --------------
        # Enable autopilot for ego vehicle
        # --------------
        
        ego_vehicle.set_autopilot(True)
        

        # --------------
        # Game loop. Prevents the script from finishing.
        # --------------
        first_frame = w_frame = world.get_snapshot().frame
        while True:
            world.tick()
            w_frame = world.get_snapshot().frame
            if (w_frame - first_frame) / 20 == 101:
                print("frames:", w_frame,"--", first_frame)
                break

    finally:
        world.apply_settings(original_settings)
        # --------------
        # Stop recording and destroy actors
        # --------------
        client.stop_recorder()
        if ego_vehicle is not None:
            if ego_cam is not None:
                ego_cam.stop()
                ego_cam.destroy()
            if sem_cam is not None:
                sem_cam.stop()
                sem_cam.destroy()
            ego_vehicle.destroy()

if __name__ == '__main__':

    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        print('\nDone with tutorial_ego.')