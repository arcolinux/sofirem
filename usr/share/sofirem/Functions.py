# =================================================================
# =                 Author: Cameron Percival                      =
# =================================================================

import os
import sys
import psutil
import time
import datetime
from datetime import datetime, timedelta
import subprocess
import threading
import gi
import logging
import shutil
from threading import Thread
from Package import Package
from ui.MessageDialog import MessageDialog
from distro import id
from os import makedirs

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

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
sofirem_lockfile = "/tmp/sofirem.lock"
sofirem_pidfile = "/tmp/sofirem.pid"
# 10m timeout
process_timeout = 600

arcolinux_mirrorlist = "/etc/pacman.d/arcolinux-mirrorlist"
pacman_conf = "/etc/pacman.conf"
pacman_conf_backup = "/etc/pacman.conf.bak"
pacman_logfile = "/var/log/pacman.log"
pacman_lockfile = "/var/lib/pacman/db.lck"

arco_test_repo = [
    "#[arcolinux_repo_testing]",
    "#SigLevel = Optional TrustedOnly",
    "#Include = /etc/pacman.d/arcolinux-mirrorlist",
]

arco_repo = [
    "[arcolinux_repo]",
    "SigLevel = Optional TrustedOnly",
    "Include = /etc/pacman.d/arcolinux-mirrorlist",
]

arco_3rd_party_repo = [
    "[arcolinux_repo_3party]",
    "SigLevel = Optional TrustedOnly",
    "Include = /etc/pacman.d/arcolinux-mirrorlist",
]

arco_xlrepo = [
    "[arcolinux_repo_xlarge]",
    "SigLevel = Optional TrustedOnly",
    "Include = /etc/pacman.d/arcolinux-mirrorlist",
]


log_dir = "/var/log/sofirem/%s/" % datetime.now().strftime("%Y-%m-%d")
event_log_file = "%s/%s-event.log" % (
    log_dir,
    datetime.now().strftime("%H-%M-%S"),
)

export_dir = "%s/sofirem-exports" % home


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
        logger.error(e)


# Create log directory and export directory
try:
    if not os.path.exists(log_dir):
        makedirs(log_dir)

    if not os.path.exists(export_dir):
        makedirs(export_dir)

    permissions(export_dir)

    print("[INFO] Log directory = %s" % log_dir)
    print("[INFO] Export directory = %s" % export_dir)


except os.error as oe:
    print("[ERROR] Exception in setup log/export directory: %s" % oe)
    sys.exit(1)

logger = logging.getLogger("logger")

logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

fh = logging.FileHandler(event_log_file, mode="a", encoding="utf-8", delay=False)
fh.setLevel(level=logging.INFO)

# create formatter
formatter = logging.Formatter(
    "%(asctime)s:%(levelname)s > %(message)s", "%Y-%m-%d %H:%M:%S"
)
# add formatter to ch
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

# add fh to logger
logger.addHandler(fh)


# a before state of packages
def create_packages_log():
    try:
        logger.info("Creating a list of currently installed packages")
        packages_log = "%s-packages.log" % datetime.now().strftime("%H-%M-%S")
        logger.info("Saving in %s" % packages_log)
        cmd = ["pacman", "-Q"]

        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            with open("%s/%s" % (log_dir, packages_log), "w") as f:
                f.write(
                    "# Created by Sofirem on %s\n"
                    % datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )

                for line in process.stdout:
                    f.write("%s" % line)
    except Exception as e:
        logger.error("Exception in create_packages_log(): %s" % e)


# =====================================================
#               GLOBAL FUNCTIONS
# =====================================================


def _get_position(lists, value):
    data = [string for string in lists if value in string]
    position = lists.index(data[0])
    return position


def is_file_stale(filepath, stale_days, stale_hours, stale_minutes):
    # first, lets obtain the datetime of the day that we determine data to be "stale"
    now = datetime.now()
    # For the purposes of this, we are assuming that one would have the app open longer than 5 minutes if installing.
    stale_datetime = now - timedelta(
        days=stale_days, hours=stale_hours, minutes=stale_minutes
    )
    # Check to see if the file path is in existence.
    if os.path.exists(filepath):
        # if the file exists, when was it made?
        file_created = datetime.fromtimestamp(os.path.getctime(filepath))
        # file is older than the time delta identified above
        if file_created < stale_datetime:
            return True
    return False


# =====================================================
#               PACMAN SYNC PACKAGE DB
# =====================================================
def sync_package_db():
    try:
        sync_str = ["pacman", "-Sy"]
        logger.info("Synchronizing pacman package databases")
        process_sync = subprocess.run(
            sync_str,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=process_timeout,
        )

        if process_sync.returncode == 0:
            return None
        else:
            if process_sync.stdout:
                out = str(process_sync.stdout.decode("utf-8"))
                logger.error(out)

                return out

    except Exception as e:
        logger.error("Exception in sync(): %s" % e)


# =====================================================
#               PACMAN INSTALL/UNINSTALL PROCESS
# =====================================================


# this is run inside a separate thread
def start_subprocess(self, cmd, progress_dialog, action, pkg, widget):
    try:
        self.switch_pkg_version.set_sensitive(False)
        self.switch_arco_keyring.set_sensitive(False)
        self.switch_arco_mirrorlist.set_sensitive(False)

        widget.set_sensitive(False)

        # store process std out into a list, if there are errors display to user once the process completes
        process_stdout_lst = []
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            if progress_dialog is not None:
                progress_dialog.pkg_dialog_closed = False

            self.in_progress = True

            line = (
                "Pacman is processing the %s of package %s \n\nCommand running = %s\n\n"
                % (action, pkg.name, " ".join(cmd))
            )

            if progress_dialog is not None:
                GLib.idle_add(
                    update_progress_textview,
                    self,
                    line,
                    progress_dialog,
                    priority=GLib.PRIORITY_DEFAULT,
                )

            logger.debug("Pacman is now processing the request")

            # poll for the process to complete
            # read stdout as it comes in, update the progress textview

            # poll() Check if child process has terminated.
            # Set and return returncode attribute. Otherwise, returns None.

            while True:
                if process.poll() is not None:
                    break

                if (
                    progress_dialog is not None
                    and progress_dialog.pkg_dialog_closed is False
                ):
                    for line in process.stdout:
                        GLib.idle_add(
                            update_progress_textview,
                            self,
                            line,
                            progress_dialog,
                            priority=GLib.PRIORITY_DEFAULT,
                        )
                        process_stdout_lst.append(line)

                    time.sleep(0.3)
                else:
                    # increase wait time to reduce cpu load, no textview updates required since dialog is closed
                    # since the progress dialog window is closed, capture errors and then later display it
                    for line in process.stdout:
                        process_stdout_lst.append(line)
                    time.sleep(1)

            returncode = process.poll()

            # logger.debug("Pacman process return code = %s" % returncode)

            logger.info(
                "Pacman process completed for package = %s and action = %s"
                % (pkg.name, action)
            )

            GLib.idle_add(
                refresh_ui,
                self,
                action,
                widget,
                pkg,
                progress_dialog,
                process_stdout_lst,
                priority=GLib.PRIORITY_DEFAULT,
            )

    except TimeoutError as t:
        logger.error("TimeoutError in %s start_subprocess(): %s" % (action, t))
        process.terminate()
        if progress_dialog is not None:
            progress_dialog.btn_package_progress_close.set_sensitive(True)
        self.switch_pkg_version.set_sensitive(True)
        self.switch_arco_keyring.set_sensitive(True)
        self.switch_arco_mirrorlist.set_sensitive(True)

    except SystemError as s:
        logger.error("SystemError in %s start_subprocess(): %s" % (action, s))
        process.terminate()
        if progress_dialog is not None:
            progress_dialog.btn_package_progress_close.set_sensitive(True)
        self.switch_pkg_version.set_sensitive(True)
        self.switch_arco_keyring.set_sensitive(True)
        self.switch_arco_mirrorlist.set_sensitive(True)


# refresh ui components, once the process completes
# show notification dialog to user if errors are encountered during package install/uninstall
def refresh_ui(self, action, switch, pkg, progress_dialog, process_stdout_lst):
    self.switch_pkg_version.set_sensitive(True)
    self.switch_arco_keyring.set_sensitive(True)
    self.switch_arco_mirrorlist.set_sensitive(True)

    logger.debug("Checking if package %s is installed" % pkg.name)
    installed = check_package_installed(pkg.name)

    if progress_dialog is not None:
        progress_dialog.btn_package_progress_close.set_sensitive(True)

    if installed is True and action == "install":
        logger.debug("Toggle switch state = True")
        switch.set_sensitive(True)
        switch.set_state(True)
        switch.set_active(True)

        if progress_dialog is not None:
            if progress_dialog.pkg_dialog_closed is False:
                progress_dialog.set_title("Package install for %s completed" % pkg.name)

                progress_dialog.infobar.set_name("infobar_info")

                content = progress_dialog.infobar.get_content_area()
                if content is not None:
                    for widget in content.get_children():
                        content.remove(widget)

                    lbl_install = Gtk.Label(xalign=0, yalign=0)
                    lbl_install.set_markup("<b>Package %s installed</b>" % pkg.name)

                    content.add(lbl_install)

                    if self.timeout_id is not None:
                        GLib.source_remove(self.timeout_id)
                        self.timeout_id = None

                    self.timeout_id = GLib.timeout_add(
                        100, reveal_infobar, self, progress_dialog
                    )

    if installed is False and action == "install":
        logger.debug("Toggle switch state = False")

        if progress_dialog is not None:
            # install failed/terminated
            switch.set_sensitive(True)
            switch.set_state(False)
            switch.set_active(False)

            if progress_dialog.pkg_dialog_closed is False:
                progress_dialog.set_title("Package install for %s failed" % pkg.name)

                progress_dialog.infobar.set_name("infobar_error")

                content = progress_dialog.infobar.get_content_area()
                if content is not None:
                    for widget in content.get_children():
                        content.remove(widget)

                    lbl_install = Gtk.Label(xalign=0, yalign=0)
                    lbl_install.set_markup(
                        "<b>Package %s install failed</b>" % pkg.name
                    )

                    content.add(lbl_install)

                    if self.timeout_id is not None:
                        GLib.source_remove(self.timeout_id)
                        self.timeout_id = None

                    self.timeout_id = GLib.timeout_add(
                        100, reveal_infobar, self, progress_dialog
                    )
            else:
                logger.debug(" ".join(process_stdout_lst))

                message_dialog = MessageDialog(
                    "Errors occurred during install",
                    "Errors occurred install for %s failed" % pkg.name,
                    "Pacman failed to install package %s\n" % pkg.name,
                    " ".join(process_stdout_lst),
                    "error",
                    True,
                )

                message_dialog.show_all()
                # message_dialog.run()
                # message_dialog.hide()
        elif progress_dialog is None or progress_dialog.pkg_dialog_closed is True:
            # the package progress dialog has been closed, but notify user package failed to install

            if (
                "error: failed to init transaction (unable to lock database)\n"
                in process_stdout_lst
            ):
                # at this point the package install is stuck behind another pacman transaction so put this onto the holding queue

                # logger.debug(" ".join(process_stdout_lst))

                if progress_dialog is None:
                    logger.debug("Adding package to holding queue")
                    if self.show_progress_dialog is False:
                        inst_str = [
                            "pacman",
                            "-S",
                            pkg.name,
                            "--needed",
                            "--noconfirm",
                        ]
                        self.pkg_holding_queue.put(
                            (
                                pkg,
                                action,
                                switch,
                                inst_str,
                                progress_dialog,
                            ),
                        )
                else:
                    logger.debug(" ".join(process_stdout_lst))
                    switch.set_sensitive(True)
                    switch.set_state(False)
                    switch.set_active(False)

                    proc = fn.get_pacman_process()

                    message_dialog = MessageDialog(
                        "Warning",
                        "Sofirem cannot proceed pacman lockfile found",
                        "Pacman cannot lock the db, a lockfile is found inside %s"
                        % fn.pacman_lockfile,
                        "Pacman is running: %s" % proc,
                        "warning",
                        False,
                    )

                    message_dialog.show_all()
                    # message_dialog.run()
                    # message_dialog.hide()

                    # progress dialog is closed show message dialog with error
            elif "error: target not found: %s\n" % pkg.name in process_stdout_lst:
                message_dialog = MessageDialog(
                    "Error",
                    "Pacman repository error: package '%s' was not found" % pkg.name,
                    "Sofirem cannot process the request",
                    "Are the correct pacman mirrorlists configured ?",
                    "error",
                    False,
                )

                message_dialog.show_all()

            else:
                # logger.debug(" ".join(process_stdout_lst))

                switch.set_sensitive(True)
                switch.set_state(False)
                switch.set_active(False)

                message_dialog = MessageDialog(
                    "Errors occurred during install",
                    "Errors occurred install for %s failed" % pkg.name,
                    "Pacman failed to install package %s\n" % pkg.name,
                    " ".join(process_stdout_lst),
                    "error",
                    True,
                )

                message_dialog.show_all()
                # message_dialog.run()
                # message_dialog.hide()

    if installed is False and action == "uninstall":
        logger.debug("Toggle switch state = False")
        switch.set_sensitive(True)
        switch.set_state(False)
        switch.set_active(False)

        if progress_dialog is not None:
            if progress_dialog.pkg_dialog_closed is False:
                progress_dialog.set_title(
                    "Package uninstall for %s completed" % pkg.name
                )
                progress_dialog.infobar.set_name("infobar_info")
                content = progress_dialog.infobar.get_content_area()
                if content is not None:
                    for widget in content.get_children():
                        content.remove(widget)

                    lbl_install = Gtk.Label(xalign=0, yalign=0)
                    lbl_install.set_markup("<b>Package %s uninstalled</b>" % pkg.name)

                    content.add(lbl_install)

                    if self.timeout_id is not None:
                        GLib.source_remove(self.timeout_id)
                        self.timeout_id = None

                    self.timeout_id = GLib.timeout_add(
                        100, reveal_infobar, self, progress_dialog
                    )

    if installed is True and action == "uninstall":
        # uninstall failed/terminated
        switch.set_sensitive(True)
        switch.set_state(True)
        switch.set_active(True)

        if progress_dialog is not None:
            if progress_dialog.pkg_dialog_closed is False:
                progress_dialog.set_title("Package uninstall for %s failed" % pkg.name)
                progress_dialog.infobar.set_name("infobar_error")

                content = progress_dialog.infobar.get_content_area()
                if content is not None:
                    for widget in content.get_children():
                        content.remove(widget)

                    lbl_install = Gtk.Label(xalign=0, yalign=0)
                    lbl_install.set_markup(
                        "<b>Package %s uninstall failed</b>" % pkg.name
                    )

                    content.add(lbl_install)

                    if self.timeout_id is not None:
                        GLib.source_remove(self.timeout_id)
                        self.timeout_id = None

                    self.timeout_id = GLib.timeout_add(
                        100, reveal_infobar, self, progress_dialog
                    )

        elif progress_dialog is None or progress_dialog.pkg_dialog_closed is True:
            # the package progress dialog has been closed, but notify user package failed to uninstall

            if (
                "error: failed to init transaction (unable to lock database)\n"
                in process_stdout_lst
            ):
                # proc = get_pacman_process()
                # if proc is not None and len(proc) > 0:
                #     message_dialog = MessageDialog(
                #         "Warning",
                #         "Sofirem cannot proceed pacman lockfile found",
                #         "Pacman cannot lock the db, a lockfile is found inside %s"
                #         % pacman_lockfile,
                #         "Process running = %s" % proc,
                #         "warning",
                #         False,
                #     )
                #     message_dialog.show_all()
                #     message_dialog.run()
                #     message_dialog.hide()
                # else:
                #     message_dialog = MessageDialog(
                #         "Warning",
                #         "Sofirem cannot proceed pacman lockfile found",
                #         "Pacman cannot lock the db, a lockfile is found inside %s"
                #         % pacman_lockfile,
                #         "",
                #         "warning",
                #         False,
                #     )
                #     message_dialog.show_all()
                #     message_dialog.run()
                #     message_dialog.hide()
                logger.debug(" ".join(process_stdout_lst))

            else:
                message_dialog = MessageDialog(
                    "Errors occurred during uninstall",
                    "Errors occurred uninstall of %s failed" % pkg.name,
                    "Pacman failed to uninstall package %s\n" % pkg.name,
                    " ".join(process_stdout_lst),
                    "error",
                    True,
                )

                message_dialog.show_all()
                # message_dialog.run()
                # message_dialog.hide()


# update progress textview using stdout from the pacman process running


def update_progress_textview(self, line, progress_dialog):
    if (
        progress_dialog is not None
        and progress_dialog.pkg_dialog_closed is False
        and self.in_progress is True
    ):
        buffer = progress_dialog.package_progress_textview.get_buffer()
        if len(line) > 0 or buffer is None:
            buffer.insert(buffer.get_end_iter(), "%s" % line, len("%s" % line))

            text_mark_end = buffer.create_mark("\nend", buffer.get_end_iter(), False)

            # scroll to the end of the textview
            progress_dialog.package_progress_textview.scroll_mark_onscreen(
                text_mark_end
            )
    else:
        # dialog window is closed
        line = None
        return False


# =====================================================
#               APP INSTALLATION
# =====================================================
def install(self):
    pkg, action, widget, inst_str, progress_dialog = self.pkg_queue.get()

    try:
        if action == "install":
            # path = base_dir + "/cache/installed.lst"
            logger.debug("Running inside install thread")
            logger.info("Installing package %s" % pkg.name)
            logger.debug(inst_str)

            # run pacman process inside a thread

            th_subprocess_install = Thread(
                name="thread_subprocess",
                target=start_subprocess,
                args=(
                    self,
                    inst_str,
                    progress_dialog,
                    action,
                    pkg,
                    widget,
                ),
                daemon=True,
            )

            th_subprocess_install.start()

            logger.debug("Thread: subprocess install started")

    except Exception as e:
        # deactivate switch widget, install failed
        widget.set_state(False)
        if progress_dialog is not None:
            progress_dialog.btn_package_progress_close.set_sensitive(True)
        logger.error("Exception in install(): %s" % e)
    finally:
        # task completed
        self.pkg_queue.task_done()


# =====================================================
#               APP UNINSTALLATION
# =====================================================
def uninstall(self):
    pkg, action, widget, uninst_str, progress_dialog = self.pkg_queue.get()

    try:
        if action == "uninstall":
            # path = base_dir + "/cache/installed.lst"
            logger.debug("Running inside uninstall thread")
            logger.info("Uninstalling package %s" % pkg.name)
            logger.debug(uninst_str)

            # run pacman process inside a thread

            th_subprocess_uninstall = Thread(
                name="thread_subprocess",
                target=start_subprocess,
                args=(
                    self,
                    uninst_str,
                    progress_dialog,
                    action,
                    pkg,
                    widget,
                ),
                daemon=True,
            )

            # is there a pacman lockfile, wait for it before uninstalling
            while check_pacman_lockfile():
                time.sleep(0.2)

            th_subprocess_uninstall.start()

            logger.debug("Thread: subprocess uninstall started")

    except Exception as e:
        widget.set_state(True)
        if progress_dialog is not None:
            progress_dialog.btn_package_progress_close.set_sensitive(True)
        logger.error("Exception in uninstall(): %s" % e)
    finally:
        self.pkg_queue.task_done()


# =====================================================
#               SEARCH INDEXING
# =====================================================


# store a list of package metadata into memory for fast retrieval
def store_packages():
    path = base_dir + "/yaml/"
    yaml_files = []
    packages = []

    category_dict = {}

    try:
        # get latest package version info

        package_metadata = get_all_package_info()

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

                        # get the package version, lookup dictionary

                        package_version = "Unknown"

                        for i in package_metadata:
                            if i["name"] == package_name:
                                package_version = i["version"]
                                break

                        package = Package(
                            package_name,
                            package_desc,
                            category_name,
                            subcat_name,
                            subcat_desc,
                            package_version,
                        )

                        packages.append(package)

        # filter the results so that each category holds a list of package

        category_name = None
        packages_cat_lst = []
        for pkg in packages:
            if category_name == pkg.category:
                packages_cat_lst.append(pkg)
                category_dict[category_name] = packages_cat_lst
            elif category_name is None:
                packages_cat_lst.append(pkg)
                category_dict[pkg.category] = packages_cat_lst
            else:
                # reset packages, new category
                packages_cat_lst = []

                packages_cat_lst.append(pkg)

                category_dict[pkg.category] = packages_cat_lst

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
        sys.exit(1)


# =====================================================
#              PACKAGE VERSIONS
# =====================================================


# get live package name, version info and repo name
def get_all_package_info():
    query_str = ["pacman", "-Si"]

    try:
        process_pkg_query = subprocess.Popen(
            query_str, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        out, err = process_pkg_query.communicate(timeout=process_timeout)

        if process_pkg_query.returncode == 0:
            if out:
                package_data = []
                package_name = "Unknown"
                package_version = "Unknown"

                for line in out.decode("utf-8").splitlines():
                    package_dict = {}
                    if "Name            :" in line.strip():
                        package_name = line.replace(" ", "").split("Name:")[1].strip()

                    if "Version         :" in line.strip():
                        package_version = (
                            line.replace(" ", "").split("Version:")[1].strip()
                        )

                        package_dict["name"] = package_name
                        package_dict["version"] = package_version

                        package_data.append(package_dict)

                return package_data
        else:
            logger.error("Failed to extract package version information.")

    except Exception as e:
        logger.error("Exception in get_all_package_info() : %s" % e)


# get installed package version, installed date, name to be displayed inside PackageListDialog


def get_installed_package_data():
    # to capture the latest package version
    latest_package_data = get_all_package_info()

    query_str = ["pacman", "-Qi"]

    try:
        installed_packages_lst = []
        pkg_name = None
        pkg_version = None
        pkg_install_date = None
        pkg_installed_size = None
        pkg_latest_version = None

        with subprocess.Popen(
            query_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            for line in process.stdout:
                if "Name            :" in line.strip():
                    pkg_name = line.replace(" ", "").split("Name:")[1].strip()

                if "Version         :" in line.strip():
                    pkg_version = line.replace(" ", "").split("Version:")[1].strip()

                if "Installed Size  :" in line.strip():
                    pkg_installed_size = line.split("Installed Size  :")[1].strip()

                if "Install Date    :" in line.strip():
                    pkg_install_date = line.split("Install Date    :")[1].strip()

                    # get the latest version lookup dictionary

                    found = False
                    pkg_latest_version = None

                    for i in latest_package_data:
                        if i["name"] == pkg_name:
                            pkg_latest_version = i["version"]
                            break

                    installed_packages_lst.append(
                        (
                            pkg_name,
                            pkg_version,
                            pkg_latest_version,
                            pkg_installed_size,
                            pkg_install_date,
                        )
                    )

        return installed_packages_lst

    except Exception as e:
        logger.error("Exception in get_installed_package_data() : %s" % e)


# get key package information which is to be shown inside ProgressDialog


def get_package_information(package_name):
    logger.info("Fetching package information for %s" % package_name)

    try:
        pkg_name = "Unknown"
        pkg_version = "Unknown"
        pkg_repository = "Unknown / pacman mirrorlist not configured"
        pkg_description = "Unknown"
        pkg_arch = "Unknown"
        pkg_url = "Unknown"
        pkg_depends_on = []
        pkg_conflicts_with = []
        pkg_download_size = "Unknown"
        pkg_installed_size = "Unknown"
        pkg_build_date = "Unknown"
        pkg_packager = "Unknown"
        package_metadata = {}

        # if check_package_installed(package_name):
        #     query_str = ["pacman", "-Qii", package_name]
        # else:
        #     query_str = ["pacman", "-Sii", package_name]

        query_local_str = ["pacman", "-Qi", package_name]

        query_remote_str = ["pacman", "-Si", package_name]

        process_query_remote = subprocess.run(
            query_remote_str,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=process_timeout,
        )

        # added validation on process result
        if process_query_remote.returncode == 0:
            for line in process_query_remote.stdout.decode("utf-8").splitlines():
                if "Name            :" in line.strip():
                    pkg_name = line.replace(" ", "").split("Name:")[1].strip()

                if "Version         :" in line.strip():
                    pkg_version = line.replace(" ", "").split("Version:")[1].strip()

                if "Repository      :" in line.strip():
                    pkg_repository = line.split("Repository      :")[1].strip()

                if "Description     :" in line.strip():
                    pkg_description = line.split("Description     :")[1].strip()

                if "Architecture    :" in line.strip():
                    pkg_arch = line.split("Architecture    :")[1].strip()

                if "URL             :" in line.strip():
                    pkg_url = line.split("URL             :")[1].strip()

                if "Depends On      :" in line.strip():
                    if line.split("Depends On      :")[1].strip() != "None":
                        pkg_depends_on_str = line.split("Depends On      :")[1].strip()

                        for pkg_dep in pkg_depends_on_str.split("  "):
                            pkg_depends_on.append((pkg_dep, None))
                    else:
                        pkg_depends_on = []

                if "Conflicts With  :" in line.strip():
                    if line.split("Conflicts With  :")[1].strip() != "None":
                        pkg_conflicts_with_str = line.split("Conflicts With  :")[
                            1
                        ].strip()

                        for pkg_con in pkg_conflicts_with_str.split("  "):
                            pkg_conflicts_with.append((pkg_con, None))
                    else:
                        pkg_conflicts_with = []

                if "Download Size   :" in line.strip():
                    pkg_download_size = line.split("Download Size   :")[1].strip()

                if "Installed Size  :" in line.strip():
                    pkg_installed_size = line.split("Installed Size  :")[1].strip()

                if "Build Date      :" in line.strip():
                    pkg_build_date = line.split("Build Date      :")[1].strip()

                if "Packager        :" in line.strip():
                    pkg_packager = line.split("Packager        :")[1].strip()

            package_metadata["name"] = pkg_name
            package_metadata["version"] = pkg_version
            package_metadata["repository"] = pkg_repository
            package_metadata["description"] = pkg_description
            package_metadata["arch"] = pkg_arch
            package_metadata["url"] = pkg_url
            package_metadata["depends_on"] = pkg_depends_on
            package_metadata["conflicts_with"] = pkg_conflicts_with
            package_metadata["download_size"] = pkg_download_size
            package_metadata["installed_size"] = pkg_installed_size
            package_metadata["build_date"] = pkg_build_date
            package_metadata["packager"] = pkg_packager

            return package_metadata
        else:
            process_query_local = subprocess.run(
                query_local_str,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=process_timeout,
            )

            # added validation on process result
            if process_query_local.returncode == 0:
                for line in process_query_local.stdout.decode("utf-8").splitlines():
                    if "Name            :" in line.strip():
                        pkg_name = line.replace(" ", "").split("Name:")[1].strip()

                    if "Version         :" in line.strip():
                        pkg_version = line.replace(" ", "").split("Version:")[1].strip()

                    if "Repository      :" in line.strip():
                        pkg_repository = line.split("Repository      :")[1].strip()

                    if "Description     :" in line.strip():
                        pkg_description = line.split("Description     :")[1].strip()

                    if "Architecture    :" in line.strip():
                        pkg_arch = line.split("Architecture    :")[1].strip()

                    if "URL             :" in line.strip():
                        pkg_url = line.split("URL             :")[1].strip()

                    if "Depends On      :" in line.strip():
                        if line.split("Depends On      :")[1].strip() != "None":
                            pkg_depends_on_str = line.split("Depends On      :")[
                                1
                            ].strip()

                            for pkg_dep in pkg_depends_on_str.split("  "):
                                pkg_depends_on.append((pkg_dep, None))
                        else:
                            pkg_depends_on = []

                    if "Conflicts With  :" in line.strip():
                        if line.split("Conflicts With  :")[1].strip() != "None":
                            pkg_conflicts_with_str = line.split("Conflicts With  :")[
                                1
                            ].strip()

                            for pkg_con in pkg_conflicts_with_str.split("  "):
                                pkg_conflicts_with.append((pkg_con, None))
                        else:
                            pkg_conflicts_with = []

                    if "Download Size   :" in line.strip():
                        pkg_download_size = line.split("Download Size   :")[1].strip()

                    if "Installed Size  :" in line.strip():
                        pkg_installed_size = line.split("Installed Size  :")[1].strip()

                    if "Build Date      :" in line.strip():
                        pkg_build_date = line.split("Build Date      :")[1].strip()

                    if "Packager        :" in line.strip():
                        pkg_packager = line.split("Packager        :")[1].strip()

                package_metadata["name"] = pkg_name
                package_metadata["version"] = pkg_version
                package_metadata["repository"] = pkg_repository
                package_metadata["description"] = pkg_description
                package_metadata["arch"] = pkg_arch
                package_metadata["url"] = pkg_url
                package_metadata["depends_on"] = pkg_depends_on
                package_metadata["conflicts_with"] = pkg_conflicts_with
                package_metadata["download_size"] = pkg_download_size
                package_metadata["installed_size"] = pkg_installed_size
                package_metadata["build_date"] = pkg_build_date
                package_metadata["packager"] = pkg_packager

                return package_metadata
            else:
                return str(process_query_local.stdout.decode("utf-8"))
    except Exception as e:
        logger.error("Exception in get_package_information(): %e" % e)


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
        logger.warning("Failed to run %s" % query_str)


def query_pkg(package):
    try:
        package = package.strip()
        path = base_dir + "/cache/installed.lst"

        if os.path.exists(path):
            if is_file_stale(path, 0, 0, 30):
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
        logger.error("Exception in query_pkg(): %s " % e)


# =====================================================
#        PACKAGE DESCRIPTION CACHE AND SEARCH
# =====================================================


def cache(package, path_dir_cache):
    try:
        # first we need to strip the new line escape sequence to ensure we don't get incorrect outcome
        pkg = package.strip()
        # you can see all the errors here with the print command below
        if debug is True:
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
            if debug is True:
                logger.debug("Return code: equals 0 " + str(process.returncode))
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
            if debug is True:
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
        logger.error("Exception in cache(): %s " % e)


# Creating an over-load so that we can use the same function, with slightly different code to get the results we need
def cache_btn():
    # fraction = 1 / len(packages)
    # Non Multithreaded version.
    packages.sort()
    number = 1
    for pkg in packages:
        logger.debug(str(number) + "/" + str(len(packages)) + ": Caching " + pkg)
        cache(pkg, path_dir_cache)
        number = number + 1
        # progressbar.timeout_id = GLib.timeout_add(50, progressbar.update, fraction)

    logger.debug("Caching applications finished")

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


# =====================================================
#               MONITOR PACMAN LOG FILE
# =====================================================


# write lines from the pacman log onto a queue, this is called from a non-blocking thread
def add_pacmanlog_queue(self):
    try:
        lines = []
        with open(pacman_logfile, "r", encoding="utf-8") as f:
            while True:
                line = f.readline()
                if line:
                    lines.append(line.encode("utf-8"))
                    self.pacmanlog_queue.put(lines)
                else:
                    time.sleep(0.5)

    except Exception as e:
        logger.error("Exception in add_pacmanlog_queue() : %s" % e)
    finally:
        logger.debug("No new lines found inside the pacman log file")


# update the textview called from a non-blocking thread
def start_log_timer(self, window_pacmanlog):
    while True:
        if window_pacmanlog.start_logtimer is False:
            logger.debug("Stopping Pacman log monitoring timer")
            return False

        GLib.idle_add(update_textview_pacmanlog, self, priority=GLib.PRIORITY_DEFAULT)
        time.sleep(2)


# update the textview component with new lines from the pacman log file


# To fix: Gtk-CRITICAL **: gtk_text_buffer_emit_insert: assertion 'g_utf8_validate (text, len, NULL)' failed
# Make sure the line read from the pacman log file is encoded in utf-8
# Then decode the line when inserting inside the buffer


def update_textview_pacmanlog(self):
    lines = self.pacmanlog_queue.get()

    try:
        buffer = self.textbuffer_pacmanlog
        if len(lines) > 0:
            end_iter = buffer.get_end_iter()
            for line in lines:
                if len(line) > 0:
                    buffer.insert(
                        end_iter,
                        line.decode("utf-8"),
                        len(line),
                    )

    except Exception as e:
        logger.error("Exception in update_textview_pacmanlog() : %s" % e)
    finally:
        self.pacmanlog_queue.task_done()

        if len(lines) > 0:
            text_mark_end = buffer.create_mark("end", buffer.get_end_iter(), False)
            # auto-scroll the textview to the bottom as new content is added

            self.textview_pacmanlog.scroll_mark_onscreen(text_mark_end)

        lines.clear()


# =====================================================
#               USER SEARCH
# =====================================================


def search(self, term):
    try:
        logger.info('Searching for: "%s"' % term)

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
            elif category_name is None:
                packages_cat.append(pkg_match)
                category_dict[pkg_match.category] = packages_cat
            else:
                # reset packages, new category
                packages_cat = []

                packages_cat.append(pkg_match)

                category_dict[pkg_match.category] = packages_cat

            category_name = pkg_match.category

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
            self.search_queue.put(
                None,
            )

    except Exception as e:
        logger.error("Exception in search(): %s", e)


# =====================================================
#               ARCOLINUX REPOS, KEYS AND MIRRORS
# =====================================================


def append_repo(text):
    """Append a new repo"""
    try:
        with open(pacman_conf, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(text)
    except Exception as e:
        logger.error("Exception in append_repo(): %s" % e)


def repo_exist(value):
    """check repo_exists"""
    with open(pacman_conf, "r", encoding="utf-8") as f:
        lines = f.readlines()
        f.close()

    for line in lines:
        if value in line:
            return True
    return False


def install_arco_keyring():
    try:
        keyring = base_dir + "/packages/arcolinux-keyring/"
        file = os.listdir(keyring)
        cmd_str = [
            "pacman",
            "-U",
            keyring + str(file).strip("[]'"),
            "--noconfirm",
        ]

        logger.debug("%s" % " ".join(cmd_str))

        with subprocess.Popen(
            cmd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            process.wait(process_timeout)

            output = []

            for line in process.stdout:
                output.append(line)

            if process.returncode == 0:
                return 0

            else:
                if len(output) == 0:
                    output.append("Error: install of ArcoLinux keyring failed")

                logger.error(" ".join(output))

                result_err = {}

                result_err["cmd_str"] = cmd_str
                result_err["output"] = output

                return result_err
    except Exception as e:
        logger.error("Exception in install_arco_keyring(): %s" % e)
        result_err = {}

        result_err["cmd_str"] = cmd_str
        result_err["output"] = e

        return result_err


def remove_arco_keyring():
    try:
        cmd_str = ["pacman", "-Rdd", "arcolinux-keyring", "--noconfirm"]
        with subprocess.Popen(
            cmd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            process.wait(process_timeout)

            output = []

            for line in process.stdout:
                output.append(line)

            if process.returncode == 0:
                return 0

            else:
                if len(output) == 0:
                    output.append("Error: removal of ArcoLinux keyring failed")

                logger.error(" ".join(output))

                result_err = {}

                result_err["cmd_str"] = cmd_str
                result_err["output"] = output

                return result_err

    except Exception as e:
        logger.error("Exception in remove_arco_keyring(): %s" % e)

        result_err = {}

        result_err["cmd_str"] = cmd_str
        result_err["output"] = e

        return result_err


def install_arco_mirrorlist():
    try:
        mirrorlist = base_dir + "/packages/arcolinux-mirrorlist/"
        file = os.listdir(mirrorlist)
        cmd_str = [
            "pacman",
            "-U",
            mirrorlist + str(file).strip("[]'"),
            "--noconfirm",
        ]

        logger.debug("%s" % " ".join(cmd_str))
        with subprocess.Popen(
            cmd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            process.wait(process_timeout)

            output = []

            for line in process.stdout:
                output.append(line)

            if process.returncode == 0:
                return 0

            else:
                if len(output) == 0:
                    output.append("Error: install of ArcoLinux mirrorlist failed")

                logger.error(" ".join(output))

                result_err = {}

                result_err["cmd_str"] = cmd_str
                result_err["output"] = output

                return result_err
    except Exception as e:
        logger.error("Exception in install_arco_mirrorlist(): %s" % e)

        result_err = {}

        result_err["cmd_str"] = cmd_str
        result_err["output"] = output

        return result_err


def remove_arco_mirrorlist():
    try:
        cmd_str = ["pacman", "-Rdd", "arcolinux-mirrorlist-git", "--noconfirm"]
        logger.debug("%s" % " ".join(cmd_str))
        with subprocess.Popen(
            cmd_str,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True,
        ) as process:
            process.wait(process_timeout)

            output = []

            for line in process.stdout:
                output.append(line)

            if process.returncode == 0:
                return 0

            else:
                if len(output) == 0:
                    output.append("Error: removal of ArcoLinux mirrorlist failed")

                logger.error(" ".join(output))

                result_err = {}

                result_err["cmd_str"] = cmd_str
                result_err["output"] = output

                return result_err

    except Exception as e:
        logger.error("Exception in remove_arco_mirrorlist(): %s" % e)

        result_err = {}

        result_err["cmd_str"] = cmd_str
        result_err["output"] = e

        return result_err


def add_arco_repos():
    logger.info("Adding ArcoLinux repos on %s" % distr)
    try:
        # first check if arco repos are already inside pacman conf file

        if verify_arco_pacman_conf() is False:
            # take backup of existing pacman.conf file

            if os.path.exists(pacman_conf):
                shutil.copy(pacman_conf, pacman_conf_backup)

                # read existing contents from pacman.conf file

                logger.info("Reading from %s" % pacman_conf)

                lines = []

                with open(pacman_conf, "r", encoding="utf-8") as r:
                    lines = r.readlines()

                # check for existing ArcoLinux entries
                if len(lines) > 0:
                    arco_test_repo_found = False
                    arco_repo_found = False
                    arco_3rd_party_repo_found = False
                    arco_xlrepo_found = False

                    for line in lines:
                        if "#" in line.strip():
                            if arco_test_repo[0].replace("#", "") in line.strip():
                                arco_test_repo_found = True

                            if arco_repo[0].replace("#", "") in line.strip():
                                arco_repo_found = True
                                index = lines.index(line)

                                del lines[index]
                                lines.insert(index, arco_repo[0])

                                index += 1

                                del lines[index]
                                lines.insert(index, arco_repo[1])

                                index += 1

                                del lines[index]
                                lines.insert(index, arco_repo[2])

                            if arco_3rd_party_repo[0].replace("#", "") in line.strip():
                                arco_3rd_party_repo_found = True
                                index = lines.index(line)

                                del lines[index]
                                lines.insert(index, arco_3rd_party_repo[0])

                                index += 1

                                del lines[index]
                                lines.insert(index, arco_3rd_party_repo[1])

                                index += 1

                                del lines[index]
                                lines.insert(index, arco_3rd_party_repo[2])

                            if arco_xlrepo[0].replace("#", "") in line.strip():
                                arco_xlrepo_found = True
                                index = lines.index(line)

                                del lines[index]
                                lines.insert(index, arco_xlrepo[0])

                                index += 1

                                del lines[index]
                                lines.insert(index, arco_xlrepo[1])

                                index += 1

                                del lines[index]
                                lines.insert(index, arco_xlrepo[2])

                        if line.strip() == arco_test_repo[0]:
                            arco_test_repo_found = True

                        if line.strip() == arco_repo[0]:
                            arco_repo_found = True

                        if line.strip() == arco_3rd_party_repo[0]:
                            arco_3rd_party_repo_found = True

                        if line.strip() == arco_xlrepo[0]:
                            arco_xlrepo_found = True

                    if arco_test_repo_found is False:
                        lines.append("\n")

                        for arco_test_repo_line in arco_test_repo:
                            lines.append(arco_test_repo_line)

                    if arco_repo_found is False:
                        lines.append("\n")

                        for arco_repo_line in arco_repo:
                            lines.append(arco_repo_line)

                    if arco_3rd_party_repo_found is False:
                        lines.append("\n")

                        for arco_3rd_party_repo_line in arco_3rd_party_repo:
                            lines.append(arco_3rd_party_repo_line)

                    if arco_xlrepo_found is False:
                        lines.append("\n")

                        for arco_xlrepo_line in arco_xlrepo:
                            lines.append(arco_xlrepo_line)

                    logger.info("[Add ArcoLinux repos] Writing to %s" % pacman_conf)

                    if len(lines) > 0:
                        with open(pacman_conf, "w", encoding="utf-8") as w:
                            for l in lines:
                                w.write(l.strip() + "\n")

                            w.flush()

                        return 0

                    else:
                        logger.error("Failed to process %s" % pacman_conf)

                else:
                    logger.error("Failed to read %s" % pacman_conf)
        else:
            logger.info("ArcoLinux repos already setup inside pacman conf file")
            return 0

    except Exception as e:
        logger.error("Exception in add_arco_repos(): %s" % e)
        return e


def remove_arco_repos():
    # remove the ArcoLinux repos in /etc/pacman.conf
    try:
        # check for existing ArcoLinux entries and remove
        if verify_arco_pacman_conf() is True:
            if os.path.exists(pacman_conf):
                shutil.copy(pacman_conf, pacman_conf_backup)

                logger.info("Reading from %s" % pacman_conf)

                lines = []

                with open(pacman_conf, "r", encoding="utf-8") as r:
                    lines = r.readlines()

                if len(lines) > 0:
                    index = 0

                    for line in lines:
                        if arco_test_repo[0] == line.strip().replace(" ", ""):
                            index = lines.index(line)

                            if index > 0:
                                if distr != "arcolinux":
                                    del lines[index]
                                    del lines[index]
                                    del lines[index]

                        # make sure the arco testing repo is disabled, if absolutely required update the pacman conf file manually and enable them

                        if "%s" % arco_test_repo[0].replace("#", "") == line.strip():
                            index = lines.index(
                                "%s\n" % arco_test_repo[0].replace("#", "")
                            )
                            if distr != "arcolinux":
                                del lines[index]
                                del lines[index]
                                del lines[index]
                            else:
                                # comment out the testing repo

                                lines[index] = "%s\n" % arco_test_repo[0]
                                lines[index + 1] = "%s\n" % arco_test_repo[1]
                                lines[index + 2] = "%s\n" % arco_test_repo[2]

                        if "%s\n" % arco_repo[0] == line:
                            index = lines.index("%s\n" % arco_repo[0])

                            if index > 0:
                                if distr != "arcolinux":
                                    del lines[index]
                                    del lines[index]
                                    del lines[index]
                                else:
                                    lines[index] = "#%s\n" % arco_repo[0]
                                    lines[index + 1] = "#%s\n" % arco_repo[1]
                                    lines[index + 2] = "#%s\n" % arco_repo[2]
                        elif (
                            "#" in line.strip()
                            and arco_repo[0] == line.replace("#", "").strip()
                            and distr != "arcolinux"
                        ):
                            # check if already commented

                            index = lines.index(line)
                            del lines[index]
                            del lines[index]
                            del lines[index]

                        if "%s\n" % arco_3rd_party_repo[0] == line:
                            index = lines.index("%s\n" % arco_3rd_party_repo[0])

                            if index > 0:
                                if distr != "arcolinux":
                                    del lines[index]
                                    del lines[index]
                                    del lines[index]
                                else:
                                    lines[index] = "#%s\n" % arco_3rd_party_repo[0]
                                    lines[index + 1] = "#%s\n" % arco_3rd_party_repo[1]
                                    lines[index + 2] = "#%s\n" % arco_3rd_party_repo[2]
                        elif (
                            "#" in line.strip()
                            and arco_3rd_party_repo[0] == line.replace("#", "").strip()
                            and distr != "arcolinux"
                        ):
                            # check if already commented

                            index = lines.index(line)
                            del lines[index]
                            del lines[index]
                            del lines[index]

                        if "%s\n" % arco_xlrepo[0] == line:
                            index = lines.index("%s\n" % arco_xlrepo[0])

                            if index > 0:
                                if distr != "arcolinux":
                                    del lines[index]
                                    del lines[index]
                                    del lines[index]
                                else:
                                    lines[index] = "#%s\n" % arco_xlrepo[0]
                                    lines[index + 1] = "#%s\n" % arco_xlrepo[1]
                                    lines[index + 2] = "#%s\n" % arco_xlrepo[2]
                        elif (
                            "#" in line.strip()
                            and arco_xlrepo[0] == line.replace("#", "").strip()
                            and distr != "arcolinux"
                        ):
                            # check if already commented

                            index = lines.index(line)
                            del lines[index]
                            del lines[index]
                            del lines[index]

                    # remove any white spaces from end of the file only if on non arcolinux system
                    # on any non arcolinux distro lines are deleted which leaves empty lines in the file
                    # causing the file to grow in size
                    if distr != "arcolinux":
                        if lines[-1] == "\n":
                            del lines[-1]

                        if lines[-2] == "\n":
                            del lines[-2]

                        if lines[-3] == "\n":
                            del lines[-3]

                        if lines[-4] == "\n":
                            del lines[-4]

                    logger.info("[Remove ArcoLinux Repos] Writing to %s" % pacman_conf)

                    if len(lines) > 0:
                        with open(pacman_conf, "w") as w:
                            w.writelines(lines)

                            w.flush()

                        return 0

                    else:
                        logger.error("Failed to process %s" % pacman_conf)

                else:
                    logger.error("Failed to read %s" % pacman_conf)
        else:
            logger.info("No ArcoLinux repos setup inside pacman conf file")
            return 0

    except Exception as e:
        logger.error("Exception in remove_arco_repos(): %s" % e)
        return e


# check if pacman.conf has arco repos setup


def verify_arco_pacman_conf():
    try:
        lines = None
        arco_repo_setup = False
        arco_3rd_party_repo_setup = False
        arco_xlrepo_setup = False
        with open(pacman_conf, "r") as r:
            lines = r.readlines()

        if lines is not None:
            for line in lines:
                if arco_repo[0] in line.strip():
                    if "#" not in line.strip():
                        arco_repo_setup = True
                    else:
                        return False

                if arco_3rd_party_repo[0] in line.strip():
                    if "#" not in line.strip():
                        arco_3rd_party_repo_setup = True
                    else:
                        return False

                if arco_xlrepo[0] in line.strip():
                    if "#" not in line.strip():
                        arco_xlrepo_setup = True
                    else:
                        return False

            if (
                arco_repo_setup is True
                and arco_3rd_party_repo_setup is True
                and arco_xlrepo_setup is True
            ):
                return True
            else:
                return False
    except Exception as e:
        logger.error("Exception in check_arco_pacman(): %s" % e)


# =====================================================
#               CHECK IF PACKAGE IS INSTALLED
# =====================================================


# check if package is installed or not
def check_package_installed(package_name):
    # query_str = ["pacman", "-Qi", package]
    query_str = ["pacman", "-Qq"]
    try:
        process_pkg_installed = subprocess.run(
            query_str,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=process_timeout,
            universal_newlines=True,
        )

        if package_name in process_pkg_installed.stdout.splitlines():
            return True
        else:
            return False

    except subprocess.CalledProcessError:
        # package is not installed
        return False


# =====================================================
#               CHECK RUNNING PROCESS
# =====================================================


def check_if_process_running(process_name):
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=["pid", "name", "create_time"])
            if process_name == pinfo["pid"]:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


# =====================================================
#               NOTIFICATIONS
# =====================================================


def show_in_app_notification(self, message, err):
    if self.timeout_id is not None:
        GLib.source_remove(self.timeout_id)
        self.timeout_id = None

    if err is True:
        self.notification_label.set_markup(
            '<span background="yellow" foreground="black">' + message + "</span>"
        )
    else:
        self.notification_label.set_markup(
            '<span foreground="white">' + message + "</span>"
        )
    self.notification_revealer.set_reveal_child(True)
    self.timeout_id = GLib.timeout_add(3000, timeout, self)


def timeout(self):
    close_in_app_notification(self)


def close_in_app_notification(self):
    self.notification_revealer.set_reveal_child(False)
    GLib.source_remove(self.timeout_id)
    self.timeout_id = None


def reveal_infobar(self, progress_dialog):
    progress_dialog.infobar.set_revealed(True)
    progress_dialog.infobar.show_all()
    GLib.source_remove(self.timeout_id)
    self.timeout_id = None


"""
    Since the app could be quit/terminated at any time during a pacman transaction.
    The pacman process spawned by the install/uninstall threads, needs to be terminated too.
    Otherwise the app may hang waiting for pacman to complete its transaction.
"""
# =====================================================
#              PACMAN
# =====================================================


def terminate_pacman():
    try:
        process_found = False
        for proc in psutil.process_iter():
            try:
                pinfo = proc.as_dict(attrs=["pid", "name", "create_time"])
                if pinfo["name"] == "pacman":
                    process_found = True
                    logger.debug("Killing pacman process = %s" % pinfo["name"])

                    proc.kill()

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if process_found is True:
            if check_pacman_lockfile():
                os.unlink(pacman_lockfile)
    except Exception as e:
        logger.error("Exception in terminate_pacman() : %s" % e)


def is_thread_alive(thread_name):
    for thread in threading.enumerate():
        if thread.name == thread_name and thread.is_alive():
            return True

    return False


def print_running_threads():
    threads_alive = []
    for thread in threading.enumerate():
        if thread.is_alive():
            threads_alive.append(thread.name)

    for th in threads_alive:
        logger.debug("Thread = %s status = alive" % th)


# this keeps monitoring for items on the package holding queue
# items are added to the queue if a package install is stuck behind another pacman transaction
def check_holding_queue(self):
    while True:
        (
            package,
            action,
            widget,
            inst_str,
            progress_dialog,
        ) = self.pkg_holding_queue.get()

        try:
            # logger.debug("Enqueued package = %s" % package.name)

            while check_pacman_lockfile() is True:
                # logger.debug("Pacman is processing a transaction")
                time.sleep(0.2)

            if action == "install":
                th_subprocess_install = Thread(
                    name="thread_subprocess",
                    target=start_subprocess,
                    args=(
                        self,
                        inst_str,
                        progress_dialog,
                        action,
                        package,
                        widget,
                    ),
                    daemon=True,
                )

                th_subprocess_install.start()

        finally:
            self.pkg_holding_queue.task_done()


# check if pacman lock file exists
def check_pacman_lockfile():
    try:
        if os.path.exists(pacman_lockfile):
            # logger.debug("Pacman lockfile found inside %s" % pacman_lockfile)
            # logger.debug("Another pacman process is running")
            return True
        else:
            # logger.info("No pacman lockfile found, OK to proceed")
            return False
    except Exception as e:
        logger.error("Exception in check_pacman_lockfile() : %s" % e)


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
        logger.error("Exception in get_pacman_process() : %s" % e)


# ANYTHING UNDER THIS LINE IS CURRENTLY UNUSED!
