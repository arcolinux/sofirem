# This class is used to create a modal dialog window to display currently installed packages

import os
import gi
import Functions as fn
from ui.MessageDialog import MessageDialog

from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

gi.require_version("Gtk", "3.0")

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# base_dir = os.path.dirname(os.path.realpath(__file__))
filename = "%s/%s-installed-packages.x86_64.txt" % (
    fn.export_dir,
    fn.datetime.now().strftime("%Y-%m-%d"),
)


class PackageListDialog(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self)

        self.set_resizable(True)
        self.set_size_request(800, 700)
        self.set_modal(True)

        self.set_border_width(10)
        self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))

        self.connect("delete-event", self.on_close)

        headerbar = Gtk.HeaderBar()
        headerbar.set_title("Showing installed packages")
        headerbar.set_show_close_button(True)

        self.set_titlebar(headerbar)

        grid_packageslst = Gtk.Grid()
        grid_packageslst.set_column_homogeneous(True)

        lbl_info = Gtk.Label(xalign=0, yalign=0)
        lbl_info.set_text("Export destination %s" % filename)

        # get a list of installed packages on the system

        installed_packages_list = fn.get_installed_package_data()

        if len(installed_packages_list) > 0:
            self.set_title(
                "Showing %s installed packages" % len(installed_packages_list)
            )

            search_entry = Gtk.SearchEntry()
            search_entry.set_placeholder_text("Search...")

            # remove the focus on startup from search entry
            headerbar.set_property("can-focus", True)
            Gtk.Window.grab_focus(headerbar)

            treestore_packages = Gtk.TreeStore(str, str, str, str, str)
            for item in sorted(installed_packages_list):
                treestore_packages.append(None, list(item))

            treeview_packages = Gtk.TreeView()
            treeview_packages.set_search_entry(search_entry)

            treeview_packages.set_model(treestore_packages)

            for i, col_title in enumerate(
                [
                    "Name",
                    "Installed Version",
                    "Latest Version",
                    "Installed Size",
                    "Installed Date",
                ]
            ):
                renderer = Gtk.CellRendererText()
                col = Gtk.TreeViewColumn(col_title, renderer, text=i)
                treeview_packages.append_column(col)

            # allow sorting by installed date

            col_installed_date = treeview_packages.get_column(4)
            col_installed_date.set_sort_column_id(4)

            treestore_packages.set_sort_func(4, self.compare_install_date, None)

            path = Gtk.TreePath.new_from_indices([0])

            selection = treeview_packages.get_selection()
            selection.select_path(path)

            treeview_packages.expand_all()
            treeview_packages.columns_autosize()

            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_vexpand(True)
            scrolled_window.set_hexpand(True)

            grid_packageslst.attach(scrolled_window, 0, 0, 8, 10)

            lbl_padding1 = Gtk.Label(xalign=0, yalign=0)
            lbl_padding1.set_text("")

            grid_packageslst.attach_next_to(
                lbl_padding1, scrolled_window, Gtk.PositionType.BOTTOM, 1, 1
            )

            btn_dialog_export = Gtk.Button(label="Export")
            btn_dialog_export.connect(
                "clicked", self.on_dialog_export_clicked, installed_packages_list
            )
            btn_dialog_export.set_size_request(100, 30)
            btn_dialog_export.set_halign(Gtk.Align.END)

            btn_dialog_export_close = Gtk.Button(label="Close")
            btn_dialog_export_close.connect("clicked", self.on_close, "delete-event")
            btn_dialog_export_close.set_size_request(100, 30)
            btn_dialog_export_close.set_halign(Gtk.Align.END)

            scrolled_window.add(treeview_packages)

            grid_btn = Gtk.Grid()
            grid_btn.attach(btn_dialog_export, 0, 1, 1, 1)

            lbl_padding2 = Gtk.Label(xalign=0, yalign=0)
            lbl_padding2.set_text(" ")

            grid_btn.attach_next_to(
                lbl_padding2, btn_dialog_export, Gtk.PositionType.RIGHT, 1, 1
            )

            grid_btn.attach_next_to(
                btn_dialog_export_close, lbl_padding2, Gtk.PositionType.RIGHT, 1, 1
            )

            grid_btn.set_halign(Gtk.Align.END)

            vbox_btn = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            vbox_btn.pack_start(grid_btn, True, True, 1)

            lbl_padding3 = Gtk.Label(xalign=0, yalign=0)
            lbl_padding3.set_text("")

            self.vbox.add(search_entry)
            self.vbox.add(lbl_padding3)
            self.vbox.add(grid_packageslst)
            self.vbox.add(lbl_info)
            self.vbox.add(vbox_btn)

    def on_close(self, dialog, event):
        self.hide()
        self.destroy()

    def on_dialog_export_clicked(self, dialog, installed_packages_list_export):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(
                    "# Created by Sofirem on %s\n"
                    % fn.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                for package in sorted(installed_packages_list_export):
                    f.write("%s\n" % (package[0]))

            if os.path.exists(filename):
                fn.logger.info("Export completed")

                # fix permissions, file is owned by root
                fn.permissions(filename)

                message_dialog = MessageDialog(
                    "Info",
                    "Package export complete",
                    "Package list exported to %s" % filename,
                    "",
                    "info",
                    False,
                )

                message_dialog.show_all()
                message_dialog.run()
                message_dialog.hide()
                message_dialog.destroy()

            else:
                fn.logger.error("Export failed")

                message_dialog = MessageDialog(
                    "Error",
                    "Package export failed",
                    "Failed to export package list to %s." % filename,
                    "",
                    "error",
                    False,
                )

                message_dialog.show_all()
                message_dialog.run()
                message_dialog.hide()
                message_dialog.destroy()

        except Exception as e:
            fn.logger.error("Exception in on_dialog_export_clicked(): %s" % e)

    # noqa: any locales other than en_GB.UTF-8 / en_US.UTF-8 are untested
    def compare_install_date(self, model, row1, row2, user_data):
        try:
            sort_column, _ = model.get_sort_column_id()
            str_value1 = model.get_value(row1, sort_column)
            str_value2 = model.get_value(row2, sort_column)

            datetime_value1 = None
            datetime_value2 = None

            # convert string into datetime object, check if time format is 12H format with AM/PM
            if str_value1.lower().find("am") > 0 or str_value1.lower().find("pm") > 0:
                # 12H format
                datetime_value1 = fn.datetime.strptime(
                    str_value1, "%a %d %b %Y %I:%M:%S %p %Z"
                ).replace(tzinfo=None)
                datetime_value2 = fn.datetime.strptime(
                    str_value2, "%a %d %b %Y %I:%M:%S %p %Z"
                ).replace(tzinfo=None)
            else:
                # 24H format
                datetime_value1 = fn.datetime.strptime(
                    str_value1, "%a %d %b %Y %H:%M:%S %Z"
                ).replace(tzinfo=None)
                datetime_value2 = fn.datetime.strptime(
                    str_value2, "%a %d %b %Y %H:%M:%S %Z"
                ).replace(tzinfo=None)

            if datetime_value1 is not None and datetime_value2 is not None:
                if datetime_value1 < datetime_value2:
                    return -1
                elif datetime_value1 == datetime_value2:
                    return 0
                else:
                    return 1
        except ValueError as ve:
            # fn.logger.error("ValueError in compare_install_date: %s" % ve)
            # compare fails due to the format of the datetime string, which hasn't been tested
            pass
        except Exception as e:
            fn.logger.error("Exception in compare_install_date: %s" % e)
