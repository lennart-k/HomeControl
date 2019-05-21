"""The entrypoint for HomeControl"""

import subprocess
import shutil
from contextlib import suppress
import logging
import logging.config
import asyncio
import sys
import argparse
import os

import aiomonitor
import pkg_resources
import yaml

from homecontrol.core import Core
from homecontrol.dependencies.yaml_loader import YAMLLoader
from homecontrol.const import (
    MINIMUM_PYTHON_VERSION,
    EXIT_RESTART
)

LOGGER = logging.getLogger(__name__)


def get_arguments() -> dict:
    """Parse commandline arguments"""
    # pylint: disable=line-too-long
    parser = argparse.ArgumentParser(description="HomeControl")
    parser.add_argument(
        "-cfgfile", "-cf",
        default=os.path.expanduser("~/.homecontrol/config.yaml"),
        help="File storing the HomeControl configuration")
    parser.add_argument(
        "-pid-file",
        default=None,
        help=("Location of the PID file when running as a daemon."
              " Ensures that only one session is running"))
    parser.add_argument(
        "-clearport",
        action="store_true",
        default=None,
        help=("Frees the port for the API server using fuser."
              "Therefore only available on Linux"))
    parser.add_argument(
        "-verbose",
        action="store_true",
        default=None,
        help="Sets the loglevel for the logfile to INFO")
    parser.add_argument(
        "-nocolor",
        action="store_true",
        default=False,
        help="Disables colored console output")
    parser.add_argument(
        "-logfile",
        default=None,
        help="Logfile location")
    parser.add_argument(
        "-killprev", "-kp",
        action="store_true",
        default=None,
        help="Kills the previous HomeControl instance")
    if os.name == "posix":
        parser.add_argument(
            "-daemon", "-d",
            action="store_true",
            default=None,
            help="Start HomeControl as a daemon process [posix only]")

    return vars(parser.parse_args())


def get_config(path: str) -> dict:
    """
    Loads the config file from path
    If the config file does not exist it will ask the user
    if it should initialise with default configuration
    """
    if not os.path.isfile(path):
        LOGGER.critical("Config file does not exist: %s", path)
        create_new_config = input(
            (f"Shall a default config folder be created "
             f"at {os.path.dirname(path)}? [Y/n]"))

        if not create_new_config or create_new_config.lower()[0] == "y":
            LOGGER.info(
                "Installing the default configuration to %s",
                os.path.dirname(path))
            import homecontrol
            source = pkg_resources.resource_filename(
                homecontrol.__name__, "default_config")
            shutil.copytree(source, os.path.dirname(path))
            LOGGER.info("Running HomeControl with default config")
            return get_config(path=path)

        LOGGER.critical("Terminating")
        sys.exit(1)
    try:
        cfg = YAMLLoader.load(open(path))
    except yaml.YAMLError:
        LOGGER.error("Error in config file", exc_info=True)
        sys.exit(1)
    return cfg


def clear_port(port: int):
    """Clears a TCP port, only works on posix as it depends on fuser"""
    if os.name == "posix":
        subprocess.call(["/bin/fuser", "-k", "{port}/tcp".format(port=port)])


def validate_python_version():
    """Checks if the Python version is high enough"""
    if sys.version_info[:3] < MINIMUM_PYTHON_VERSION:
        LOGGER.critical(
            "The minimum Python version for HomeControl to work is %s",
            ".".join(MINIMUM_PYTHON_VERSION))
        sys.exit(1)


def run_homecontrol(config: dict, config_path: str, start_args: dict):
    """
    Runs HomeControl

    config: dict
        The loaded config file
    config_path: str
        Path to the config file
    start_args: dict
        The commandline arguments by ArgumentParser
    """
    loop = asyncio.get_event_loop()
    if os.name == "nt":
        def windows_wakeup():
            # This seems to be a workaround so that
            # SIGINT signals also work on Windows
            loop.call_later(0.1, windows_wakeup)
        # https://stackoverflow.com/questions/24774980/why-cant-i-catch-sigint-when-asyncio-event-loop-is-running/24775107#answer-24775107
        windows_wakeup()
    core = Core(
        cfg=config, cfg_path=config_path, loop=loop, start_args=start_args)
    with aiomonitor.Monitor(loop=loop, locals={"core": core, "loop": loop}):
        loop.call_soon(lambda: loop.create_task(core.bootstrap()))
        exit_return = loop.run_until_complete(core.block_until_stop())
    loop.stop()
    loop.close()
    if exit_return == EXIT_RESTART:
        LOGGER.warning("Restarting now%s", 4 * "\n")
        args = start_command()
        os.execv(args[0], args)
    elif start_args["pid_file"]:
        try:
            os.remove(start_args["pid_file"])
        except FileNotFoundError:
            pass


def start_command():
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
                  logfile: str = None
                  ):
    """
    Set up logging
    """
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

    fmt = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    console_datefmt = '%H:%M:%S'
    datefmt = '%Y-%m-%d %H:%M:%S'

    if color:
        with suppress(ImportError):
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


def main():
    """The main function"""
    validate_python_version()

    args = get_arguments()
    logfile = args["logfile"] or os.path.join(os.path.dirname(args["cfgfile"]),
                                              "homecontrol.log")

    cfg = get_config(args["cfgfile"])

    setup_logging(verbose=args["verbose"],
                  color=not args["nocolor"],
                  logfile=logfile)

    if not args["pid_file"]:
        args["pid_file"] = os.path.join(os.path.dirname(args["cfgfile"]),
                                        "homecontrol.pid")
    check_pid_file(args["pid_file"], kill=args["killprev"])

    if args.get("daemon", False):
        LOGGER.info("Running as a daemon")
        daemonize()

    if args["pid_file"]:
        try:
            with open(args["pid_file"], "w") as file:
                file.write(str(os.getpid()))
        except IOError:
            LOGGER.warning("Cannot write pid file %s", args["pid_file"])

    if args["clearport"] and cfg.get("http-server", {}).get("port"):
        clear_port(cfg["http-server"]["port"])

    run_homecontrol(config=cfg, config_path=args["cfgfile"], start_args=args)


main()
