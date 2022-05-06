#!/usr/bin/env python3
import Splash
import gi
import Functions
import signal
import GUI
import subprocess
from Functions import os
from queue import Queue
#from Functions import install_alacritty, os, pacman
from subprocess import PIPE, STDOUT
from time import sleep
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib  # noqa

#      #============================================================
#      #=          Authors:  Erik Dubois - Cameron Percival        =
#      #============================================================

base_dir = os.path.dirname(os.path.realpath(__file__))

class Main(Gtk.Window):
    #Create a queue, for worker communication (Multithreading - used in GUI layer)
    queue = Queue()
    def __init__(self):
        super(Main, self).__init__(title="ArcoLinux Application Installer")
        self.set_border_width(10)
        self.connect("delete-event", self.on_close)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_from_file(os.path.join(base_dir, 'images/arcolinux.png'))
        self.set_default_size(800, 700)

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

        if not os.path.isdir(Functions.aai_log_dir):
            try:
                os.mkdir(Functions.aai_log_dir)
            except Exception as e:
                print(e)


        if not Functions.os.path.isdir(Functions.home +
                                       "/.config/arcolinux-application-installer"):

            Functions.os.makedirs(Functions.home +
                                  "/.config/arcolinux-application-installer", 0o766)
            Functions.permissions(Functions.home +
                                  "/.config/arcolinux-application-installer")
        # Force Permissions
        a1 = Functions.os.stat(Functions.home + "/.config/autostart")
        a2 = Functions.os.stat(Functions.home + "/.config/arcolinux-application-installer")
        #a3 = Functions.os.stat(Functions.home + "/" + Functions.bd)
        autostart = a1.st_uid
        aai = a2.st_uid
        #backup = a3.st_uid

        if autostart == 0:
            Functions.permissions(Functions.home + "/.config/autostart")
            print("Fix autostart permissions...")
        if aai == 0:
            Functions.permissions(Functions.home + "/.config/arcolinux-application-installer")
            print("Fix arcolinux-application-installer permissions...")

        GUI.GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)

        if not os.path.isfile("/tmp/aai.lock"):
            with open("/tmp/aai.lock", "w") as f:
                f.write("")

    def on_close(self, widget, data):
        os.unlink("/tmp/aai.lock")
        Gtk.main_quit()

# ====================================================================
#                     Button Functions
# ====================================================================
# Given what this function does, it might be worth considering making it a
# thread so that the app doesn't block while installing/uninstalling is happening.
    def app_toggle(self, widget, active, package):
        if widget.get_active():
            #Install the package
            Functions.install(package)
        else:
            #Uninstall the package
            Functions.uninstall(package)


# ====================================================================
#                       MAIN
# ====================================================================


def signal_handler(sig, frame):
    print('\nAAI is Closing.')
    os.unlink("/tmp/aai.lock")
    Gtk.main_quit(0)

#These should be kept as it ensures that multiple installation instances can't be run concurrently.
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    if not os.path.isfile("/tmp/aai.lock"):
        with open("/tmp/aai.pid", "w") as f:
            f.write(str(os.getpid()))
            f.close()
        style_provider = Gtk.CssProvider()
        style_provider.load_from_path(base_dir + "/aai.css")

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        w = Main()
        w.show_all()
        Gtk.main()
    else:
        md = Gtk.MessageDialog(parent=Main(),
                               flags=0,
                               message_type=Gtk.MessageType.INFO,
                               buttons=Gtk.ButtonsType.YES_NO,
                               text="Lock File Found")
        md.format_secondary_markup(
            "The lock file has been found. This indicates there is already an instance of <b>ArcoLinux Application Installer</b> running.\n\
click yes to remove the lock file and try running again")  # noqa

        result = md.run()
        md.destroy()

        if result in (Gtk.ResponseType.OK, Gtk.ResponseType.YES):
            pid = ""
            with open("/tmp/aai.pid", "r") as f:
                line = f.read()
                pid = line.rstrip().lstrip()
                f.close()

            if Functions.checkIfProcessRunning(int(pid)):
                Functions.MessageBox("Application Running!",
                                     "You first need to close the existing application")  # noqa
            else:
                os.unlink("/tmp/aai.lock")
