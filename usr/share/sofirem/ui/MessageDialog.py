# This class is used to create a modal dialog window showing detailed information about an event

import os
import gi
import Functions as fn

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# base_dir = os.path.dirname(os.path.realpath(__file__))


class MessageDialog(Gtk.Dialog):
    # message_type is a string, either one of "info", "warning", "error" to show which infobar to display
    # extended argument when set to true shows a textview inside the dialog
    # extended argument when set to false only shows a standard dialog
    def __init__(
        self, title, subtitle, first_msg, secondary_msg, message_type, extended
    ):
        Gtk.Dialog.__init__(self)

        headerbar = Gtk.HeaderBar()
        headerbar.set_title(title)
        headerbar.set_show_close_button(True)

        self.set_resizable(True)

        self.set_border_width(10)

        self.set_titlebar(headerbar)

        btn_ok = Gtk.Button(label="OK")
        btn_ok.set_size_request(100, 30)
        btn_ok.connect("clicked", on_message_dialog_ok_response, self)
        btn_ok.set_halign(Gtk.Align.END)
        self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))

        infobar = Gtk.InfoBar()

        if message_type == "info":
            infobar.set_name("infobar_info")
        if message_type == "error":
            infobar.set_name("infobar_error")
        if message_type == "warning":
            infobar.set_name("infobar_warning")

        lbl_title_message = Gtk.Label(xalign=0, yalign=0)
        lbl_title_message.set_markup("<b>%s</b>" % subtitle)
        content = infobar.get_content_area()
        content.add(lbl_title_message)

        infobar.set_revealed(True)

        lbl_padding1 = Gtk.Label(xalign=0, yalign=0)
        lbl_padding1.set_text("")

        lbl_padding2 = Gtk.Label(xalign=0, yalign=0)
        lbl_padding2.set_text("")

        grid_message = Gtk.Grid()

        grid_message.attach(infobar, 0, 0, 1, 1)
        grid_message.attach(lbl_padding1, 0, 1, 1, 1)

        if extended is True:
            scrolled_window = Gtk.ScrolledWindow()
            textview = Gtk.TextView()
            textview.set_property("editable", False)
            textview.set_property("monospace", True)
            textview.set_border_width(10)
            textview.set_vexpand(True)
            textview.set_hexpand(True)

            msg_buffer = textview.get_buffer()
            msg_buffer.insert(
                msg_buffer.get_end_iter(),
                "Event timestamp = %s\n"
                % fn.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            msg_buffer.insert(msg_buffer.get_end_iter(), "%s\n" % first_msg)
            msg_buffer.insert(msg_buffer.get_end_iter(), "%s\n" % secondary_msg)

            # move focus away from the textview, to hide the cursor at load
            headerbar.set_property("can-focus", True)
            Gtk.Window.grab_focus(headerbar)

            scrolled_window.add(textview)

            grid_message.attach(scrolled_window, 0, 2, 1, 1)
            grid_message.attach(lbl_padding2, 0, 3, 1, 1)

            self.set_default_size(800, 600)

        else:
            # do not display textview
            lbl_first_message = Gtk.Label(xalign=0, yalign=0)
            lbl_first_message.set_text(first_msg)

            lbl_second_message = Gtk.Label(xalign=0, yalign=0)
            lbl_second_message.set_markup("<b>%s</b>" % secondary_msg)

            grid_message.attach(lbl_first_message, 0, 2, 1, 1)
            grid_message.attach(lbl_second_message, 0, 3, 1, 1)

            self.set_default_size(600, 100)
            self.set_resizable(False)

        vbox_close = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox_close.pack_start(btn_ok, True, True, 1)

        self.vbox.add(grid_message)
        self.vbox.add(vbox_close)


def on_message_dialog_ok_response(self, widget):
    # widget.hide()
    widget.destroy()
