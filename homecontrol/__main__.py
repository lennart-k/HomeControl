"""The entrypoint for HomeControl"""

import argparse
import asyncio
import logging
import logging.config
import os
import shutil
import subprocess
import sys
from contextlib import suppress
from typing import List, Optional

import aiomonitor
import pkg_resources
import yaml

from homecontrol.const import EXIT_RESTART, MINIMUM_PYTHON_VERSION
from homecontrol.core import Core
from homecontrol.dependencies.yaml_loader import YAMLLoader

CONFIG_FILE_NAME = "configuration.yaml"

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Returns the ArgumentParser"""
    # pylint: disable=line-too-long
    parser = argparse.ArgumentParser(description="HomeControl")
    parser.add_argument(
        "--cfgdir", "-cd",
        default=os.path.expanduser("~/.homecontrol/"),
        help="Directory storing the HomeControl configuration")
    parser.add_argument(
        "--pid-file",
        default=None,
        help=("Location of the PID file."
              "Ensures that only one session is running. "
              "Defaults to the configuration path"))
    parser.add_argument(
        "--clearport",
        action="store_true",
        default=None,
        help=("Frees the port for the API server using fuser. "
              "Therefore only available on Linux"))
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=None,
        help="Sets the loglevel for the logfile to INFO")
    parser.add_argument(
        "--nocolor",
        action="store_true",
        default=False,
        help="Disables colored console output")
    parser.add_argument(
        "--logfile",
        default=None,
        help="Logfile location")
    parser.add_argument(
        "--killprev", "-kp",
        action="store_true",
        default=False,
        help="Kills the previous HomeControl instance")
    parser.add_argument(
        "--skip-pip", "-sp",
        action="store_true",
        default=False,
        help="Skips the installation of configured pip requirements")
    if os.name == "posix":
        parser.add_argument(
            "--daemon", "-d",
            action="store_true",
            default=None,
            help="Start HomeControl as a daemon process [posix only]")
    return parser.parse_args()


def copy_folder(src: str, dest: str, merge_folders: bool = False) -> None:
    """
    Copies a folder to another path overwriting files
    and merging folders
    """
    for src_root, dirs, files in os.walk(src, followlinks=True):
        dest_root = src_root.replace(src, dest, 1)
        if not os.path.isdir(dest_root):
            os.mkdir(dest_root)

        for file in set(files) & set(os.listdir(dest_root)):
            if os.path.isfile(os.path.join(dest_root, file)):
                os.remove(os.path.join(dest_root, file))
        if not merge_folders:
            for folder in os.listdir(dest_root):
                if os.path.isdir(os.path.join(dest_root, folder)):
                    shutil.rmtree(os.path.join(dest_root, folder))

        for file in files:
            shutil.copy(
                os.path.join(src_root, file),
                os.path.join(dest_root, file))


def get_config(directory: str) -> dict:
    """
    Loads the config from path
    If the config file does not exist it will ask the user
    if it should initialise with default configuration
    """
    file = os.path.join(directory, CONFIG_FILE_NAME)
    if not os.path.isfile(file):
        LOGGER.warning("Config file does not exist: %s", file)
        # Don't ask if HomeControl is not interactive.
        # It's quite likely a Docker container or daemon
        create_new_config = not sys.stdout.isatty()

        if not create_new_config:
            user_choice = input(
                (f"Shall a default config folder be created "
                 f"at {directory}? [Y/n]"))
            create_new_config = (not user_choice
                                 or create_new_config.lower()[0] == "y")

        if create_new_config:
            LOGGER.info(
                "Installing the default configuration to %s",
                directory)
            # pylint: disable=import-outside-toplevel
            from homecontrol import __name__ as package_name
            source = pkg_resources.resource_filename(
                package_name, "default_config")
            copy_folder(source, directory)
            LOGGER.info("Running HomeControl with default config")
            return get_config(directory)

        LOGGER.critical("Terminating")
        sys.exit(1)
    try:
        cfg: dict = YAMLLoader.load(open(file), cfg_folder=directory)
    except yaml.YAMLError:
        LOGGER.error("Error in config file", exc_info=True)
        sys.exit(1)
    return cfg


def clear_port(port: int) -> None:
    """Clears a TCP port, only works on posix as it depends on fuser"""
    if os.name == "posix":
        subprocess.call(["/bin/fuser", "-k", "{port}/tcp".format(port=port)])


def validate_python_version() -> None:
    """Checks if the Python version is high enough"""
    if sys.version_info[:3] < MINIMUM_PYTHON_VERSION:
        LOGGER.critical(
            "The minimum Python version for HomeControl to work is %s",
            ".".join(map(str, MINIMUM_PYTHON_VERSION)))
        sys.exit(1)


def run_homecontrol(
        config: dict, config_file: str, start_args: argparse.Namespace):
    """
    Runs HomeControl
    """
    loop = asyncio.get_event_loop()
    if os.name == "nt":
        def windows_wakeup() -> None:
            # This seems to be a workaround so that
            # SIGINT signals also work on Windows
            loop.call_later(0.1, windows_wakeup)
        # https://stackoverflow.com/questions/24774980/why-cant-i-catch-sigint-when-asyncio-event-loop-is-running/24775107#answer-24775107
        windows_wakeup()
    core = Core(cfg=config,
                cfg_file=config_file,
                loop=loop,
                start_args=start_args)

    with aiomonitor.Monitor(loop=loop, locals={"core": core, "loop": loop}):
        loop.call_soon(lambda: loop.create_task(core.bootstrap()))
        exit_return = loop.run_until_complete(core.block_until_stop())

    loop.close()

    if exit_return == EXIT_RESTART:
        LOGGER.warning("Restarting now%s", 4 * "\n")
        args = start_command()
        os.execv(args[0], args)
    elif start_args.pid_file:
        with suppress(FileNotFoundError):
            os.remove(start_args.pid_file)
        sys.exit()


def start_command() -> List[str]:
    """
    Returns a command to re-execute HomeControlwith the same parameters
    except the daemon parameter
    """
    # pylint: disable=line-too-long
    if (os.path.basename(sys.argv[0]) == "__main__.py"
            or (os.path.split(sys.argv[0])[-1] == "homecontrol"
                and os.path.isdir(sys.argv[0]))):

        os.environ["PYTHONPATH"] = os.path.dirname(
            os.path.dirname(sys.argv[0]))

        return ([sys.executable]
                + [arg for arg in sys.argv if arg not in ("-d", "-daemon")])

    return [arg for arg in sys.argv if arg not in ("-d", "-daemon")]


def daemonize() -> None:
    """Move current process to a daemon process."""
    # Create first fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    os.setsid()
    LOGGER.info("Process ID: %s", os.getpid())

    # redirect standard file descriptors to devnull
    infd = open(os.devnull, 'r')
    outfd = open(os.devnull, 'a+')
    sys.stdout.flush()
    sys.stderr.flush()
    os.dup2(infd.fileno(), sys.stdin.fileno())
    os.dup2(outfd.fileno(), sys.stdout.fileno())
    os.dup2(outfd.fileno(), sys.stderr.fileno())


def check_pid_file(pid_file: str, kill: bool = False) -> None:
    """Checks if another instance of HomeControl is already running"""
    if not os.path.isfile(pid_file):
        # No pid file existing
        return
    with open(pid_file) as file:
        line = file.readline()
        if line.isdigit():
            pid = int(line)
        else:
            return
    if pid == os.getpid():
        # Just restarted
        return
    if kill:
        try:
            os.kill(pid, 9)
            LOGGER.info("Killing previous instance of HomeControl")
            while True:
                os.kill(pid, 0)
        except OSError:
            # Process dead
            return
    try:
        os.kill(pid, 0)
    except OSError:
        # PID does not exist. Last session not closed properly
        return

    LOGGER.error("HomeControl is already running on pid %s", pid)
    sys.exit(1)


def setup_logging(verbose: bool = False,
                  color: bool = True,
                  logfile: Optional[str] = None
                  ) -> None:
    """
    Set up logging
    """
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

    fmt = "%(asctime)s %(levelname)s (%(threadName)s)[%(name)s] %(message)s"
    console_datefmt = '%H:%M:%S'
    datefmt = '%Y-%m-%d %H:%M:%S'

    if color:
        # pylint: disable=import-outside-toplevel
        from colorlog import ColoredFormatter

        logging.basicConfig(level=logging.INFO)

        colorfmt = "%(log_color)s{}%(reset)s".format(fmt)
        logging.getLogger().handlers[0].setFormatter(ColoredFormatter(
            colorfmt,
            datefmt=console_datefmt,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'white',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red',
            }
        ))

    if logfile:
        file_handler = logging.FileHandler(logfile, mode="w")
        file_handler.setLevel(logging.INFO if verbose else logging.WARNING)
        file_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        logging.getLogger().addHandler(file_handler)


def set_loop_policy() -> None:
    """
    Try to use a ProactorEventLoop on Windows and uvloop elsewhere
    """

    if (sys.platform == "win32"
            and hasattr(asyncio, "WindowsProactorEventLoopPolicy")):
        asyncio.set_event_loop_policy(
            asyncio.WindowsProactorEventLoopPolicy())

    else:
        with suppress(ImportError):
            # pylint: disable=import-outside-toplevel
            import uvloop
            asyncio.set_event_loop_policy(
                uvloop.EventLoopPolicy())


def main() -> None:
    """The main function"""
    validate_python_version()

    args = parse_args()
    logfile = args.logfile or os.path.join(args.cfgdir, "homecontrol.log")

    cfg = get_config(args.cfgdir)
    cfg_file = os.path.join(args.cfgdir, CONFIG_FILE_NAME)

    setup_logging(verbose=args.verbose,
                  color=not args.nocolor,
                  logfile=logfile)

    if not args.pid_file:
        args.pid_file = os.path.join(args.cfgdir, "homecontrol.pid")
    check_pid_file(args.pid_file, kill=args.killprev)

    if not args.skip_pip and "pip-requirements" in cfg:
        # pylint: disable=import-outside-toplevel
        from homecontrol.dependencies.ensure_pip_requirements import (
            ensure_packages
        )
        ensure_packages(cfg["pip-requirements"])

    if args.daemon:
        LOGGER.info("Running as a daemon")
        daemonize()

    if args.pid_file:
        try:
            with open(args.pid_file, "w") as file:
                file.write(str(os.getpid()))
        except IOError:
            LOGGER.warning("Cannot write pid file %s", args.pid_file)

    if args.clearport and cfg.get("http-server", {}).get("port"):
        clear_port(cfg["http-server"]["port"])

    set_loop_policy()

    run_homecontrol(config=cfg, config_file=cfg_file, start_args=args)


if __name__ == "__main__":
    main()
