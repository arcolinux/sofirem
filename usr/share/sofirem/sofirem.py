#!/usr/bin/env python3
import Splash
import gi
import os
import Functions as fn
from ProgressBarWindow import ProgressBarWindow
import signal
import datetime
import GUI
import subprocess
from Functions import os
from queue import Queue
import App_Frame_GUI

# from Functions import install_alacritty, os, pacman
from subprocess import PIPE, STDOUT
from time import sleep
from datetime import datetime
from collections import deque
import sys

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib  # noqa


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
now = datetime.now()
global launchtime
launchtime = now.strftime("%Y-%m-%d-%H-%M-%S")


class Main(Gtk.Window):
    # Create a queue, for worker communication (Multithreading - used in GUI layer)
    queue = Queue()

    # Create a queue to handle package install/removal
    pkg_queue = Queue()

    # A deque to manage the number of packages to install we can have stacked up
    pkg_inst_deque = deque(maxlen=5)

    # Create a queue for storing search results
    search_queue = Queue()

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
            self.timeout_id = None

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
            print("[INFO] : pkgver = pkgversion")
            print("[INFO] : pkgrel = pkgrelease")
            print(
                "---------------------------------------------------------------------------"
            )
            print("[INFO] : Distro = " + fn.distr)
            print(
                "---------------------------------------------------------------------------"
            )

            # Create installed.lst file for first time
            now = datetime.now().strftime("%H:%M:%S")
            fn.get_current_installed()
            print("[INFO] %s Created installed.lst" % now)
            fn.create_actions_log(
                launchtime,
                "[INFO] %s Created installed.lst" % now + "\n",
            )

            # Creating directories
            if not os.path.isdir(fn.log_dir):
                try:
                    os.mkdir(fn.log_dir)
                except Exception as e:
                    print(e)

            if not os.path.isdir(fn.sof_log_dir):
                try:
                    os.mkdir(fn.sof_log_dir)
                except Exception as e:
                    print(e)

            if not os.path.isdir(fn.act_log_dir):
                try:
                    os.mkdir(fn.act_log_dir)
                except Exception as e:
                    print(e)

            # start making sure sofirem starts next time with dark or light theme
            if os.path.isdir(fn.home + "/.config/gtk-3.0"):
                try:
                    if not os.path.islink("/root/.config/gtk-3.0"):
                        fn.shutil.rmtree("/root/.config/gtk-3.0")
                        fn.shutil.copytree(
                            fn.home + "/.config/gtk-3.0", "/root/.config/gtk-3.0"
                        )
                except Exception as error:
                    print(error)

            if os.path.isdir("/root/.config/xsettingsd/xsettingsd.conf"):
                try:
                    if not os.path.islink("/root/.config/xsettingsd/"):
                        fn.shutil.rmtree("/root/.config/xsettingsd/")
                        if fn.path.isdir(fn.home + "/.config/xsettingsd/"):
                            fn.shutil.copytree(
                                fn.home + "/.config/xsettingsd/",
                                "/root/.config/xsettingsd/",
                            )
                except Exception as error:
                    print(error)

            # run pacman -Sy to sync pacman db, else you get a lot of 404 errors

            if fn.sync(self) == 0:
                now = datetime.now().strftime("%H:%M:%S")
                print("[INFO] %s Synchronising complete" % now)
                fn.create_actions_log(
                    launchtime,
                    "[INFO] %s Synchronising complete" % now + "\n",
                )
            else:
                # Should the app continue to load here, given the fact that the pacman sync failed
                now = datetime.now().strftime("%H:%M:%S")
                print(
                    "[ERROR] %s Synchronising failed" % now,
                )
                fn.create_actions_log(
                    launchtime,
                    "[ERROR] %s Synchronising failed" % now + "\n",
                )
                print(
                    "---------------------------------------------------------------------------"
                )

                msg_dialog = fn.message_dialog(
                    self,
                    "pacman -Sy",
                    "Pacman database synchronisation failed",
                    "Please verify the pacman logs for more details",
                    Gtk.MessageType.ERROR,
                )

                msg_dialog.run()
                msg_dialog.hide()

            # store package information into memory, and use the dictionary returned to search in for quicker retrieval
            print("[INFO] %s Storing package metadata started" % now)

            self.packages = fn.storePackages()

            print(
                "[INFO] %s Categories = %s"
                % (
                    now,
                    len(self.packages.keys()),
                )
            )

            total_packages = 0

            for category in self.packages:
                total_packages += len(self.packages[category])

            print(
                "[INFO] %s Total packages = %s"
                % (
                    now,
                    total_packages,
                )
            )

            print("[INFO] %s Storing package metadata completed" % now)

            splScr = Splash.splashScreen()

            while Gtk.events_pending():
                Gtk.main_iteration()

            sleep(2)
            splScr.destroy()

            print("[INFO] %s Preparing GUI" % fn.datetime.now().strftime("%H:%M:%S"))

            fn.create_actions_log(
                launchtime,
                "[INFO] %s Preparing GUI" % fn.datetime.now().strftime("%H:%M:%S")
                + "\n",
            )

            # On initial app load search_activated is set to False

            self.search_activated = False

            # Save reference to the vbox generated from the main GUI view
            self.vbox_main = GUI.GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)

            print("[INFO] %s Completed GUI" % fn.datetime.now().strftime("%H:%M:%S"))

            fn.create_actions_log(
                launchtime,
                "[INFO] %s Completed GUI" % fn.datetime.now().strftime("%H:%M:%S")
                + "\n",
            )

            if not os.path.isfile("/tmp/sofirem.lock"):
                with open("/tmp/sofirem.lock", "w") as f:
                    f.write("")

        except Exception as e:
            print("Exception in Main() : %s" % e)

    # =====================================================
    #               WINDOW KEY EVENT CTRL + F
    # =====================================================

    # sets focus on the search entry
    def on_keypress_event(self, widget, event):
        shortcut = Gtk.accelerator_get_label(event.keyval, event.state)

        if shortcut in ("Ctrl+F", "Ctrl+Mod2+F"):
            # set focus on text entry, select all text if any
            self.searchEntry.grab_focus()

        if shortcut in ("Ctrl+I", "Ctrl+Mod2+I"):
            fn.show_package_info(self)

    # =====================================================
    #               SEARCH ENTRY
    # =====================================================

    def on_search_activated(self, searchentry):
        if searchentry.get_text_length() == 0 and self.search_activated:
            self.vbox_main = GUI.GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)
            self.search_activated = False

        if searchentry.get_text_length() == 0:
            self.search_activated = False

        search_term = searchentry.get_text()
        # if the string is completely whitespace ignore searching
        if not search_term.isspace():
            try:
                if len(search_term) > 0:
                    # test if the string entered by the user is in the package name
                    # results is a dictionary, which holds a list of packages
                    # results[category]=pkg_list

                    # searching is processed inside a thread

                    th_search = fn.threading.Thread(
                        name="thread_search",
                        target=fn.search,
                        args=(
                            self,
                            search_term,
                        ),
                    )
                    print(
                        "[INFO] %s Starting search"
                        % fn.datetime.now().strftime("%H:%M:%S")
                    )

                    th_search.start()

                    # get the search_results from the queue
                    results = self.search_queue.get()

                    if results is not None:
                        print(
                            "[INFO] %s Search complete"
                            % fn.datetime.now().strftime("%H:%M:%S")
                        )

                        if len(results) > 0:
                            total = 0
                            for val in results.values():
                                total += len(val)

                            print(
                                "[INFO] %s Search found %s results"
                                % (
                                    fn.datetime.now().strftime("%H:%M:%S"),
                                    total,
                                )
                            )
                            # make sure the gui search only displays the pkgs inside the results

                            self.vbox_search = GUI.GUISearch(
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
                        print(
                            "[INFO] %s Search found %s results"
                            % (
                                fn.datetime.now().strftime("%H:%M:%S"),
                                0,
                            )
                        )
                        self.searchEntry.grab_focus()

                elif self.search_activated == True:
                    self.vbox_main = GUI.GUI(
                        self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango
                    )
                    self.search_activated = False
            except Exception as err:
                print("Exception in on_search_activated(): %s" % err)

            finally:
                if self.search_activated == True:
                    self.search_queue.task_done()

    def on_search_cleared(self, searchentry, icon_pos, event):
        if self.search_activated:
            self.vbox_main = GUI.GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)

        self.searchEntry.set_placeholder_text("Search...")

        self.search_activated = False

    # =====================================================
    #               ARCOLINUX REPOS, KEYS AND MIRRORS
    # =====================================================

    def on_repos_clicked(self, widget):
        if self.btnRepos._value == 1:
            print("[INFO] : Let's install the ArcoLinux keys and mirrors")
            fn.install_arcolinux_key_mirror(self)

            print("[INFO] : Checking whether the repos have been added")
            fn.add_repos()

            self.btnRepos.set_label("Remove repos")
            self.btnRepos._value = 2

        else:
            print("[INFO] : Let's remove the ArcoLinux keys and mirrors")
            fn.remove_arcolinux_key_mirror(self)
            print("[INFO] : Removing the ArcoLinux repos in /etc/pacman.conf")
            fn.remove_repos()

            self.btnRepos.set_label("Add repos")
            self.btnRepos._value = 1

    # =====================================================
    #               RESTART/QUIT BUTTON
    # =====================================================

    def on_close(self, widget, data):
        if os.path.exists("/tmp/sofirem.lock"):
            os.unlink("/tmp/sofirem.lock")

        if os.path.exists("/tmp/sofirem.pid"):
            os.unlink("/tmp/sofirem.pid")

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
    def app_toggle(self, widget, active, package, Gtk, vboxStack1, fn, category):
        # switch widget is currently toggled off
        if widget.get_state() == False and widget.get_active() == True:
            widget.set_state(True)
            package = package.strip()

            if len(package) > 0:
                print(
                    "[INFO] %s Package to install : %s"
                    % (datetime.now().strftime("%H:%M:%S"), package)
                )

                if len(self.pkg_inst_deque) <= 5:
                    self.pkg_inst_deque.append(package)
                    self.pkg_queue.put(
                        (
                            package,
                            "install",
                            widget,
                        ),
                    )

                    th = fn.threading.Thread(
                        name="thread_pkginst",
                        target=fn.install,
                        args=(self,),
                    )

                    th.start()
                else:
                    msg_dialog = message_dialog(
                        self,
                        "Please wait until previous Pacman transactions are completed",
                        "There are a maximum of 5 packages added to the queue",
                        "Waiting for previous Pacman transactions to complete",
                        Gtk.MessageType.WARNING,
                    )

                    msg_dialog.run()
                    msg_dialog.hide()

        # switch widget is currently toggled on
        if widget.get_state() == True and widget.get_active() == False:
            widget.set_state(False)
            # Uninstall the package
            package = package.strip()

            if len(package) > 0:
                print(
                    "[INFO] %s Package to remove : %s"
                    % (datetime.now().strftime("%H:%M:%S"), package)
                )

                self.pkg_queue.put(
                    (
                        package,
                        "uninstall",
                        widget,
                    ),
                )

                th = fn.threading.Thread(
                    name="thread_pkgrem",
                    target=fn.uninstall,
                    args=(self,),
                )

                th.start()

        fn.get_current_installed()

        # return True to prevent the default handler from running
        return True

        # App_Frame_GUI.GUI(self, Gtk, vboxStack1, fn, category, package_file)
        # widget.get_parent().get_parent().get_parent().get_parent().get_parent().get_parent().get_parent().queue_redraw()
        # self.gui.hide()
        # self.gui.queue_redraw()
        # self.gui.show_all()

    def pkgInfo_clicked(self, widget):
        fn.show_package_info(self)

    def recache_clicked(self, widget):
        # Check if cache is out of date. If so, run the re-cache, if not, don't.
        # pb = ProgressBarWindow()
        # pb.show_all()
        # pb.set_text("Updating Cache")
        # pb.reset_timer()

        print(
            "[INFO] %s Recache applications - start"
            % fn.datetime.now().strftime("%H:%M:%S")
        )

        fn.create_actions_log(
            launchtime,
            "[INFO] %s Recache applications - start"
            % fn.datetime.now().strftime("%H:%M:%S")
            + "\n",
        )

        fn.cache_btn()


# ====================================================================
#                       MAIN
# ====================================================================


def signal_handler(sig, frame):
    print("[INFO] %s Sofirem is closing." % fn.datetime.now().strftime("%H:%M:%S"))
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

            fn.create_packages_log()

            print("[INFO] %s App Started" % fn.datetime.now().strftime("%H:%M:%S"))
            fn.create_actions_log(
                launchtime,
                "[INFO] %s App Started" % fn.datetime.now().strftime("%H:%M:%S") + "\n",
            )
            Gtk.main()
        else:
            md = Gtk.MessageDialog(
                parent=Main(),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Lock File Found",
            )
            md.format_secondary_markup(
                "The lock file has been found. This indicates there is already an instance of <b>Sofirem</b> running.\n\
Click 'Yes' to remove the lock file and try running again"
            )  # noqa

            result = md.run()
            md.destroy()

            if result in (Gtk.ResponseType.OK, Gtk.ResponseType.YES):
                pid = ""
                with open("/tmp/sofirem.pid", "r") as f:
                    line = f.read()
                    pid = line.rstrip().lstrip()

                if fn.checkIfProcessRunning(int(pid)):
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
                    print("You first need to close the existing application")
                else:
                    os.unlink("/tmp/sofirem.lock")
    except Exception as e:
        print("Exception in __main__: %s" % e)
