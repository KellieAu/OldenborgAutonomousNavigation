import random
from argparse import ArgumentParser, BooleanOptionalAction, Namespace
from math import radians
from pathlib import Path
from random import randrange

import matplotlib.pyplot as plt
from box.box import Pt, aligned_box
from box.boxenv import BoxEnv
from box.boxnavigator import PerfectNavigator, TeleportingNavigator, WanderingNavigator
from box.boxunreal import UENavigatorWrapper
from celluloid import Camera
from tqdm import tqdm

from ue5osc import TexturedSurface

# TODO: this should probably be a command line argument (pass in a list of coordinates)
# route 2, uses path w/ water fountain & stairs
boxes = [
    aligned_box(left=4640, right=5240, lower=110, upper=1510, target=(4940, 870)),
    aligned_box(left=3720, right=5240, lower=700, upper=1040, target=(4000, 870)),
    aligned_box(left=3850, right=4120, lower=360, upper=1040, target=(4000, 400)),
    aligned_box(left=110, right=4120, lower=260, upper=540, target=(255, 400)),
    aligned_box(left=150, right=400, lower=-1980, upper=540, target=(255, -1850)),
    aligned_box(left=-1550, right=400, lower=-1980, upper=-1720, target=(-825, -1850)),
    aligned_box(left=-900, right=-700, lower=-1980, upper=3320, target=(-825, 2485)),
    aligned_box(left=-900, right=230, lower=2150, upper=2820, target=(150, 2485)),
]


def check_path(directory: str) -> None:
    path = Path(directory)
    # Create directory if it doesn't exist
    path.mkdir(parents=True, exist_ok=True)

    # Check if directory is empty
    if len(list(Path(path).iterdir())) != 0:
        raise ValueError(f"Directory {path} is not empty.")


def simulate(args: Namespace) -> None:
    """Create and update the box environment and run the navigator."""

    box_env = BoxEnv(boxes)

    starting_box = boxes[0]
    initial_x = starting_box.left + starting_box.width / 2
    initial_y = starting_box.lower + 50
    initial_position = Pt(initial_x, initial_y)
    initial_rotation = radians(90)

    if args.navigator == "wandering":
        NavigatorConstructor = WanderingNavigator
    elif args.navigator == "perfect":
        NavigatorConstructor = PerfectNavigator
    elif args.navigator == "teleport":
        NavigatorConstructor = TeleportingNavigator
    else:
        raise ValueError("Invalid value for navigator.")

    agent = NavigatorConstructor(
        initial_position,
        initial_rotation,
        box_env,
        args.distance_threshold,
        args.movement_increment,
        args.rotation_increment,
    )

    # Wrap the agent if we want to connect to Unreal Engine
    if args.ue:
        agent = UENavigatorWrapper(
            agent,
            args.save_images,
            args.py_port,
            args.ue_port,
            args.image_ext,
            args.movement_increment,
            args.resolution,
            # TODO: add quality level as a command line argument?
        )

    is_ue_navigator = isinstance(agent, UENavigatorWrapper)

    fig, ax = plt.subplots()
    camera = Camera(fig)

    """
    # TODO: for AJC to try out later
    import enlighten

    manager = enlighten.get_manager()
    trial_bar = manager.counter(total=32, desc="Trial")

    for trial in range(32):
        step_bar = manager.counter(total=128, desc="Step", leave=False)
        for step in range(128):
            time.sleep(0.01)
            step_bar.update()
        step_bar.close()
        print("Trial happened")
        trial_bar.update()

    manager.stop()
    """

    for _ in tqdm(range(args.max_total_actions), desc="Actions taken"):
        if agent.stuck or agent.at_final_target():
            # num_actions = agent.num_actions_taken()
            # if agent.at_final_target():
            #     print(f"Agent reached final target in {num_actions} actions.")
            # else:
            #     print(f"Agent was unable to reach final target within {num_actions} actions.")
            agent.reset()
            if args.stop_after_one_trial:
                break

        try:
            _ = agent.take_action()

        except TimeoutError as e:
            print(e)
            if is_ue_navigator:
                agent.ue.close_osc()
            raise SystemExit

        except Exception as e:
            print(e)
            if is_ue_navigator:
                agent.ue.close_osc()
            raise SystemExit

        if is_ue_navigator:
            # TODO: turn "20" into a command line argument
            if agent.num_actions_taken() % 20 == 0 and args.randomize:
                random_surface = random.choice(list(TexturedSurface))
                agent.ue.set_texture(random_surface, randrange(42))

        if args.anim_ext:
            # TODO: Rotate axis so that agent is always facing up
            box_env.display(ax)
            agent.display(ax, 300)
            ax.invert_xaxis()
            camera.snap()

    if isinstance(agent, UENavigatorWrapper):
        agent.ue.close_osc()

    print("Simulation complete.", end=" ")

    if args.anim_ext:
        output_filename = None
        num = 1
        while not output_filename or Path(output_filename).exists():
            output_filename = f"output_{num}.{args.anim_ext}"
            num += 1
        anim = camera.animate()
        anim.save(output_filename)
        print(f"Animation saved to {output_filename}.")


def main():
    """Parse arguments and run simulation."""

    argparser = ArgumentParser("Navigate around a box environment.")

    #
    # Required arguments
    #

    argparser.add_argument("navigator", type=str, help="Navigator to run.")

    #
    # Optional arguments
    #

    argparser.add_argument("--anim_ext", type=str, help="Output format for animation.")

    argparser.add_argument(
        "--save_images",
        type=str,
        help="Directory in which images should be saved (no images saved otherwise).",
    )

    argparser.add_argument(
        "--ue", action="store_true", help="Connect and send command to Unreal Engine."
    )

    argparser.add_argument(
        "--py_port", type=int, default=7001, help="Python OSC server port."
    )

    argparser.add_argument(
        "--ue_port", type=int, default=7447, help="Unreal Engine OSC server port."
    )

    argparser.add_argument(
        "--resolution",
        type=str,
        default="244x244",
        help="Set resolution of images as ResXxResY.",
    )

    argparser.add_argument(
        "--image_ext", type=str, default="png", help="Output format for images"
    )

    argparser.add_argument(
        "--max_total_actions",
        type=int,
        default=10,
        help="Maximum total allowed actions across all trials.",
    )

    argparser.add_argument(
        "--stop_after_one_trial",
        type=bool,
        default=False,
        help="Stop after one time through the environment (for debugging).",
    )

    argparser.add_argument(
        "--movement_increment",
        type=float,
        default=120.0,
        help="Determines how far to move forward each step.",
    )

    argparser.add_argument(
        "--rotation_increment",
        type=float,
        default=radians(10),
        help="Determines how much to rotate by for each step.",
    )

    argparser.add_argument(
        "--distance_threshold",
        type=int,
        default=75,
        help="Determines how close the robot has to be to the target to activate the next one.",
    )

    argparser.add_argument(
        "--randomize",
        type=bool,
        default=False,
        action=BooleanOptionalAction,
        help="Randomizes the texture of the walls, floors, and ceilings.",
    )

    args = argparser.parse_args()

    possible_navigators = ["wandering", "perfect", "teleport"]
    if args.navigator not in possible_navigators:
        raise ValueError(
            f"Invalid navigator type: {args.navigator}. Possible options: {'|'.join(possible_navigators)}"
        )

    if args.save_images:
        args.ue = True

    if args.save_images:
        check_path(args.save_images)

    simulate(args)


if __name__ == "__main__":
    main()
