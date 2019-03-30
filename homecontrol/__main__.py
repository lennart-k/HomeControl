import traceback
from core import Core
import asyncio
import aiomonitor
from functools import partial
from dependencies.yaml_loader import YAMLLoader
import yaml
import sys
import argparse
import os
import subprocess
from const import (
    MINIMUM_PYTHON_VERSION,
    EXIT_RESTART
)

def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HomeControl")

    parser.add_argument("-cfgfile", "-cf", default="config.yaml", help="File storing the HomeControl configuration")
    parser.add_argument("-pid-file", default=None, help="Location of the PID file when running as a daemon. Ensures that only one session is running")
    parser.add_argument("-clearport", action="store_true", default=None, help="Frees the port for the API server using fuser. Therefore only available on Linux")
    parser.add_argument("-verbose", action="store_true", default=None)
    if os.name == "posix":
        parser.add_argument("-daemon", "-d", action="store_true", default=None, help="Start HomeControl as a daemon process [posix only]")
    
    return vars(parser.parse_args())

def get_config(path: str) -> dict:
    if not os.path.isfile(path):
        print("Config file does not exist!")
        sys.exit(1)
    try:
        cfg = YAMLLoader.load(open(path))
    except yaml.YAMLError as e:
        print("Error in config file")
        traceback.print_exc()
        sys.exit(1)
    return cfg

def clear_port(port: int):
    if os.name == "posix":
        subprocess.call(["fuser", "-k", "{port}/tcp".format(port=port)])


def validate_python_version():
    if sys.version_info[:3] < MINIMUM_PYTHON_VERSION:
        print("The minimum Python version for HomeControl to work is {}.{}.{}".format(*MINIMUM_PYTHON_VERSION))
        sys.exit(1)


def run_homecontrol(config: dict, start_args: dict):
    loop = asyncio.get_event_loop()
    with aiomonitor.Monitor(loop=loop):
        core = Core(cfg=config, loop=loop, start_args=start_args)
        loop.call_soon(partial(loop.create_task, core.bootstrap()))
        exit_return = loop.run_until_complete(core.block_until_stop())
    loop.stop()
    loop.close()
    if exit_return == EXIT_RESTART:
        print("RESTARTING NOW"+4*"\n")
        args = start_command()
        os.execv(args[0], args)
    elif start_args["pid_file"]:
        try:
            os.remove(start_args["pid_file"])
        except FileNotFoundError:
            pass

def start_command():
    """
    Returns a command to re-execute HomeControl with the same parameters except the daemon parameter
    """
    if os.path.basename(sys.argv[0]) == "__main__.py" or (os.path.split(sys.argv[0])[-1] == "homecontrol" and os.path.isdir(sys.argv[0])):
        os.environ["PYTHONPATH"] = os.path.dirname(os.path.dirname(sys.argv[0]))
        return [sys.executable] + [arg for arg in sys.argv if not arg in ("-d", "-daemon")]

    return [arg for arg in sys.argv if not arg in ("-d", "-daemon")]


def daemonize() -> None:
    """Move current process to daemon process."""
    # Create first fork
    pid = os.fork()
    if pid > 0:
        sys.exit(0)

    os.setsid()
    print("Process ID:", os.getpid())

    # redirect standard file descriptors to devnull
    infd = open(os.devnull, 'r')
    outfd = open(os.devnull, 'a+')
    sys.stdout.flush()
    sys.stderr.flush()
    os.dup2(infd.fileno(), sys.stdin.fileno())
    os.dup2(outfd.fileno(), sys.stdout.fileno())
    os.dup2(outfd.fileno(), sys.stderr.fileno())

def check_pid_file(pid_file: str) -> None:
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

    try:
        os.kill(pid, 0)
    except OSError:
        # PID does not exist. Last session not closed properly
        return

    print("FATAL ERROR: HomeControl is already running on pid", pid)
    sys.exit(1)


def main():
    validate_python_version()

    args = get_arguments()
    cfg = get_config(args["cfgfile"])

    if args["pid_file"]:
        check_pid_file(args["pid_file"])

    if args.get("daemon", False):
        print("Running as a daemon")
        daemonize()

    if args["pid_file"]:
        try:
            with open(args["pid_file"], "w") as file:
                file.write(str(os.getpid()))
        except IOError:
            print("Error: Cannot write pid file {}".format(args["pid_file"]))

    if args["clearport"]:
        clear_port(cfg["api-server"]["port"])

    run_homecontrol(config=cfg, start_args=args)

start_command()

main()
