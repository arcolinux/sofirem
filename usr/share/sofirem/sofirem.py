#!/usr/bin/env python3
import Splash
import gi
import Functions
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


class Main(Gtk.Window):
    # Create a queue, for worker communication (Multithreading - used in GUI layer)
    queue = Queue()

    # Created a second queue to handle package install/removal
    pkg_queue = Queue()

    def __init__(self):
        super(Main, self).__init__(title="Sofirem")
        self.set_border_width(10)
        self.connect("delete-event", self.on_close)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))
        self.set_default_size(800, 900)

        print(
            "---------------------------------------------------------------------------"
        )
        print("If you have errors, report it on the discord channel of ArcoLinux")
        print(
            "---------------------------------------------------------------------------"
        )
        print("You can receive support on https://discord.gg/R2amEEz")
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
        # run pacman -Sy to sync pacman db, else you get a lot of 404 errors

        if Functions.sync() == 0:
            print(
                "[INFO] %s Synchronising complete"
                % Functions.datetime.now().strftime("%H:%M:%S")
            )
            print(
                "---------------------------------------------------------------------------"
            )
        else:
            print(
                "[ERROR] %s Synchronising failed"
                % Functions.datetime.now().strftime("%H:%M:%S")
            )
            print(
                "---------------------------------------------------------------------------"
            )

        splScr = Splash.splashScreen()

        while Gtk.events_pending():
            Gtk.main_iteration()

        sleep(2)
        splScr.destroy()

        if not os.path.isdir(Functions.log_dir):
            try:
                os.mkdir(Functions.log_dir)
            except Exception as e:
                print(e)

        if not os.path.isdir(Functions.sof_log_dir):
            try:
                os.mkdir(Functions.sof_log_dir)
            except Exception as e:
                print(e)

        if not Functions.os.path.isdir(Functions.home + "/.config/sofirem"):

            Functions.os.makedirs(Functions.home + "/.config/sofirem", 0o766)
            Functions.permissions(Functions.home + "/.config/sofirem")
        # Force Permissions
        a1 = Functions.os.stat(Functions.home + "/.config/autostart")
        a2 = Functions.os.stat(Functions.home + "/.config/sofirem")
        # a3 = Functions.os.stat(Functions.home + "/" + Functions.bd)
        autostart = a1.st_uid
        sof = a2.st_uid
        # backup = a3.st_uid

        if autostart == 0:
            Functions.permissions(Functions.home + "/.config/autostart")
            print("Fix autostart permissions...")
        if sof == 0:
            Functions.permissions(Functions.home + "/.config/sofirem")
            print("Fix sofirem permissions...")

        print("[INFO] %s Preparing GUI" % Functions.datetime.now().strftime("%H:%M:%S"))

        gui = GUI.GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)

        print("[INFO] %s Completed GUI" % Functions.datetime.now().strftime("%H:%M:%S"))

        if not os.path.isfile("/tmp/sofirem.lock"):
            with open("/tmp/sofirem.lock", "w") as f:
                f.write("")

    # =====================================================
    #               RESTART/QUIT BUTTON
    # =====================================================

    def on_close(self, widget):
        os.unlink("/tmp/sofirem.lock")
        os.unlink("/tmp/sofirem.pid")

        Gtk.main_quit()
        print(
            "---------------------------------------------------------------------------"
        )
        print("Thanks for using Sofirem")
        print("Report issues to make it even better")
        print(
            "---------------------------------------------------------------------------"
        )
        print("You can report issues on https://discord.gg/R2amEEz")
        print(
            "---------------------------------------------------------------------------"
        )

    # ====================================================================
    #                     Button Functions
    # ====================================================================
    # Given what this function does, it might be worth considering making it a
    # thread so that the app doesn't block while installing/uninstalling is happening.
    def app_toggle(
        self, widget, active, package, Gtk, vboxStack1, Functions, category, packages
    ):
        path = base_dir + "/cache/installed.lst"

        if widget.get_active():
            # Install the package
            package = package.strip()

            if len(package) > 0:
                print(":: Package to install : %s" % package)

                self.pkg_queue.put(package)

                th = Functions.threading.Thread(
                    name="thread_pkginst",
                    target=Functions.install,
                    args=(self.pkg_queue,),
                )

                th.daemon = True
                th.start()

                self.pkg_queue.put(None)

            # Functions.install(package)
        else:
            # Uninstall the package
            package = package.strip()

            if len(package) > 0:
                print(":: Package to remove : %s" % package)

                self.pkg_queue.put(package)

                th = Functions.threading.Thread(
                    name="thread_pkgrem",
                    target=Functions.uninstall,
                    args=(self.pkg_queue,),
                )

                th.daemon = True
                th.start()

                self.pkg_queue.put(None)

                # Functions.uninstall(package)
        Functions.get_current_installed(path)
        # App_Frame_GUI.GUI(self, Gtk, vboxStack1, Functions, category, package_file)
        # widget.get_parent().get_parent().get_parent().get_parent().get_parent().get_parent().get_parent().queue_redraw()
        # self.gui.hide()
        # self.gui.queue_redraw()
        # self.gui.show_all()

    def recache_clicked(self, widget):
        # Check if cache is out of date. If so, run the re-cache, if not, don't.
        pb = ProgressBarWindow()
        pb.show_all()
        # pb.set_text("Updating Cache")
        # pb.reset_timer()
        Functions.cache_btn("cache/", pb)


# ====================================================================
#                       MAIN
# ====================================================================


def signal_handler(sig, frame):
    print("\nSofirem is closing.")
    os.unlink("/tmp/sofirem.lock")
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

            Functions.create_packages_log()

            print(
                "[INFO] %s App Started" % Functions.datetime.now().strftime("%H:%M:%S")
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

                if Functions.checkIfProcessRunning(int(pid)):
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
