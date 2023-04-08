# =================================================================
# =                 Author: Cameron Percival                      =
# =================================================================

import os
import sys
import shutil
import psutil
import datetime
from datetime import datetime, timedelta

# import time
import subprocess
import threading  # noqa
import gi
import requests
import time
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool

# import configparser
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa
from queue import Queue  # Multithreading the caching
from threading import Thread
from ProgressBarWindow import ProgressBarWindow

# =====================================================
#               Base Directory
# =====================================================

base_dir = os.path.dirname(os.path.realpath(__file__))

# =====================================================
#               Global Variables
# =====================================================
sudo_username = os.getlogin()
home = "/home/" + str(sudo_username)
packages = []
# =====================================================
#               Create log file
# =====================================================

log_dir = "/var/log/sofirem/"
sof_log_dir = "/var/log/sofirem/sof/"


def create_log(self):
    print("Making log in /var/log/sofirem")
    now = datetime.datetime.now()
    time = now.strftime("%Y-%m-%d-%H-%M-%S")
    destination = sof_log_dir + "sof-log-" + time
    command = "sudo pacman -Q > " + destination
    subprocess.call(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    # GLib.idle_add(show_in_app_notification, self, "Log file created")


# =====================================================
#               GLOBAL FUNCTIONS
# =====================================================


def _get_position(lists, value):
    data = [string for string in lists if value in string]
    position = lists.index(data[0])
    return position


def isfileStale(filepath, staleDays, staleHours, staleMinutes):
    # first, lets obtain the datetime of the day that we determine data to be "stale"
    now = datetime.now()
    # For the purposes of this, we are assuming that one would have the app open longer than 5 minutes if installing.
    staleDateTime = now - timedelta(
        days=staleDays, hours=staleHours, minutes=staleMinutes
    )
    # Check to see if the file path is in existence.
    if os.path.exists(filepath):
        # if the file exists, when was it made?
        fileCreated = datetime.fromtimestamp(os.path.getctime(filepath))
        # file is older than the time delta identified above
        if fileCreated < staleDateTime:
            return True
    return False


# =====================================================
#               PERMISSIONS
# =====================================================


def permissions(dst):
    try:
        groups = subprocess.run(
            ["sh", "-c", "id " + sudo_username],
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        for x in groups.stdout.decode().split(" "):
            if "gid" in x:
                g = x.split("(")[1]
                group = g.replace(")", "").strip()
        subprocess.call(["chown", "-R", sudo_username + ":" + group, dst], shell=False)

    except Exception as e:
        print(e)


# =====================================================
#               PACMAN SYNC PACKAGE DB
# =====================================================
def sync():
    try:
        sync_str = ["pacman", "-Sy"]

        print(
            "[INFO] %s Synchronising package databases"
            % datetime.now().strftime("%H:%M:%S")
        )

        # Pacman will not work if there is a lock file
        if os.path.exists("/var/lib/pacman/db.lck"):
            print("[ERROR] Pacman lock file found")
            print("[ERROR] Sync failed")
            sys.exit(1)
        else:

            process_sync = subprocess.run(
                sync_str,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )

        return process_sync.returncode
    except Exception as e:
        print("Exception in sync(): %s" % e)


# =====================================================
#               APP INSTALLATION
# =====================================================
def install(queue):

    pkg = queue.get()

    try:
        if not waitForPacmanLockFile() and pkg is not None:
            path = base_dir + "/cache/installed.lst"

            inst_str = ["pacman", "-S", pkg, "--needed", "--noconfirm"]

            print(
                "[INFO] %s Installing package %s: "
                % (datetime.now().strftime("%H:%M:%S"), pkg)
            )

            process_pkg_inst = subprocess.run(
                inst_str,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )

            if process_pkg_inst.returncode == 0:
                print("[INFO] Package install completed")
                print(
                    "---------------------------------------------------------------------------"
                )
            else:
                print("[ERROR] Package install failed")
                print(
                    "---------------------------------------------------------------------------"
                )
                raise SystemError("Pacman failed to install package = %s" % pkg)

    except Exception as e:
        print("Exception in install(): %s" % e)
    except SystemError as s:
        print("SystemError in install(): %s" % s)
    finally:
        queue.task_done()


# =====================================================
#               APP UNINSTALLATION
# =====================================================
def uninstall(queue):

    pkg = queue.get()

    try:
        if not waitForPacmanLockFile() and pkg is not None:
            if checkPackageInstalled(pkg):
                path = base_dir + "/cache/installed.lst"
                uninst_str = ["pacman", "-Rs", pkg, "--noconfirm"]

                print(
                    "[INFO] %s Removing package : %s"
                    % (datetime.now().strftime("%H:%M:%S"), pkg)
                )

                process_pkg_rem = subprocess.run(
                    uninst_str,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=60,
                )

                if process_pkg_rem.returncode == 0:
                    print(
                        "[INFO] %s Package removal completed",
                        datetime.now().strftime("%H:%M:%S"),
                    )
                    print(
                        "---------------------------------------------------------------------------"
                    )
                else:
                    print(
                        "[ERROR] %s Package removal failed",
                        datetime.now().strftime("%H:%M:%S"),
                    )
                    print(
                        "---------------------------------------------------------------------------"
                    )
                    raise SystemError("Pacman failed to remove package = %s" % pkg)

    except Exception as e:
        print("Exception in uninstall(): %s" % e)
    except SystemError as s:
        print("SystemError in uninstall(): %s" % s)
    finally:
        queue.task_done()


# =====================================================
#               APP QUERY
# =====================================================


def get_current_installed(path):
    # query_str = "pacman -Q > " + path
    query_str = ["pacman", "-Q"]
    # run the query - using Popen because it actually suits this use case a bit better.

    subprocess_query = subprocess.Popen(query_str, shell=False, stdout=subprocess.PIPE)

    out, err = subprocess_query.communicate()

    # added validation on process result
    if subprocess_query.returncode == 0:
        file = open(path, "w")
        for line in out.decode("utf-8"):
            file.write(line)
        file.close()
    else:
        print(
            "[ERROR] %s Failed to run %s"
            % (datetime.now().strftime("%H:%M:%S"), query_str)
        )


def query_pkg(package):
    try:
        package = package.strip()
        path = base_dir + "/cache/installed.lst"

        if os.path.exists(path):
            if isfileStale(path, 0, 0, 30):
                get_current_installed(path)
        # file does NOT exist;
        else:
            get_current_installed(path)
        # then, open the resulting list in read mode
        with open(path, "r") as f:

            # first we need to strip the new line escape sequence to ensure we don't get incorrect outcome
            pkg = package.strip("\n")

            # If the pkg name appears in the list, then it is installed
            for line in f:
                installed = line.split(" ")
                # We only compare against the name of the package, NOT the version number.
                if pkg == installed[0]:
                    # file.close()
                    return True
            # We will only hit here, if the pkg does not match anything in the file.
            # file.close()
        return False
    except Exception as e:
        print("Exception in query_pkg(): %s " % e)


# =====================================================
#        PACKAGE DESCRIPTION CACHE AND SEARCH
# =====================================================


def cache(package, path):
    try:
        # first we need to strip the new line escape sequence to ensure we don't get incorrect outcome
        pkg = package.strip()
        # create the query
        query_str = ["pacman", "-Si", pkg, " --noconfirm"]

        # run the query - using Popen because it actually suits this use case a bit better.

        process = subprocess.Popen(
            query_str, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        out, err = process.communicate()

        # validate the process result
        if process.returncode == 0:
            # out, err = process.communicate()

            output = out.decode("utf-8")

            if len(output) > 0:
                split = output.splitlines()

                # Currently the output of the pacman command above always puts the description on the 4th line.
                desc = str(split[3])
                # Ok, so this is a little fancy: there is formatting from the output which we wish to ignore (ends at 19th character)
                # and there is a remenant of it as the last character - usually a single or double quotation mark, which we also need to ignore
                description = desc[18:]
                # writing to a caching file with filename matching the package name
                filename = base_dir + "/cache/" + pkg

                file = open(filename, "w")
                file.write(description)
                file.close()

                return description
        return "No Description Found"
    except Exception as e:
        print("Exception in cache(): %s " % e)


# Creating an over-load so that we can use the same function, with slightly different code to get the results we need
def cache_btn(path, progressbar):
    fraction = 1 / len(packages)
    # Non Multithreaded version.
    for pkg in packages:
        cache(pkg, base_dir + path)
        progressbar.timeout_id = GLib.timeout_add(50, progressbar.update, fraction)

    # This will need to be coded to be running multiple processes eventually, since it will be manually invoked.
    # process the file list
    # for each file in the list, open the file
    # process the file ignoring what is not what we need
    # for each file line processed, we need to invoke the cache function that is not over-ridden.


def file_lookup(package, path):
    # first we need to strip the new line escape sequence to ensure we don't get incorrect outcome
    pkg = package.strip("\n")
    output = ""
    filename = path + pkg
    file = open(filename, "r")
    output = file.read()
    file.close()
    if len(output) > 0:
        return output
    return "No Description Found"


def obtain_pkg_description(package):
    # This is a pretty simple function now, decide how to get the information, then get it.
    # processing variables.
    output = ""
    path = base_dir + "/cache/"

    # First we need to determine whether to pull from cache or pacman.
    if os.path.exists(path + package.strip("\n")):
        output = file_lookup(package, path)

    # file doesn't exist, so create a blank copy
    else:
        output = cache(package, path)
    # Add the package in question to the global variable, in case recache is needed
    packages.append(package)
    return output


def restart_program():
    os.unlink("/tmp/sofirem.lock")
    python = sys.executable
    os.execl(python, python, *sys.argv)


def check_github(yaml_files):
    # This is the link to the location where the .yaml files are kept in the github
    path = base_dir + "/cache/"
    link = "https://github.com/arcolinux/arcob-calamares-config-awesome/tree/master/calamares/modules/"
    urls = []
    fns = []
    for file in yaml_files:
        if isfileStale(path + file, 14, 0, 0):
            fns.append(path + file)
            urls.append(link + file)
    if len(fns) > 0 & len(urls) > 0:
        inputs = zip(urls, fns)
        download_parallel(inputs)


def download_url(args):
    t0 = time.time()
    url, fn = args[0], args[1]
    try:
        r = requests.get(url)
        with open(fn, "wb") as f:
            f.write(r.content)
        return (url, time.time() - t0)
    except Exception as e:
        print("Exception in download_url():", e)


def download_parallel(args):
    cpus = cpu_count()
    results = ThreadPool(cpus - 1).imap_unordered(download_url, args)
    for result in results:
        print("url:", result[0], "time (s):", result[1])


# =====================================================
#               CHECK RUNNING PROCESS
# =====================================================


def checkIfProcessRunning(processName):
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=["pid", "name", "create_time"])
            if processName == pinfo["pid"]:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


# =====================================================
#               CHECK PACMAN LOCK FILE
# =====================================================


def waitForPacmanLockFile():
    while True:
        if not os.path.exists("/var/lib/pacman/db.lck"):
            return False
        else:
            time.sleep(5)


# =====================================================
#               CHECK PACKAGE INSTALLED
# =====================================================


def checkPackageInstalled(pkg):
    try:
        query_str = ["pacman", "-Q", pkg]

        process_query = subprocess.run(
            query_str,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )

        if process_query.returncode == 0:
            return True
        else:
            return False
    except Exception as e:
        print("Exception in checkPackageInstalled(): %s", e)


#######ANYTHING UNDER THIS LINE IS CURRENTLY UNUSED!
