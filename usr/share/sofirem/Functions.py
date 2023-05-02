# =================================================================
# =                 Author: Cameron Percival                      =
# =================================================================

import os
import sys
import shutil
import psutil
import time
import datetime
from datetime import datetime, timedelta
import subprocess
import threading  # noqa
import gi
import requests
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool

# import configparser
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa
from queue import Queue  # Multithreading the caching
from threading import Thread
from ProgressBarWindow import ProgressBarWindow
from sofirem import launchtime
from Package import Package
from distro import id

# =====================================================
#               Base Directory
# =====================================================

base_dir = os.path.dirname(os.path.realpath(__file__))

# =====================================================
#               Global Variables
# =====================================================
sudo_username = os.getlogin()
home = "/home/" + str(sudo_username)
path_dir_cache = base_dir + "/cache/"
packages = []
debug = False
distr = id()
pacman_lock_file = "/var/lib/pacman/db.lck"
# this timeout is only for the pacman lock file, install/uninstall processes
# 10m timeout
process_timeout = 600

arcolinux_mirrorlist = "/etc/pacman.d/arcolinux-mirrorlist"
pacman_conf = "/etc/pacman.conf"

atestrepo = "#[arcolinux_repo_testing]\n\
#SigLevel = Optional TrustedOnly\n\
#Include = /etc/pacman.d/arcolinux-mirrorlist"

arepo = "[arcolinux_repo]\n\
SigLevel = Optional TrustedOnly\n\
Include = /etc/pacman.d/arcolinux-mirrorlist"

a3prepo = "[arcolinux_repo_3party]\n\
SigLevel = Optional TrustedOnly\n\
Include = /etc/pacman.d/arcolinux-mirrorlist"

axlrepo = "[arcolinux_repo_xlarge]\n\
SigLevel = Optional TrustedOnly\n\
Include = /etc/pacman.d/arcolinux-mirrorlist"

# =====================================================
#               BEGIN GLOBAL FUNCTIONS
# =====================================================


# get position in list
def get_position(lists, value):
    data = [string for string in lists if value in string]
    if len(data) != 0:
        position = lists.index(data[0])
        return position
    return 0


# =====================================================
#               END GLOBAL FUNCTIONS
# =====================================================

# =====================================================
#               Create log file
# =====================================================

log_dir = "/var/log/sofirem/"
sof_log_dir = "/var/log/sofirem/software/"
act_log_dir = "/var/log/sofirem/actions/"


def create_packages_log():
    now = datetime.now().strftime("%H:%M:%S")
    print("[INFO] " + now + " Creating a log file in /var/log/sofirem/software")
    destination = sof_log_dir + "software-log-" + launchtime
    command = "sudo pacman -Q > " + destination
    subprocess.call(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    create_actions_log(
        launchtime,
        "[INFO] %s Creating a log file in /var/log/sofirem/software " % now + "\n",
    )
    # GLib.idle_add(
    #     show_in_app_notification, "is already installed - nothing to do", "test"
    # )


def create_actions_log(launchtime, message):
    if not os.path.exists(act_log_dir + launchtime):
        try:
            with open(act_log_dir + launchtime, "x", encoding="utf8") as f:
                f.close
        except Exception as error:
            print(error)

    if os.path.exists(act_log_dir + launchtime):
        try:
            with open(act_log_dir + launchtime, "a", encoding="utf-8") as f:
                f.write(message)
                f.close()
        except Exception as error:
            print(error)


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
def sync(self):
    try:
        sync_str = ["pacman", "-Sy"]
        now = datetime.now().strftime("%H:%M:%S")
        print("[INFO] %s Synchronising package databases" % now)
        create_actions_log(
            launchtime,
            "[INFO] %s Synchronising package databases " % now + "\n",
        )

        # Pacman will not work if there is a lock file
        if os.path.exists(pacman_lock_file):
            print("[ERROR] %s Pacman lock file found: %s" % (now, pacman_lock_file))
            print("[ERROR] %s Synchronisation failed" % now)

            msg_dialog = message_dialog(
                self,
                "pacman -Sy",
                "Pacman database synchronisation failed",
                "Pacman lock file found inside %s" % pacman_lock_file,
                Gtk.MessageType.ERROR,
            )

            msg_dialog.run()
            msg_dialog.hide()
            sys.exit(1)
        else:
            process_sync = subprocess.run(
                sync_str,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120,
            )

        return process_sync.returncode
    except Exception as e:
        print("Exception in sync(): %s" % e)


# =====================================================
#               APP INSTALLATION
# =====================================================
def install(self):
    pkg, action, widget = self.pkg_queue.get()
    install_state = {}
    install_state[pkg] = "QUEUED"
    thread_alive = False
    lockfile_thread = "thread_waitForPacmanLockFile"

    # check the pacman lock file thread isn't already running
    for thread in threading.enumerate():
        if thread.name == lockfile_thread and thread.is_alive():
            thread_alive = True
            break

    if thread_alive == False:
        print(
            "[DEBUG] %s Starting waitForPacmanLockFile thread"
            % datetime.now().strftime("%H:%M:%S")
        )

        th = Thread(
            name=lockfile_thread,
            target=waitForPacmanLockFile,
        )

        th.start()
    else:
        print(
            "[DEBUG] %s waitForPacmanLockFile thread is already running"
            % datetime.now().strftime("%H:%M:%S")
        )

        print(
            "[INFO] %s Another Package install is in progress"
            % datetime.now().strftime("%H:%M:%S")
        )

    try:
        print(
            "[DEBUG] %s PkgInstallThread: Package install queue size : %s"
            % (datetime.now().strftime("%H:%M:%S"), len(self.pkg_inst_deque))
        )

        if len(self.pkg_inst_deque) == 5:
            print(
                "[WARN] %s Package install queue size hit limit of 5"
                % (datetime.now().strftime("%H:%M:%S"))
            )
            widget.set_state(False)

            msg_dialog = message_dialog(
                self,
                "Please wait until previous Pacman transactions are completed",
                "There are a maximum of 5 packages added to the queue",
                "Waiting for previous Pacman transactions to complete",
                Gtk.MessageType.WARNING,
            )

            msg_dialog.run()
            msg_dialog.hide()
        else:
            """
            Running waitForPacmanLockFile() inside a separate thread
            will not add further packages to the queue
            """
            if action == "install":
                path = base_dir + "/cache/installed.lst"

                inst_str = ["pacman", "-S", pkg, "--needed", "--noconfirm"]

                now = datetime.now().strftime("%H:%M:%S")
                print("[INFO] %s Installing package %s " % (now, pkg))
                create_actions_log(
                    launchtime, "[INFO] " + now + " Installing package " + pkg + "\n"
                )

                process_pkg_inst = subprocess.Popen(
                    inst_str,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )

                out, err = process_pkg_inst.communicate(timeout=process_timeout)

                if process_pkg_inst.returncode == 0:
                    # activate switch widget, install ok
                    widget.set_state(True)

                    get_current_installed()
                    install_state[pkg] = "INSTALLED"

                    print(
                        "[INFO] %s Package install : %s status = completed"
                        % (datetime.now().strftime("%H:%M:%S"), pkg)
                    )
                    print(
                        "---------------------------------------------------------------------------"
                    )

                    GLib.idle_add(
                        show_in_app_notification,
                        self,
                        "Package: %s installed" % pkg,
                        False,
                    )

                else:
                    # deactivate switch widget, install failed
                    widget.set_state(False)

                    get_current_installed()
                    print(
                        "[ERROR] %s Package install : %s status = failed"
                        % (datetime.now().strftime("%H:%M:%S"), pkg)
                    )
                    if out:
                        out = out.decode("utf-8")
                        install_state[pkg] = out
                    print(
                        "---------------------------------------------------------------------------"
                    )
                    if (
                        "error: could not lock database: File exists"
                        not in install_state[pkg]
                    ):
                        GLib.idle_add(
                            show_in_app_notification,
                            self,
                            "Package install failed for: %s" % pkg,
                            True,
                        )
                    raise SystemError("Pacman failed to install package = %s" % pkg)
    except TimeoutError as t:
        print("TimeoutError in install(): %s" % t)
        process_pkg_inst.terminate()
    except SystemError as s:
        print("SystemError in install(): %s" % s)
        process_pkg_inst.terminate()
    except Exception as e:
        print("Exception in install(): %s" % e)
        process_pkg_inst.terminate()
    finally:
        # Now check install_state for any packages which failed to install
        # display dependencies notification to user here

        # remove the package from the deque
        self.pkg_inst_deque.remove(pkg)

        if (
            install_state[pkg] != None
            and install_state[pkg] != "INSTALLED"
            and install_state[pkg] != "QUEUED"
            and len(install_state[pkg]) > 0
        ):
            print(
                "[ERROR] %s Package install failed : %s"
                % (datetime.now().strftime("%H:%M:%S"), install_state[pkg])
            )

            proc = get_pacman_process()

            if proc:
                print(
                    "[DEBUG] %s Pacman status = %s"
                    % (datetime.now().strftime("%H:%M:%S"), str(proc))
                )

                msg_dialog = message_dialog(
                    self,
                    "Error installing package",
                    "Failed to install package: %s" % pkg,
                    str(install_state[pkg])
                    + "\n"
                    + "Pacman process currently running: %s " % proc,
                    Gtk.MessageType.ERROR,
                )
            else:
                msg_dialog = message_dialog(
                    self,
                    "Error installing package",
                    "Failed to install package: %s" % pkg,
                    str(install_state[pkg]),
                    Gtk.MessageType.ERROR,
                )

            msg_dialog.run()
            msg_dialog.hide()

        self.pkg_queue.task_done()


# =====================================================
#               APP UNINSTALLATION
# =====================================================
def uninstall(self):
    pkg, action, widget = self.pkg_queue.get()
    uninstall_state = {}
    uninstall_state[pkg] = "QUEUED"

    try:
        if action == "uninstall":
            # peek at the install queue

            # do not allow a package to be uninstalled while it is being installed
            if pkg in self.pkg_inst_deque:
                widget.set_state(True)
                msg_dialog = message_dialog(
                    self,
                    "Error removing package",
                    "Package: %s is installing / queued to be installed" % pkg,
                    "Cannot remove a package which is installing",
                    Gtk.MessageType.ERROR,
                )

                msg_dialog.run()
                msg_dialog.hide()
            else:
                path = base_dir + "/cache/installed.lst"
                uninst_str = ["pacman", "-Rs", pkg, "--noconfirm"]

                now = datetime.now().strftime("%H:%M:%S")
                print("[INFO] %s Removing package : %s" % (now, pkg))
                create_actions_log(
                    launchtime, "[INFO] " + now + " Removing package " + pkg + "\n"
                )

                process_pkg_rem = subprocess.Popen(
                    uninst_str,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )

                out, err = process_pkg_rem.communicate(timeout=process_timeout)

                if process_pkg_rem.returncode == 0:
                    # deactivate switch widget, uninstall ok
                    widget.set_state(False)

                    get_current_installed()
                    uninstall_state[pkg] = "REMOVED"
                    print(
                        "[INFO] %s Package removal : %s status = completed"
                        % (datetime.now().strftime("%H:%M:%S"), pkg)
                    )
                    print(
                        "---------------------------------------------------------------------------"
                    )

                    GLib.idle_add(
                        show_in_app_notification,
                        self,
                        "Package: %s removed" % pkg,
                        False,
                    )

                else:
                    if out:
                        out = out.decode("utf-8")
                        if len(out) > 0:
                            uninstall_state[pkg] = out.splitlines()
                            get_current_installed()
                            if (
                                "error: target not found: %s" % pkg
                                in uninstall_state[pkg]
                            ):
                                widget.set_state(False)
                                uninstall_state[pkg] = "REMOVED"
                                print(
                                    "[INFO] %s Package removal : %s status = completed"
                                    % (datetime.now().strftime("%H:%M:%S"), pkg)
                                )
                                GLib.idle_add(
                                    show_in_app_notification,
                                    self,
                                    "Package: %s removed" % pkg,
                                    False,
                                )
                            else:
                                # activate switch widget, uninstall failed
                                widget.set_state(True)

                                print(
                                    "[ERROR] %s Package removal : %s status = failed"
                                    % (datetime.now().strftime("%H:%M:%S"), pkg)
                                )
                                if (
                                    "error: could not lock database: File exists"
                                    not in uninstall_state[pkg]
                                ):
                                    GLib.idle_add(
                                        show_in_app_notification,
                                        self,
                                        "Package removal failed for: %s" % pkg,
                                        True,
                                    )

                                raise SystemError(
                                    "Pacman failed to remove package = %s" % pkg
                                )
                        else:
                            # the package was already removed as a dependency from another package
                            # deactivate the widget
                            widget.set_state(False)

                print(
                    "---------------------------------------------------------------------------"
                )
    except TimeoutError as t:
        print("TimeoutError in install(): %s" % t)
        process_pkg_rem.terminate()
    except SystemError as s:
        print("SystemError in uninstall(): %s" % s)
        process_pkg_rem.terminate()
    except Exception as e:
        print("Exception in uninstall(): %s" % e)
        process_pkg_rem.terminate()

    finally:
        # Now check uninstall_state for any packages which failed to uninstall
        # display dependencies notification to user here

        if (
            uninstall_state[pkg] != None
            and len(uninstall_state[pkg]) > 0
            and uninstall_state[pkg] != "REMOVED"
            and uninstall_state[pkg] != "QUEUED"
        ):
            print(
                "[ERROR] %s Package uninstall failed : %s"
                % (datetime.now().strftime("%H:%M:%S"), str(uninstall_state[pkg]))
            )

            msg_dialog = message_dialog(
                self,
                "Error removing package",
                "Failed to remove package: %s" % pkg,
                " ".join(uninstall_state[pkg]),
                Gtk.MessageType.ERROR,
            )

            msg_dialog.run()
            msg_dialog.hide()

        self.pkg_queue.task_done()


# =====================================================
#               SEARCH INDEXING
# =====================================================


# store a list of package metadata into memory for fast retrieval
def storePackages():
    path = base_dir + "/yaml/"
    yaml_files = []
    packages = []

    category_dict = {}

    try:
        # get a list of yaml files
        for file in os.listdir(path):
            if file.endswith(".yaml"):
                yaml_files.append(file)

        if len(yaml_files) > 0:
            for yaml_file in yaml_files:
                cat_desc = ""
                package_name = ""
                package_cat = ""

                category_name = yaml_file[11:-5].strip().capitalize()

                # read contents of each yaml file

                with open(path + yaml_file, "r") as yaml:
                    content = yaml.readlines()
                for line in content:
                    if line.startswith("  packages:"):
                        continue
                    elif line.startswith("  description: "):
                        # Set the label text for the description line
                        subcat_desc = (
                            line.strip("  description: ")
                            .strip()
                            .strip('"')
                            .strip("\n")
                            .strip()
                        )
                    elif line.startswith("- name:"):
                        # category
                        subcat_name = (
                            line.strip("- name: ")
                            .strip()
                            .strip('"')
                            .strip("\n")
                            .strip()
                        )
                    elif line.startswith("    - "):
                        # add the package to the packages list

                        package_name = line.strip("    - ").strip()
                        # get the package description
                        package_desc = obtain_pkg_description(package_name)

                        package = Package(
                            package_name,
                            package_desc,
                            category_name,
                            subcat_name,
                            subcat_desc,
                        )

                        packages.append(package)

        # filter the results so that each category holds a list of package

        category_name = None
        packages_cat = []
        for pkg in packages:
            if category_name == pkg.category:
                packages_cat.append(pkg)
                category_dict[category_name] = packages_cat
            elif category_name == None:
                packages_cat.append(pkg)
                category_dict[pkg.category] = packages_cat
            else:
                # reset packages, new category
                packages_cat = []

                packages_cat.append(pkg)

                category_dict[pkg.category] = packages_cat

            category_name = pkg.category

        """
        Print dictionary for debugging

        for key in category_dict.keys():
            print("Category = %s" % key)
            pkg_list = category_dict[key]

            for pkg in pkg_list:
                print(pkg.name)
                #print(pkg.category)


            print("++++++++++++++++++++++++++++++")
        """

        sorted_dict = None

        sorted_dict = dict(sorted(category_dict.items()))

        return sorted_dict
    except Exception as e:
        print("Exception in storePackages() : %s" % e)
        sys.exit(0)


# =====================================================
#               CREATE MESSAGE DIALOG
# =====================================================


# show the dependencies error here which is stopping the install/uninstall pkg process
def message_dialog(self, title, first_msg, secondary_msg, msg_type):
    msg_dialog = Gtk.MessageDialog(
        self,
        flags=0,
        message_type=msg_type,
        buttons=Gtk.ButtonsType.OK,
        text="%s" % first_msg,
    )

    msg_dialog.set_title(title)

    if len(secondary_msg) > 0:
        msg_dialog.format_secondary_markup("%s" % secondary_msg)

    return msg_dialog


# =====================================================
#               APP QUERY
# =====================================================


def get_current_installed():
    path = base_dir + "/cache/installed.lst"
    # query_str = "pacman -Q > " + path
    query_str = ["pacman", "-Q"]
    # run the query - using Popen because it actually suits this use case a bit better.

    subprocess_query = subprocess.Popen(
        query_str,
        shell=False,
        stdout=subprocess.PIPE,
    )

    out, err = subprocess_query.communicate(timeout=60)

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
                get_current_installed()
        # file does NOT exist;
        else:
            get_current_installed()
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


def cache(package, path_dir_cache):
    try:
        # first we need to strip the new line escape sequence to ensure we don't get incorrect outcome
        pkg = package.strip()
        # you can see all the errors here with the print command below
        if debug == True:
            print(pkg)
        # create the query
        query_str = ["pacman", "-Si", pkg, " --noconfirm"]

        # run the query - using Popen because it actually suits this use case a bit better.

        process = subprocess.Popen(
            query_str, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = process.communicate()

        # validate the process result
        if process.returncode == 0:
            if debug == True:
                print("Return code: equals 0 " + str(process.returncode))
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
                filename = path_dir_cache + pkg

                file = open(filename, "w")
                file.write(description)
                file.close()

                return description
        # There are several packages that do not return a valid process return code
        # Cathing those manually via corrections folder
        if process.returncode != 0:
            if debug == True:
                print("Return code: " + str(process.returncode))
            exceptions = [
                "florence",
                "mintstick-bin",
                "arcolinux-conky-collection-plasma-git",
                "arcolinux-desktop-trasher-git",
                "arcolinux-pamac-all",
                "arcolinux-sddm-simplicity-git",
                "ttf-hack",
                "ttf-roboto-mono",
                "aisleriot",
                "mailspring",
                "linux-rt",
                "linux-rt-headers",
                "linux-rt-lts",
                "linux-rt-lts-headers",
                "arcolinux-sddm-simplicity-git",
                "kodi-x11",
                "kodi-addons",
                "sardi-icons",
            ]
            if pkg in exceptions:
                description = file_lookup(pkg, path_dir_cache + "corrections/")
                return description
        return "No Description Found"

    except Exception as e:
        print("Exception in cache(): %s " % e)


# Creating an over-load so that we can use the same function, with slightly different code to get the results we need
def cache_btn():
    # fraction = 1 / len(packages)
    # Non Multithreaded version.
    packages.sort()
    number = 1
    for pkg in packages:
        print(str(number) + "/" + str(len(packages)) + ": Caching " + pkg)
        cache(pkg, path_dir_cache)
        number = number + 1
        # progressbar.timeout_id = GLib.timeout_add(50, progressbar.update, fraction)

    print(
        "[INFO] Caching applications finished  " + datetime.now().strftime("%H:%M:%S")
    )

    # This will need to be coded to be running multiple processes eventually, since it will be manually invoked.
    # process the file list
    # for each file in the list, open the file
    # process the file ignoring what is not what we need
    # for each file line processed, we need to invoke the cache function that is not over-ridden.


def file_lookup(package, path):
    # first we need to strip the new line escape sequence to ensure we don't get incorrect outcome
    pkg = package.strip("\n")
    output = ""
    if os.path.exists(path + "corrections/" + pkg):
        filename = path + "corrections/" + pkg
    else:
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


# def check_github(yaml_files):
#     # This is the link to the location where the .yaml files are kept in the github
#     # Removing desktop wayland, desktop, drivers, nvidia, ...
#     path = base_dir + "/cache/"
#     link = "https://github.com/arcolinux/arcob-calamares-config-awesome/tree/master/calamares/modules/"
#     urls = []
#     fns = []
#     for file in yaml_files:
#         if isfileStale(path + file, 14, 0, 0):
#             fns.append(path + file)
#             urls.append(link + file)
#     if len(fns) > 0 & len(urls) > 0:
#         inputs = zip(urls, fns)
#         download_parallel(inputs)


# def download_url(args):
#     t0 = time.time()
#     url, fn = args[0], args[1]
#     try:
#         r = requests.get(url)
#         with open(fn, "wb") as f:
#             f.write(r.content)
#         return (url, time.time() - t0)
#     except Exception as e:
#         print("Exception in download_url():", e)


# def download_parallel(args):
#     cpus = cpu_count()
#     results = ThreadPool(cpus - 1).imap_unordered(download_url, args)
#     for result in results:
#         print("url:", result[0], "time (s):", result[1])


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


# get a number of pacman processes are running


# =====================================================
#               CHECK PACMAN LOCK FILE
# =====================================================


def waitForPacmanLockFile():
    start = int(time.time())

    try:
        while True:
            if os.path.exists(pacman_lock_file):
                time.sleep(5)

                elapsed = int(time.time()) + 5

                print(
                    "[DEBUG] %s Pacman is busy.. elapsed duration: %ss"
                    % (datetime.now().strftime("%H:%M:%S"), (elapsed - start))
                )

                proc = get_pacman_process()

                if proc:
                    print(
                        "[DEBUG] %s Pacman process: %s"
                        % (datetime.now().strftime("%H:%M:%S"), str(proc))
                    )
                else:
                    print(
                        "[DEBUG] %s Process completed, Pacman is ready"
                        % datetime.now().strftime("%H:%M:%S")
                    )
                    return

                if (elapsed - start) >= process_timeout:
                    print(
                        "[WARN] %s Waiting for previous Pacman transaction to complete timed out after %ss"
                        % (datetime.now().strftime("%H:%M:%S"), process_timeout)
                    )
                    return
            else:
                print(
                    "[DEBUG] %s Pacman is ready" % datetime.now().strftime("%H:%M:%S")
                )
                return
    except Exception as e:
        print("Exception in waitForPacmanLockFile(): %s " % e)


# this gets info on the pacman process currently running
def get_pacman_process():
    try:
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=["pid", "name", "create_time"])
                if pinfo["name"] == "pacman":
                    return " ".join(proc.cmdline())

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        print("Exception in get_pacman_process() : %s" % e)


# =====================================================
#               MESSAGEBOX
# =====================================================


def messageBox(self, title, message):
    md2 = Gtk.MessageDialog(
        parent=self,
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text=message,
    )
    md2.format_secondary_markup(message)
    md2.run()
    md2.destroy()


# =====================================================
#               USER SEARCH
# =====================================================


def search(self, term):
    try:
        print(
            '[INFO] %s Searching for: "%s"'
            % (
                datetime.now().strftime("%H:%M:%S"),
                term,
            )
        )

        pkg_matches = []

        category_dict = {}

        whitespace = False

        if term.strip():
            whitespace = True

        for pkg_list in self.packages.values():
            for pkg in pkg_list:
                if whitespace:
                    for te in term.split(" "):
                        if (
                            te.lower() in pkg.name.lower()
                            or te.lower() in pkg.description.lower()
                        ):
                            # only unique name matches
                            if pkg not in pkg_matches:
                                pkg_matches.append(
                                    pkg,
                                )
                else:
                    if (
                        term.lower() in pkg.name.lower()
                        or term.lower() in pkg.description.lower()
                    ):
                        pkg_matches.append(
                            pkg,
                        )

        # filter the results so that each category holds a list of package

        category_name = None
        packages_cat = []
        for pkg_match in pkg_matches:
            if category_name == pkg_match.category:
                packages_cat.append(pkg_match)
                category_dict[category_name] = packages_cat
            elif category_name == None:
                packages_cat.append(pkg_match)
                category_dict[pkg_match.category] = packages_cat
            else:
                # reset packages, new category
                packages_cat = []

                packages_cat.append(pkg_match)

                category_dict[pkg_match.category] = packages_cat

            category_name = pkg_match.category

        if len(category_dict) == 0:
            self.search_queue.put(None)
            msg_dialog = message_dialog(
                self,
                "Find Package",
                '"%s" was not found in the available sources' % term,
                "Please try another search query",
                Gtk.MessageType.ERROR,
            )

            msg_dialog.run()
            msg_dialog.hide()

        # debug console output to display package info
        """
        # print out number of results found from each category
        print("[DEBUG] %s Search results.." % datetime.now().strftime("%H:%M:%S"))

        for category in sorted(category_dict):
            category_res_len = len(category_dict[category])
            print("[DEBUG] %s %s = %s" %(
                        datetime.now().strftime("%H:%M:%S"),
                        category,
                        category_res_len,
                    )
            )
        """

        # sort dictionary so the category names are displayed in alphabetical order
        sorted_dict = None

        if len(category_dict) > 0:
            sorted_dict = dict(sorted(category_dict.items()))
            self.search_queue.put(
                sorted_dict,
            )
        else:
            return

    except Exception as e:
        print("Exception in search(): %s", e)


# =====================================================
#               ARCOLINUX REPOS, KEYS AND MIRRORS
# =====================================================


def append_repo(text):
    """Append a new repo"""
    try:
        with open(pacman_conf, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(text)
    except Exception as error:
        print(error)


def repo_exist(value):
    """check repo_exists"""
    with open(pacman_conf, "r", encoding="utf-8") as f:
        lines = f.readlines()
        f.close()

    for line in lines:
        if value in line:
            return True
    return False


# install ArcoLinux mirrorlist and key package
def install_arcolinux_key_mirror(self):
    base_dir = os.path.dirname(os.path.realpath(__file__))
    pathway = base_dir + "/packages/arcolinux-keyring/"
    file = os.listdir(pathway)

    try:
        install = "pacman -U " + pathway + str(file).strip("[]'") + " --noconfirm"
        print("[INFO] : " + install)
        subprocess.call(
            install.split(" "),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        print("[INFO] : ArcoLinux keyring is now installed")
    except Exception as error:
        print(error)

    pathway = base_dir + "/packages/arcolinux-mirrorlist/"
    file = os.listdir(pathway)
    try:
        install = "pacman -U " + pathway + str(file).strip("[]'") + " --noconfirm"
        print("[INFO] : " + install)
        subprocess.call(
            install.split(" "),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        print("[INFO] : ArcoLinux mirrorlist is now installed")
    except Exception as error:
        print(error)


# remove ArcoLinux mirrorlist and key package
def remove_arcolinux_key_mirror(self):
    try:
        command = "pacman -Rdd arcolinux-keyring --noconfirm"
        print("[INFO] : " + command)
        subprocess.call(
            command.split(" "),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        print("[INFO] : ArcoLinux keyring is now removed")
    except Exception as error:
        print(error)

    try:
        command = "pacman -Rdd arcolinux-mirrorlist-git --noconfirm"
        print("[INFO] : " + command)
        subprocess.call(
            command.split(" "),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        print("[INFO] : ArcoLinux mirrorlist is now removed")
    except Exception as error:
        print(error)


def add_repos():
    """add the ArcoLinux repos in /etc/pacman.conf"""
    if distr == "arcolinux":
        print("[INFO] : Adding ArcoLinux repos on ArcoLinux")
        try:
            with open(pacman_conf, "r", encoding="utf-8") as f:
                lines = f.readlines()
                f.close()
        except Exception as error:
            print(error)

        text = "\n\n" + atestrepo + "\n\n" + arepo + "\n\n" + a3prepo + "\n\n" + axlrepo

        pos = get_position(lines, "#[testing]")
        lines.insert(pos - 2, text)

        try:
            with open(pacman_conf, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception as error:
            print(error)
    else:
        if not repo_exist("[arcolinux_repo_testing]"):
            print("[INFO] : Adding ArcoLinux test repo (not used)")
            append_repo(atestrepo)
        if not repo_exist("[arcolinux_repo]"):
            print("[INFO] : Adding ArcoLinux repo")
            append_repo(arepo)
        if not repo_exist("[arcolinux_repo_3party]"):
            print("[INFO] : Adding ArcoLinux 3th party repo")
            append_repo(a3prepo)
        if not repo_exist("[arcolinux_repo_xlarge]"):
            print("[INFO] : Adding ArcoLinux XL repo")
            append_repo(axlrepo)
        if repo_exist("[arcolinux_repo]"):
            print("[INFO] : ArcoLinux repos have been installed")


def remove_repos():
    """remove the ArcoLinux repos in /etc/pacman.conf"""
    try:
        with open(pacman_conf, "r", encoding="utf-8") as f:
            lines = f.readlines()
            f.close()

        if repo_exist("[arcolinux_repo_testing]"):
            pos = get_position(lines, "[arcolinux_repo_testing]")
            del lines[pos + 3]
            del lines[pos + 2]
            del lines[pos + 1]
            del lines[pos]

        if repo_exist("[arcolinux_repo]"):
            pos = get_position(lines, "[arcolinux_repo]")
            del lines[pos + 3]
            del lines[pos + 2]
            del lines[pos + 1]
            del lines[pos]

        if repo_exist("[arcolinux_repo_3party]"):
            pos = get_position(lines, "[arcolinux_repo_3party]")
            del lines[pos + 3]
            del lines[pos + 2]
            del lines[pos + 1]
            del lines[pos]

        if repo_exist("[arcolinux_repo_xlarge]"):
            pos = get_position(lines, "[arcolinux_repo_xlarge]")
            del lines[pos + 2]
            del lines[pos + 1]
            del lines[pos]

        with open(pacman_conf, "w", encoding="utf-8") as f:
            f.writelines(lines)
            f.close()

    except Exception as error:
        print(error)


# =====================================================
#               CHECK IF PACKAGE IS INSTALLED
# =====================================================


# check if package is installed or not
def check_package_installed(package):
    try:
        subprocess.check_output(
            "pacman -Qi " + package, shell=True, stderr=subprocess.STDOUT
        )
        # package is installed
        return True
    except subprocess.CalledProcessError:
        # package is not installed
        return False


# =====================================================
#               NOTIFICATIONS
# =====================================================


def show_in_app_notification(self, message, err):
    if self.timeout_id is not None:
        GLib.source_remove(self.timeout_id)
        self.timeout_id = None

    if err == True:
        self.notification_label.set_markup(
            '<span background="yellow" foreground="black">' + message + "</span>"
        )
    else:
        self.notification_label.set_markup(
            '<span foreground="white">' + message + "</span>"
        )
    self.notification_revealer.set_reveal_child(True)
    self.timeout_id = GLib.timeout_add(3000, timeOut, self)


def timeOut(self):
    close_in_app_notification(self)


def close_in_app_notification(self):
    self.notification_revealer.set_reveal_child(False)
    GLib.source_remove(self.timeout_id)
    self.timeout_id = None


# =====================================================
#               KILL PACMAN PROCESS
# =====================================================

"""
    Since the app could be quit, killed during a pacman transaction.
    The pacman process spawned by the install/uninstall threads, needs to be terminated too.
    Otherwise the app will hang waiting for pacman to complete its transaction.
"""


def terminate_pacman():
    try:
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=["pid", "name", "create_time"])
                if pinfo["name"] == "pacman":
                    proc.kill()

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        if os.path.exists(pacman_lock_file):
            os.unlink(pacman_lock_file)
    except Exception as e:
        print("Exception in terminate_pacman() : %s" % e)


#######ANYTHING UNDER THIS LINE IS CURRENTLY UNUSED!
