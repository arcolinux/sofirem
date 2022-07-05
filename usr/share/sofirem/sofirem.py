#!/usr/bin/env python3
import Splash
import gi
import Functions
from ProgressBarWindow import ProgressBarWindow
import signal
import GUI
import subprocess
from Functions import os
from queue import Queue
import App_Frame_GUI
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
        super(Main, self).__init__(title="Sofirem")
        self.set_border_width(10)
        self.connect("delete-event", self.on_close)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_from_file(os.path.join(base_dir, 'images/sofirem.png'))
        self.set_default_size(800, 900)

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
        
        gui = GUI.GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango)
        
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
    def app_toggle(self, widget, active, package, Gtk, vboxStack1, Functions, category, packages):
        path = "cache/installed.lst"
        if widget.get_active():
            #Install the package
            Functions.install(package)            
        else:
            #Uninstall the package
            Functions.uninstall(package)
        Functions.get_current_installed(path)
        #App_Frame_GUI.GUI(self, Gtk, vboxStack1, Functions, category, package_file)
        #widget.get_parent().get_parent().get_parent().get_parent().get_parent().get_parent().get_parent().queue_redraw()
        #self.gui.hide()
        #self.gui.queue_redraw()
        #self.gui.show_all()
        
        
        
        

    def recache_clicked(self, widget):
        #Check if cache is out of date. If so, run the re-cache, if not, don't.
        pb = ProgressBarWindow()
        pb.show_all()
        #pb.set_text("Updating Cache")
        #pb.reset_timer()
        Functions.cache_btn("cache/", pb)



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
