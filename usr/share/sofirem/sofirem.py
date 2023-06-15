#!/usr/bin/env python3

import gi
import os
import Functions as fn
import signal

import subprocess
from Functions import os
from queue import Queue
from time import sleep
import sys
import time

# UI modules
from ui.GUI import GUI
from ui.SplashScreen import SplashScreen
from ui.ProgressBarWindow import ProgressBarWindow
from ui.AppFrameGUI import AppFrameGUI
from ui.AboutDialog import AboutDialog
from ui.MessageDialog import MessageDialog
from ui.PacmanLogWindow import PacmanLogWindow
from ui.PackageListDialog import PackageListDialog
from ui.ProgressDialog import ProgressDialog
from ui.ISOPackagesWindow import ISOPackagesWindow

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

#      #============================================================
#      #=  Authors:  Erik Dubois - Cameron Percival   - Fennec     =
#      #============================================================

# Folder structure

# cache contains descriptions - inside we have corrections for manual intervention
# + installed applications list
# yaml is the folder that is used to create the application
# yaml-awesome is a copy/paste from Calamares to meld manually - not used in the app

base_dir = os.path.dirname(os.path.realpath(__file__))
debug = True


class Main(Gtk.Window):
    # Create a queue, for worker communication (Multithreading - used in GUI layer)
    queue = Queue()

    # Create a queue to handle package install/removal
    pkg_queue = Queue()

    # Create a queue for storing search results
    search_queue = Queue()

    # Create a queue for storing Pacman log file contents
    pacmanlog_queue = Queue()

    # Create a queue for storing packages waiting behind an in-progress pacman transaction
    pkg_holding_queue = Queue()

    def __init__(self):
        try:
            super(Main, self).__init__(title="Sofirem")

            self.set_border_width(10)
            self.connect("delete-event", self.on_close)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))
            self.set_default_size(1100, 900)

            # ctrl+f give focus to search entry
            self.connect("key-press-event", self.on_keypress_event)

            # used for notifications
            self.timeout_id = None

            # default: displaying versions are disabled
            self.display_versions = False

            # initial app load search_activated is set to False
            self.search_activated = False

            # initial app load show the progress dialog window when a package is installed/uninstalled
            self.show_progress_dialog = True

            print(
                "---------------------------------------------------------------------------"
            )
            print("If you have errors, report it on the discord channel of ArcoLinux")
            print(
                "---------------------------------------------------------------------------"
            )
            print("You can receive support on https://discord.gg/stBhS4taje")
            print(
                "---------------------------------------------------------------------------"
            )
            print(
                "Many applications are coming from the Arch Linux repos and can be installed"
            )
            print(
                "without any issues. Other applications are available from third party repos"
            )
            print("like Chaotic repo, ArcoLinux repo and others.")
            print(
                "---------------------------------------------------------------------------"
            )
            print("We do NOT build packages from AUR.")
            print(
                "---------------------------------------------------------------------------"
            )
            print("Some packages are only available on the ArcoLinux repos.")
            print(
                "---------------------------------------------------------------------------"
            )

            splash_screen = SplashScreen()

            while Gtk.events_pending():
                Gtk.main_iteration()

            sleep(3)
            splash_screen.destroy()

            # Fetch list of packages already installed before the app makes changes
            fn.create_packages_log()

            if not os.path.isfile(fn.sofirem_lockfile):
                with open(fn.sofirem_lockfile, "w") as f:
                    f.write("")

                # test there is no pacman lock file on the system
                if fn.check_pacman_lockfile():
                    message_dialog = MessageDialog(
                        "Error",
                        "Sofirem cannot proceed pacman lockfile found",
                        "Pacman cannot lock the db, a lockfile is found inside %s"
                        % fn.pacman_lockfile,
                        "Is there another Pacman process running ?",
                        "error",
                        False,
                    )
                    message_dialog.show_all()
                    message_dialog.run()
                    message_dialog.hide()

                    sys.exit(1)

                fn.logger.info("pkgver = pkgversion")
                fn.logger.info("pkgrel = pkgrelease")
                print(
                    "---------------------------------------------------------------------------"
                )
                fn.logger.info("Distro = " + fn.distr)
                print(
                    "---------------------------------------------------------------------------"
                )

                # Create installed.lst file for first time
                fn.get_current_installed()
                fn.logger.info("Created installed.lst")

                # start making sure sofirem starts next time with dark or light theme
                if os.path.isdir(fn.home + "/.config/gtk-3.0"):
                    try:
                        if not os.path.islink("/root/.config/gtk-3.0"):
                            if os.path.exists("/root/.config/gtk-3.0"):
                                fn.shutil.rmtree("/root/.config/gtk-3.0")

                            fn.shutil.copytree(
                                fn.home + "/.config/gtk-3.0", "/root/.config/gtk-3.0"
                            )
                    except Exception as e:
                        fn.logger.warning("GTK config: %s" % e)

                if os.path.isdir("/root/.config/xsettingsd/xsettingsd.conf"):
                    try:
                        if not os.path.islink("/root/.config/xsettingsd/"):
                            if os.path.exists("/root/.config/xsettingsd/"):
                                fn.shutil.rmtree("/root/.config/xsettingsd/")
                            if fn.path.isdir(fn.home + "/.config/xsettingsd/"):
                                fn.shutil.copytree(
                                    fn.home + "/.config/xsettingsd/",
                                    "/root/.config/xsettingsd/",
                                )
                    except Exception as e:
                        fn.logger.warning("xsettingsd config: %s" % e)

                # pacman sync db and also tests network connectivity

                if self.pacman_db_sync() is True:
                    # store package information into memory, and use the dictionary returned to search in for quicker retrieval
                    fn.logger.info("Storing package metadata started")

                    self.packages = fn.store_packages()
                    fn.logger.info("Storing package metadata completed")

                    fn.logger.info("Categories = %s" % len(self.packages.keys()))

                    total_packages = 0

                    for category in self.packages:
                        total_packages += len(self.packages[category])

                    fn.logger.info("Total packages = %s" % total_packages)

                    fn.logger.info("Setting up GUI")

                    GUI.setup_gui(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)

                else:
                    sys.exit(1)

            else:
                fn.logger.error("Sofirem lock file found in %s" % fn.sofirem_lockfile)

        except Exception as e:
            fn.logger.error("Exception in Main() : %s" % e)

    # =====================================================
    #               PACMAN DB SYNC
    # =====================================================

    def pacman_db_sync(self):
        sync_err = fn.sync_package_db()

        if sync_err is not None:
            fn.logger.error("Pacman db synchronisation failed")

            print(
                "---------------------------------------------------------------------------"
            )

            message_dialog = MessageDialog(
                "Error",
                "Pacman db synchronisation failed",
                "Failed to run command = pacman -Sy\nPacman db synchronisation failed\nCheck the synchronisation logs, and verify you can connect to the appropriate mirrors\n\n",
                sync_err,
                "error",
                True,
            )

            message_dialog.show_all()
            message_dialog.run()
            message_dialog.hide()

            return False

        else:
            fn.logger.info("Pacman synchronisation completed")

            return True

    # =====================================================
    #               WINDOW KEY EVENT CTRL + F
    # =====================================================

    # sets focus on the search entry
    def on_keypress_event(self, widget, event):
        shortcut = Gtk.accelerator_get_label(event.keyval, event.state)

        if shortcut in ("Ctrl+F", "Ctrl+Mod2+F"):
            # set focus on text entry, select all text if any
            self.searchentry.grab_focus()

        if shortcut in ("Ctrl+I", "Ctrl+Mod2+I"):
            fn.show_package_info(self)

    # =====================================================
    #               SEARCH ENTRY
    # =====================================================

    def on_search_activated(self, searchentry):
        if searchentry.get_text_length() == 0 and self.search_activated:
            GUI.setup_gui(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)
            self.search_activated = False

        if searchentry.get_text_length() == 0:
            self.search_activated = False

        search_term = searchentry.get_text()
        # if the string is completely whitespace ignore searching
        if not search_term.isspace():
            try:
                if len(search_term.rstrip().lstrip()) > 0:
                    # test if the string entered by the user is in the package name
                    # results is a dictionary, which holds a list of packages
                    # results[category]=pkg_list

                    # searching is processed inside a thread

                    th_search = fn.threading.Thread(
                        name="thread_search",
                        target=fn.search,
                        args=(
                            self,
                            search_term.rstrip().lstrip(),
                        ),
                    )
                    fn.logger.info("Starting search")

                    th_search.start()

                    # get the search_results from the queue
                    results = self.search_queue.get()

                    if results is not None:
                        fn.logger.info("Search complete")

                        if len(results) > 0:
                            total = 0
                            for val in results.values():
                                total += len(val)

                            fn.logger.info("Search found %s results" % total)
                            # make sure the gui search only displays the pkgs inside the results

                            GUI.setup_gui_search(
                                self,
                                Gtk,
                                Gdk,
                                GdkPixbuf,
                                base_dir,
                                os,
                                Pango,
                                results,
                                search_term,
                            )

                            self.search_activated = True
                    else:
                        fn.logger.info("Search found %s results" % 0)
                        self.searchentry.grab_focus()

                        message_dialog = MessageDialog(
                            "Info",
                            "Search returned 0 results",
                            "Failed to find search term inside the package name or description.",
                            "Try to search again using another term",
                            "warning",
                            False,
                        )

                        message_dialog.show_all()
                        message_dialog.run()
                        message_dialog.hide()

                elif self.search_activated == True:
                    GUI.setup_gui(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)
                    self.search_activated = False
            except Exception as err:
                fn.logger.error("Exception in on_search_activated(): %s" % err)

            finally:
                if self.search_activated == True:
                    self.search_queue.task_done()

    def on_search_cleared(self, searchentry, icon_pos, event):
        if self.search_activated:
            GUI.setup_gui(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)

        self.searchentry.set_placeholder_text("Search...")

        self.search_activated = False

    # =====================================================
    #               RESTART/QUIT BUTTON
    # =====================================================

    def on_close(self, widget, data):
        # make a final installed packages file inside /var/log/sofirem/$DATE
        # this allows a before/after comparison
        fn.create_packages_log()
        if os.path.exists(fn.sofirem_lockfile):
            os.unlink(fn.sofirem_lockfile)

        if os.path.exists(fn.sofirem_pidfile):
            os.unlink(fn.sofirem_pidfile)

        # see the comment in fn.terminate_pacman()
        fn.terminate_pacman()

        Gtk.main_quit()
        print(
            "---------------------------------------------------------------------------"
        )
        print("Thanks for using Sofirem")
        print("Report issues to make it even better")
        print(
            "---------------------------------------------------------------------------"
        )
        print("You can report issues on https://discord.gg/stBhS4taje")
        print(
            "---------------------------------------------------------------------------"
        )

    # ====================================================================
    #                     Button Functions
    # ====================================================================
    # Given what this function does, it might be worth considering making it a
    # thread so that the app doesn't block while installing/uninstalling is happening.

    def app_toggle(self, widget, active, package):
        # switch widget is currently toggled off

        if widget.get_state() == False and widget.get_active() == True:
            if len(package.name) > 0:
                inst_str = [
                    "pacman",
                    "-S",
                    package.name,
                    "--needed",
                    "--noconfirm",
                ]

                if self.show_progress_dialog is True:
                    if fn.check_pacman_lockfile():
                        widget.set_state(False)
                        widget.set_active(False)
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
                        message_dialog.run()
                        message_dialog.hide()
                        return True
                    else:
                        package_metadata = fn.get_package_information(package.name)

                        if (
                            type(package_metadata) is str
                            and package_metadata.strip()
                            == "error: package '%s' was not found" % package.name
                        ):
                            self.package_found = False
                            fn.logger.warning(
                                "The package %s was not found in any configured Pacman repositories"
                                % package.name
                            )
                            fn.logger.warning("Package install cannot continue")

                            message_dialog = MessageDialog(
                                "Error",
                                "Pacman repository error: package '%s' was not found"
                                % package.name,
                                "Sofirem cannot process the request",
                                "Are the correct pacman mirrorlists configured ?",
                                "error",
                                False,
                            )
                            message_dialog.show_all()
                            message_dialog.run()
                            message_dialog.hide()

                            widget.set_state(False)
                            widget.set_active(False)

                            return True
                        else:
                            widget.set_state(True)
                            widget.set_active(True)

                            progress_dialog = ProgressDialog(
                                "install",
                                package,
                                " ".join(inst_str),
                                package_metadata,
                            )

                            progress_dialog.show_all()

                            self.pkg_queue.put(
                                (
                                    package,
                                    "install",
                                    widget,
                                    inst_str,
                                    progress_dialog,
                                ),
                            )

                            th = fn.threading.Thread(
                                name="thread_pkginst",
                                target=fn.install,
                                args=(self,),
                                daemon=True,
                            )

                            th.start()
                            fn.logger.debug("Package-install thread started")

                else:
                    progress_dialog = None
                    widget.set_sensitive(False)

                widget.set_active(True)
                widget.set_state(True)

                fn.logger.info("Package to install : %s" % package.name)

                # another pacman transaction is running, add items to the holding queue
                if (
                    fn.check_pacman_lockfile() is True
                    and self.show_progress_dialog is False
                ):
                    self.pkg_holding_queue.put(
                        (
                            package,
                            "install",
                            widget,
                            inst_str,
                            progress_dialog,
                        ),
                    )

                    if fn.is_thread_alive("thread_check_holding_queue") is False:
                        th = fn.threading.Thread(
                            target=fn.check_holding_queue,
                            name="thread_check_holding_queue",
                            daemon=True,
                            args=(self,),
                        )

                        th.start()
                        fn.logger.debug("Check-holding-queue thread started")
                elif self.show_progress_dialog is False:
                    self.pkg_queue.put(
                        (
                            package,
                            "install",
                            widget,
                            inst_str,
                            progress_dialog,
                        ),
                    )

                    th = fn.threading.Thread(
                        name="thread_pkginst",
                        target=fn.install,
                        args=(self,),
                        daemon=True,
                    )

                    th.start()
                    fn.logger.debug("Package-install thread started")

        # switch widget is currently toggled on
        if widget.get_state() == True and widget.get_active() == False:
            # Uninstall the package

            if len(package.name) > 0:
                uninst_str = ["pacman", "-Rs", package.name, "--noconfirm"]
                widget.set_active(False)
                widget.set_state(False)

                fn.logger.info("Package to remove : %s" % package.name)

                if self.show_progress_dialog is True:
                    package_metadata = fn.get_package_information(package.name)

                    progress_dialog = ProgressDialog(
                        "uninstall",
                        package,
                        " ".join(uninst_str),
                        package_metadata,
                    )

                    progress_dialog.show_all()
                else:
                    progress_dialog = None

                self.pkg_queue.put(
                    (
                        package,
                        "uninstall",
                        widget,
                        uninst_str,
                        progress_dialog,
                    ),
                )

                th = fn.threading.Thread(
                    name="thread_pkgrem",
                    target=fn.uninstall,
                    args=(self,),
                    daemon=True,
                )

                th.start()
                fn.logger.debug("Package-uninstall thread started")

        # fn.print_running_threads()

        # return True to prevent the default handler from running
        return True

        # App_Frame_GUI.GUI(self, Gtk, vboxStack1, fn, category, package_file)
        # widget.get_parent().get_parent().get_parent().get_parent().get_parent().get_parent().get_parent().queue_redraw()
        # self.gui.hide()
        # self.gui.queue_redraw()
        # self.gui.show_all()

    def recache_clicked(self, widget):
        # Check if cache is out of date. If so, run the re-cache, if not, don't.
        # pb = ProgressBarWindow()
        # pb.show_all()
        # pb.set_text("Updating Cache")
        # pb.reset_timer()

        fn.logger.info("Recache applications - start")

        fn.cache_btn()

    # ================================================================
    #                   SETTINGS
    # ================================================================

    def on_arcolinux_iso_packages_clicked(self, widget):
        fn.logger.debug("Showing ArcoLinux ISO Packages window")
        arcolinux_iso_packages_window = ISOPackagesWindow()
        arcolinux_iso_packages_window.show()

    def on_about_app_clicked(self, widget):
        fn.logger.debug("Showing About dialog")
        self.toggle_popover()

        about = AboutDialog()
        about.run()
        about.hide()
        about.destroy()

    def on_packages_export_clicked(self, widget):
        self.toggle_popover()

        dialog_packagelist = PackageListDialog()
        dialog_packagelist.show_all()

    def on_packages_import_clicked(self, widget):
        self.toggle_popover()

        fn.package_import()

    # show/hide popover
    def toggle_popover(self):
        if self.popover.get_visible():
            self.popover.hide()
        else:
            self.popover.show_all()

    def on_settings_clicked(self, widget):
        self.toggle_popover()

    # ArcoLinux keys, mirrors setup

    def arco_keyring_toggle(self, widget, data):
        # toggle is currently off, add keyring
        if widget.get_state() == False and widget.get_active() == True:
            fn.logger.info("Installing ArcoLinux keyring")
            install_keyring = fn.install_arco_keyring()

            if install_keyring == 0:
                fn.logger.info("Installation of ArcoLinux keyring = OK")
                rc = fn.add_arco_repos()
                if rc == 0:
                    fn.logger.info("ArcoLinux repos added into %s" % fn.pacman_conf)
                    widget.set_active(True)
                else:
                    message_dialog = MessageDialog(
                        "Error",
                        "Failed to update pacman conf",
                        "Errors occurred during update of the pacman config file",
                        rc,
                        "error",
                        True,
                    )

                    message_dialog.show_all()
                    message_dialog.run()
                    message_dialog.hide()

                    widget.set_active(False)
                    widget.set_state(False)

                    return True

            else:
                message_dialog = MessageDialog(
                    "Error",
                    "Failed to install ArcoLinux keyring",
                    "Errors occurred during install of the ArcoLinux keyring",
                    "Command run = %s\n\n Error = %s"
                    % (install_keyring["cmd_str"], install_keyring["output"]),
                    "error",
                    True,
                )

                message_dialog.show_all()
                message_dialog.run()
                message_dialog.hide()

                widget.set_active(False)
                widget.set_state(False)

                return True
        # toggle is currently on
        if widget.get_state() == True and widget.get_active() == False:
            remove_keyring = fn.remove_arco_keyring()

            if remove_keyring == 0:
                fn.logger.info("Removing ArcoLinux keyring OK")

                rc = fn.remove_arco_repos()
                if rc == 0:
                    fn.logger.info("ArcoLinux repos removed from %s" % fn.pacman_conf)
                    widget.set_active(False)
                else:
                    message_dialog = MessageDialog(
                        "Error",
                        "Failed to update pacman conf",
                        "Errors occurred during update of the pacman config file",
                        rc,
                        "error",
                        True,
                    )

                    message_dialog.show_all()
                    message_dialog.run()
                    message_dialog.hide()

                    widget.set_active(True)
                    widget.set_state(True)

                    return True
            else:
                fn.logger.error("Failed to remove ArcoLinux keyring")

                message_dialog = MessageDialog(
                    "Error",
                    "Failed to remove ArcoLinux keyring",
                    "Errors occurred during removal of the ArcoLinux keyring",
                    "Command run = %s\n\n Error = %s"
                    % (remove_keyring["cmd_str"], remove_keyring["output"]),
                    "error",
                    True,
                )

                message_dialog.show_all()
                message_dialog.run()
                message_dialog.hide()

                widget.set_active(False)
                widget.set_state(False)

                return True

    def arco_mirrorlist_toggle(self, widget, data):
        # self.toggle_popover()

        # toggle is currently off

        if widget.get_state() == False and widget.get_active() == True:
            widget.set_active(True)
            widget.set_state(True)

            # before installing the mirrorlist make sure the pacman.conf file does not have any references to /etc/pacman.d/arcolinux-mirrorlist
            # otherwise the mirrorlist package will not install
            rc_remove = fn.remove_arco_repos()
            if rc_remove == 0:
                install_mirrorlist = fn.install_arco_mirrorlist()

                if install_mirrorlist == 0:
                    fn.logger.info("Installation of ArcoLinux mirrorlist = OK")

                    rc_add = fn.add_arco_repos()
                    if rc_add == 0:
                        fn.logger.info("ArcoLinux repos added into %s" % fn.pacman_conf)
                        self.pacman_db_sync()

                    else:
                        message_dialog = MessageDialog(
                            "Error",
                            "Failed to update pacman conf",
                            "Errors occurred during update of the pacman config file",
                            rc_add,
                            "error",
                            True,
                        )

                        message_dialog.show_all()
                        message_dialog.run()
                        message_dialog.hide()

                        widget.set_active(False)
                        widget.set_state(False)

                        return True

                else:
                    fn.logger.error("Failed to install ArcoLinux mirrorlist")

                    message_dialog = MessageDialog(
                        "Error",
                        "Failed to install ArcoLinux mirrorlist",
                        "Errors occurred during install of the ArcoLinux mirrorlist",
                        "Command run = %s\n\n Error = %s"
                        % (install_mirrorlist["cmd_str"], install_mirrorlist["output"]),
                        "error",
                        True,
                    )
                    message_dialog.show_all()
                    message_dialog.run()
                    message_dialog.hide()

                    widget.set_active(False)
                    widget.set_state(False)

                    return True
            else:
                message_dialog = MessageDialog(
                    "Error",
                    "Failed to update pacman conf",
                    "Errors occurred during update of the pacman config file",
                    rc,
                    "error",
                    True,
                )

                message_dialog.show_all()
                message_dialog.run()
                message_dialog.hide()

                widget.set_active(False)
                widget.set_state(False)

                return True
        # toggle is currently on
        if widget.get_state() == True and widget.get_active() == False:
            widget.set_active(False)
            widget.set_state(False)

            fn.logger.info("Removing ArcoLinux mirrorlist")

            remove_mirrorlist = fn.remove_arco_mirrorlist()

            if remove_mirrorlist == 0:
                fn.logger.info("Removing ArcoLinux mirrorlist OK")

                rc = fn.remove_arco_repos()
                if rc == 0:
                    fn.logger.info("ArcoLinux repos removed from %s" % fn.pacman_conf)
                    widget.set_active(False)
                else:
                    message_dialog = MessageDialog(
                        "Error",
                        "Failed to update pacman conf",
                        "Errors occurred during update of the pacman config file",
                        rc,
                        "error",
                        True,
                    )

                    message_dialog.show_all()
                    message_dialog.run()
                    message_dialog.hide()

                    widget.set_active(True)
                    widget.set_state(True)

                    return True
            else:
                fn.logger.error("Failed to remove ArcoLinux mirrorlist")

                message_dialog = MessageDialog(
                    "Error",
                    "Failed to remove ArcoLinux mirrorlist",
                    "Errors occurred during removal of the ArcoLinux mirrorlist",
                    "Command run = %s\n\n Error = %s"
                    % (remove_mirrorlist["cmd_str"], remove_mirrorlist["output"]),
                    "error",
                    True,
                )

                message_dialog.show_all()
                message_dialog.run()
                message_dialog.hide()

                widget.set_active(True)
                widget.set_state(True)

                return True

        return True

    def version_toggle(self, widget, data):
        if widget.get_active() == True:
            fn.logger.debug("Showing package versions")

            self.display_versions = True
            GLib.idle_add(
                self.refresh_main_gui,
                priority=GLib.PRIORITY_DEFAULT,
            )
        else:
            fn.logger.debug("Hiding package versions")
            self.display_versions = False
            GLib.idle_add(
                self.refresh_main_gui,
                priority=GLib.PRIORITY_DEFAULT,
            )

    def refresh_main_gui(self):
        self.remove(self.vbox)
        GUI.setup_gui(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)
        self.show_all()

    def on_pacman_log_clicked(self, widget):
        try:
            self.toggle_popover()

            thread_addlog = "thread_addPacmanLogQueue"
            self.thread_add_pacmanlog_alive = fn.is_thread_alive(thread_addlog)

            if self.thread_add_pacmanlog_alive == False:
                fn.logger.info("Starting thread to monitor Pacman Log file")

                th_add_pacmanlog_queue = fn.threading.Thread(
                    name=thread_addlog,
                    target=fn.add_pacmanlog_queue,
                    args=(self,),
                    daemon=True,
                )
                th_add_pacmanlog_queue.start()

            if self.thread_add_pacmanlog_alive is True:
                # need to recreate the textview, can't use existing reference as it throws a seg fault

                self.textview_pacmanlog = Gtk.TextView()
                self.textview_pacmanlog.set_property("editable", False)
                self.textview_pacmanlog.set_property("monospace", True)
                self.textview_pacmanlog.set_border_width(10)
                self.textview_pacmanlog.set_vexpand(True)
                self.textview_pacmanlog.set_hexpand(True)

                # use the reference to the text buffer initialized before the logtimer thread started
                self.textview_pacmanlog.set_buffer(self.textbuffer_pacmanlog)

                window_pacmanlog = PacmanLogWindow(
                    self.textview_pacmanlog,
                    self.btn_pacmanlog,
                )
                window_pacmanlog.show_all()

                self.start_logtimer = window_pacmanlog.start_logtimer

            else:
                # keep a handle on the textbuffer, this is needed again later, if the pacman log file dialog is closed
                # since the textbuffer will already hold textdata at that point

                # textview is used inside another thread to update as the pacmanlog file is read into memory
                self.textbuffer_pacmanlog = Gtk.TextBuffer()

                self.textview_pacmanlog = Gtk.TextView()
                self.textview_pacmanlog.set_property("editable", False)
                self.textview_pacmanlog.set_property("monospace", True)
                self.textview_pacmanlog.set_border_width(10)
                self.textview_pacmanlog.set_vexpand(True)
                self.textview_pacmanlog.set_hexpand(True)

                self.textview_pacmanlog.set_buffer(self.textbuffer_pacmanlog)

                window_pacmanlog = PacmanLogWindow(
                    self.textview_pacmanlog,
                    self.btn_pacmanlog,
                )
                window_pacmanlog.show_all()

            thread_logtimer = "thread_startLogTimer"
            thread_logtimer_alive = False

            thread_logtimer_alive = fn.is_thread_alive(thread_logtimer)

            # a flag to indicate that the textview will need updating, used inside fn.start_log_timer
            self.start_logtimer = True

            if thread_logtimer_alive == False:
                th_logtimer = fn.threading.Thread(
                    name=thread_logtimer,
                    target=fn.start_log_timer,
                    args=(self, window_pacmanlog),
                    daemon=True,
                )
                th_logtimer.start()

            self.thread_add_pacmanlog_alive = True
            self.btn_pacmanlog.set_sensitive(False)

        except Exception as e:
            fn.logger.error("Exception in on_pacman_log_clicked() : %s" % e)

    def package_progress_toggle(self, widget, data):
        if widget.get_active() is True:
            self.show_progress_dialog = True
        if widget.get_active() is False:
            self.show_progress_dialog = False


# ====================================================================
#                       MAIN
# ====================================================================


def signal_handler(sig, frame):
    fn.logger.info("Sofirem is closing.")
    if os.path.exists("/tmp/sofirem.lock"):
        os.unlink("/tmp/sofirem.lock")

    if os.path.exists("/tmp/sofirem.pid"):
        os.unlink("/tmp/sofirem.pid")
    Gtk.main_quit(0)


# These should be kept as it ensures that multiple installation instances can't be run concurrently.
if __name__ == "__main__":
    try:
        signal.signal(signal.SIGINT, signal_handler)

        if not os.path.isfile("/tmp/sofirem.lock"):
            with open("/tmp/sofirem.pid", "w") as f:
                f.write(str(os.getpid()))

            style_provider = Gtk.CssProvider()
            style_provider.load_from_path(base_dir + "/sofirem.css")

            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            w = Main()
            w.show_all()

            fn.logger.info("App Started")

            Gtk.main()
        else:
            fn.logger.info("Sofirem lock file found")

            md = Gtk.MessageDialog(
                parent=Main(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Sofirem Lock File Found",
            )
            md.format_secondary_markup(
                "A Sofirem lock file has been found. This indicates there is already an instance of <b>Sofirem</b> running.\n\
                Click 'Yes' to remove the lock file and try running again"
            )  # noqa

            result = md.run()
            md.destroy()

            if result in (Gtk.ResponseType.OK, Gtk.ResponseType.YES):
                pid = ""
                if os.path.exists(fn.sofirem_pidfile):
                    with open("/tmp/sofirem.pid", "r") as f:
                        line = f.read()
                        pid = line.rstrip().lstrip()

                    if fn.check_if_process_running(int(pid)):
                        # needs to be fixed - todo

                        # md2 = Gtk.MessageDialog(
                        #     parent=Main,
                        #     flags=0,
                        #     message_type=Gtk.MessageType.INFO,
                        #     buttons=Gtk.ButtonsType.OK,
                        #     title="Application Running!",
                        #     text="You first need to close the existing application",
                        # )
                        # md2.format_secondary_markup(
                        #     "You first need to close the existing application"
                        # )
                        # md2.run()
                        fn.logger.info(
                            "You first need to close the existing application"
                        )
                    else:
                        os.unlink("/tmp/sofirem.lock")
                        sys.exit(1)
                else:
                    # in the rare event that the lock file is present, but the pid isn't
                    os.unlink("/tmp/sofirem.lock")
                    sys.exit(1)
            else:
                sys.exit(1)
    except Exception as e:
        fn.logger.error("Exception in __main__: %s" % e)
