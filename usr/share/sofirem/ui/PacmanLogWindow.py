# This class is used to create a window to monitor the pacman log file inside /var/log/pacman.log

import os
import gi
import Functions as fn
from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

gi.require_version("Gtk", "3.0")

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# base_dir = os.path.dirname(os.path.realpath(__file__))


class PacmanLogWindow(Gtk.Window):
    def __init__(self, textview_pacmanlog, btn_pacmanlog):
        Gtk.Window.__init__(self)

        self.start_logtimer = True
        self.textview_pacmanlog = textview_pacmanlog
        self.btn_pacmanlog = btn_pacmanlog
        headerbar = Gtk.HeaderBar()

        headerbar.set_show_close_button(True)

        self.set_titlebar(headerbar)

        self.set_title("Sofirem - Pacman log file viewer")
        self.set_default_size(800, 600)
        self.set_resizable(True)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))
        self.connect("delete-event", self.on_close)

        btn_pacmanlog_ok = Gtk.Button(label="OK")
        btn_pacmanlog_ok.connect("clicked", self.on_response, "response")
        btn_pacmanlog_ok.set_size_request(100, 30)
        btn_pacmanlog_ok.set_halign(Gtk.Align.END)

        pacmanlog_scrolledwindow = Gtk.ScrolledWindow()
        pacmanlog_scrolledwindow.set_size_request(750, 500)
        pacmanlog_scrolledwindow.add(self.textview_pacmanlog)

        lbl_padding1 = Gtk.Label(xalign=0, yalign=0)
        lbl_padding1.set_text("")

        vbox_pacmanlog = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        vbox_pacmanlog.pack_start(pacmanlog_scrolledwindow, True, True, 0)
        vbox_pacmanlog.pack_start(lbl_padding1, False, False, 0)
        vbox_pacmanlog.pack_start(btn_pacmanlog_ok, False, False, 0)

        self.add(vbox_pacmanlog)

    def on_close(self, widget, data):
        fn.logger.debug("Closing pacman log monitoring window")
        self.start_logtimer = False
        self.btn_pacmanlog.set_sensitive(True)

        self.hide()
        self.destroy()

    def on_response(self, widget, response):
        # stop updating the textview
        fn.logger.debug("Closing pacman log monitoring dialog")
        self.start_logtimer = False
        self.btn_pacmanlog.set_sensitive(True)

        # self.remove(self)
        self.hide()
        self.destroy()
