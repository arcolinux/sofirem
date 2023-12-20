# ============================================================
# Authors: Brad Heffernan - Erik Dubois - Cameron Percival
# ============================================================

import os
import gi
import Functions as fn
from queue import Queue
from ui.MessageDialog import MessageDialog

from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

gi.require_version("Gtk", "3.0")
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class PackagesImportDialog(Gtk.Dialog):
    """create a gui"""

    def __init__(self, package_file, packages_list, logfile):
        Gtk.Dialog.__init__(self)

        # Create a queue for storing package import messages from pacman
        self.pkg_import_queue = Queue()

        # Create a queue for storing package install errors
        self.pkg_err_queue = Queue()

        # Create a queue for storing package install status
        self.pkg_status_queue = Queue()

        self.package_file = package_file
        self.packages_list = packages_list
        self.logfile = logfile

        self.stop_thread = False

        self.set_resizable(True)
        self.set_border_width(10)
        self.set_size_request(800, 700)
        self.set_modal(True)

        headerbar = Gtk.HeaderBar()
        headerbar.set_title("Import packages")
        headerbar.set_show_close_button(True)

        self.set_titlebar(headerbar)

        self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))

        hbox_title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_packages_title = Gtk.Label(xalign=0)
        lbl_packages_title.set_name("title")
        lbl_packages_title.set_text("Packages")

        hbox_title.pack_start(lbl_packages_title, False, False, 0)

        hbox_title_install = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        label_install_title = Gtk.Label(xalign=0)
        label_install_title.set_markup("<b> Install Packages</b>")

        hbox_title_install.pack_start(label_install_title, False, False, 0)

        hbox_sep = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hsep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        hbox_sep.pack_start(hsep, True, True, 0)

        frame_install = Gtk.Frame(label="")
        frame_install_label = frame_install.get_label_widget()
        frame_install_label.set_markup("<b>Install Packages</b>")

        hbox_install = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        label_install_desc = Gtk.Label(xalign=0, yalign=0)
        label_install_desc.set_markup(
            f""
            f" <b>WARNING: Proceed with caution this will install packages onto your system!</b>\n"
            f" <b>Packages from the AUR are not supported </b>\n"
            f" <b>This also performs a full system upgrade</b>\n\n"
            f" - A list of packages are sourced from <b>{self.package_file}</b>\n"
            f" - To ignore a package, add a # in front of the package name\n"
            f" - Log file: {self.logfile}\n"
            f" - <b>A reboot is recommended when core Linux packages are installed</b>\n"
        )

        self.scrolled_window = Gtk.ScrolledWindow()

        self.textview = Gtk.TextView()
        self.textview.set_name("textview_log")
        self.textview.set_property("editable", False)
        self.textview.set_property("monospace", True)
        self.textview.set_border_width(10)
        self.textview.set_vexpand(True)
        self.textview.set_hexpand(True)

        msg_buffer = self.textview.get_buffer()
        msg_buffer.insert(
            msg_buffer.get_end_iter(),
            "\n Click Yes to confirm install of the following packages:\n\n",
        )

        lbl_title_message = Gtk.Label(xalign=0, yalign=0)
        lbl_title_message.set_markup(
            "There are <b>%s</b> packages to install, proceed ?"
            % len(self.packages_list)
        )
        lbl_padding1 = Gtk.Label(xalign=0, yalign=0)
        lbl_padding1.set_text("")

        lbl_padding2 = Gtk.Label(xalign=0, yalign=0)
        lbl_padding2.set_text("")

        self.infobar = Gtk.InfoBar()

        content = self.infobar.get_content_area()
        content.add(lbl_title_message)

        self.infobar.set_revealed(True)

        for package in sorted(self.packages_list):
            msg_buffer.insert(msg_buffer.get_end_iter(), " - %s\n" % package)

        # move focus away from the textview, to hide the cursor at load
        headerbar.set_property("can-focus", True)
        Gtk.Window.grab_focus(headerbar)

        self.scrolled_window.add(self.textview)

        self.button_yes = self.add_button("Yes", Gtk.ResponseType.OK)
        self.button_yes.set_size_request(100, 30)
        btn_yes_context = self.button_yes.get_style_context()
        btn_yes_context.add_class("destructive-action")

        self.button_no = self.add_button("Close", Gtk.ResponseType.CANCEL)
        self.button_no.set_size_request(100, 30)

        self.connect("response", self.on_response)

        vbox_log_dir = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        btn_open_log_dir = Gtk.Button(label="Open log directory")
        btn_open_log_dir.connect("clicked", self.on_open_log_dir_clicked)
        btn_open_log_dir.set_size_request(100, 30)

        vbox_log_dir.pack_start(btn_open_log_dir, False, False, 0)

        grid_message = Gtk.Grid()

        grid_message.attach(label_install_desc, 0, 0, 1, 1)
        grid_message.attach(self.infobar, 0, 1, 1, 1)
        grid_message.attach(lbl_padding1, 0, 2, 1, 1)

        grid_message.attach(self.scrolled_window, 0, 3, 1, 1)
        grid_message.attach(lbl_padding2, 0, 4, 1, 1)
        grid_message.attach(vbox_log_dir, 0, 5, 1, 1)

        self.vbox.add(grid_message)

    def on_open_log_dir_clicked(self, widget):
        fn.open_log_dir()

    def display_progress(self):
        self.textview.destroy()
        self.infobar.destroy()
        self.button_yes.destroy()

        self.label_package_status = Gtk.Label(xalign=0, yalign=0)
        self.label_package_count = Gtk.Label(xalign=0, yalign=0)

        label_warning_close = Gtk.Label(xalign=0, yalign=0)
        label_warning_close.set_markup(
            "<b>Do not close this window during package installation</b>"
        )

        self.textview = Gtk.TextView()
        self.textview.set_name("textview_log")
        self.textview.set_property("editable", False)
        self.textview.set_property("monospace", True)
        self.textview.set_border_width(10)
        self.textview.set_vexpand(True)
        self.textview.set_hexpand(True)

        self.scrolled_window.add(self.textview)

        self.msg_buffer = self.textview.get_buffer()

        self.vbox.add(label_warning_close)
        self.vbox.add(self.label_package_status)
        self.vbox.add(self.label_package_count)

        fn.Thread(
            target=fn.monitor_package_import,
            args=(self,),
            daemon=True,
        ).start()

        self.show_all()

        fn.logger.info("Installing packages")
        event = "%s [INFO]: Installing packages\n" % fn.datetime.now().strftime(
            "%Y-%m-%d-%H-%M-%S"
        )

        fn.logger.info("Log file = %s" % self.logfile)

        self.pkg_import_queue.put(event)

        # debug install, overrride packages_list
        # self.packages_list = ["cheese", "firefox", "sofirem-dev-git", "sofirem-git"]

        # starts 2 threads one to install the packages, and another to check install status

        fn.Thread(
            target=fn.import_packages,
            args=(self,),
            daemon=True,
        ).start()

        fn.Thread(target=fn.log_package_status, args=(self,), daemon=True).start()

    def on_response(self, dialog, response):
        if response in (Gtk.ResponseType.OK, Gtk.ResponseType.YES):
            self.stop_thread = False
            self.display_progress()

        else:
            self.stop_thread = True
            dialog.hide()
            dialog.destroy()
