from math import degrees
from pathlib import Path
from time import sleep

from ue5osc import Communicator

from .box import Pt
from .boxnavigator import Action, BoxNavigatorBase


class UENavigatorWrapper:
    """A wrapper for navigators that facilitates coordination with UnrealEngine 5."""

    def __init__(
        self,
        navigator: BoxNavigatorBase,
        dataset_path: str | None,
        py_server_port: int,
        ue_server_port: int,
        image_ext: str,
        movement_increment: float,
        resolution: str,
        quality_level: int = 1,
    ) -> None:
        self.ue = Communicator("127.0.0.1", ue_server_port, py_server_port)

        self.navigator = navigator
        self.dataset_path = Path(dataset_path).resolve() if dataset_path else None

        if self.dataset_path:
            self.dataset_path.mkdir(parents=True, exist_ok=True)

        self.raycast_length = movement_increment

        self.trial_num = 0
        self.images_saved = 1
        self.image_ext = image_ext
        self.num_stationary_moves = 0
        self.distance_moved = [0, 0]
        self.stuck = False

        try:
            # Sync UE and boxsim
            self.sync_positions()
            self.sync_rotation()
        except TimeoutError:
            self.ue.close_osc()
            print(
                "Received Timeout Error from OSC Communicator.",
                "Check if UE packaged game is running.",
            )
            raise SystemExit

        if resolution:
            self.ue.set_resolution(resolution)
            # NOTE: we need to wait for the resolution to change before sending another command
            # TODO: this should probably be done inside the Communicator
            sleep(1)

        # TODO: do we need to wait for the quality level to change?
        self.ue.set_quality(quality_level)

        # NOTE: we need to sleep after a reset to give UE time to update the scene
        self.reset()
        sleep(1)

        # We set the raycast length here to ensure the checked movement forward is being correctly compared.
        # TODO: do we need to wait for the raycast length to change?
        self.ue.set_raycast_length(self.raycast_length)

    def reset(self) -> None:
        """Resets agent to its initial position."""
        self.trial_num += 1
        self.navigator.reset()
        return self.ue.reset()

    def __getattr__(self, attr):
        """Dispatch unknown method calls to navigator object."""
        return getattr(self.navigator, attr)

    def sync_positions(self) -> None:
        """Move UE agent to match boxsim agent."""

        # Get z position from UE
        _, _, unreal_z = self.ue.get_location()

        # Get x, y position from boxsim
        x, y = self.navigator.position.xy()

        self.ue.set_location(x, y, unreal_z)

    def sync_box_position_to_unreal(self) -> None:
        """Move Boxsim agent to match Unreal Agent Position"""
        unrealX, unrealY, _ = self.ue.get_location()
        target = Pt(unrealX, unrealY)
        self.navigator.position = target

    def sync_rotation(self) -> None:
        """Sync UE agent location to box agent."""
        # Conversion from Box to unreal location is (180 - boxYaw) = unrealYaw
        unreal_yaw: float = degrees(self.navigator.rotation)
        self.ue.set_yaw(unreal_yaw)

    def take_action(self) -> tuple[Action, Action]:
        """Execute action in the navigator and in the UE agent.

        Returns:
            tuple[Action, Action]: return action taken and correct action.

        Raises:
            RuntimeError: If the action is not defined.
        """

        action_taken, correct_action, valid_movement = self.navigator.take_action()
        if self.dataset_path:
            self.save_image(correct_action)
        else:
            # A short delay to allow UE to render the scene after teleport
            sleep(0.1)

        if action_taken == Action.FORWARD:
            """_summary_ This method is first getting the length of the raycast between
            the robot and any obstacle that may be in front of it and adds 1 to its
            number of actions taken counter. If the raycast returns 0 this means there
            is nothing in front of the robot and it's movement forward is valid so it
            resets its actions taken to 0 and moves forward. However, if it is not valid
            we instead get the location at this point in time and if after 10 forward
            actions it is still unable to move forward, we compare it's position from
            these two separate points in time and if it's less than a certain threshold
            we'll set the stuck flag to True which will stop this trial early."""
            self.num_stationary_moves += 1
            if valid_movement is not False:
                raycast = self.ue.get_raycast_distance()

                # Checks and sets a flag if we are stuck unable to move forward.
                self.stuck = self.num_stationary_moves >= 10
                # Sometimes large increments will hit the wall the target is on
                if raycast == 0:
                    self.ue.move_forward(self.navigator.movement_increment)
                    self.sync_box_position_to_unreal()
                    self.num_stationary_moves = 0
            else:
                # In case an invalid move also causes to get stuck we are able to reset
                self.stuck = self.num_stationary_moves >= 10
        elif action_taken == Action.BACKWARD:
            self.ue.move_backward(self.navigator.movement_increment)
        elif action_taken == Action.ROTATE_LEFT:
            self.sync_rotation()
        elif action_taken == Action.ROTATE_RIGHT:
            self.sync_rotation()
        elif action_taken == Action.TELEPORT:
            self.sync_positions()
            self.sync_rotation()
        else:
            raise RuntimeError(f"Undefined action: {action_taken}")

        return action_taken, correct_action

    def save_image(self, action: Action) -> None:
        # # Rotations are swapped in UE
        # if action == Action.ROTATE_LEFT:
        #     action = Action.ROTATE_RIGHT
        # elif action == Action.ROTATE_RIGHT:
        #     action = Action.ROTATE_LEFT

        # Generate the next filename
        # Negative because unreal using a left-hand coordinate system
        angle = f"{-self.navigator.signed_angle_to_target:+.2f}".replace(".", "p")
        image_filepath = (
            f"{self.dataset_path}/"
            f"{self.trial_num:03}_{self.images_saved:06}_{angle}.{str(self.image_ext).lower()}"
        )

        # print(image_filepath)

        self.images_saved += 1

        # Let teleport complete, save the image, then wait for image save
        sleep(0.25)
        self.ue.save_image(image_filepath)
        # TODO: maybe loop until the image exists?
        sleep(0.25)
