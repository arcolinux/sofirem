# This class is used to create a window showing a list of packages available for a given ArcoLinux ISO

import os
import gi
import requests
import Functions as fn
from ui.MessageDialog import MessageDialog

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


arcolinux_isos = [
    "arcolinuxs-xanmod-iso",
    "arcolinuxs-zen-iso",
    "arcolinuxs-lts-iso",
    "arcolinuxs-iso",
    "arcolinuxl-iso",
    "arcolinuxd-iso",
]

arcolinuxb_isos = [
    "arco-sway",
    "arco-plasma",
    "arco-hyprland",
    "arco-chadwm",
    "arco-dusk",
    "arco-dwm",
    "arco-berry",
    "arco-hypr",
    "arco-enlightenment",
    "arco-xtended",
    "arco-pantheon",
    "arco-awesome",
    "arco-bspwm",
    "arco-cinnamon",
    "arco-budgie",
    "arco-cutefish",
    "arco-cwm",
    "arco-deepin",
    "arco-gnome",
    "arco-fvwm3",
    "arco-herbstluftwm",
    "arco-i3",
    "arco-icewm",
    "arco-jwm",
    "arco-leftwm",
    "arco-lxqt",
    "arco-mate",
    "arco-openbox",
    "arco-qtile",
    "arco-spectrwm",
    "arco-ukui",
    "arco-wmderland",
    "arco-xfce",
    "arco-xmonad",
]

github_arcolinux_packagelist = "https://raw.githubusercontent.com/${ARCOLINUX}/${ISO}/master/archiso/packages.x86_64"
headers = {"Content-Type": "text/plain;charset=UTF-8"}


class ISOPackagesWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)

        headerbar = Gtk.HeaderBar()
        headerbar.set_title("ArcoLinux ISO Package Explorer")
        headerbar.set_show_close_button(True)

        # remove the focus on startup from search entry
        headerbar.set_property("can-focus", True)
        Gtk.Window.grab_focus(headerbar)

        self.set_resizable(True)
        self.set_size_request(500, 600)
        self.set_border_width(10)
        self.set_titlebar(headerbar)
        self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))
        self.treeview_loaded = False
        self.build_gui()

    def get_packagelist(self):
        try:
            # make request to get the package list from github
            url = None

            self.package_list = []

            if "-iso" in self.selected_iso:
                url = github_arcolinux_packagelist.replace(
                    "${ARCOLINUX}", "arcolinux"
                ).replace("${ISO}", self.selected_iso)
                github_arcolinux = [
                    "https://github.com/arcolinux/",
                    self.selected_iso,
                    "/blob/master/archiso/packages.x86_64",
                ]

                self.github_source = "".join(github_arcolinux)
            else:
                url = github_arcolinux_packagelist.replace(
                    "${ARCOLINUX}", "arcolinuxb"
                ).replace("${ISO}", self.selected_iso)

                github_arcolinuxb = [
                    "https://github.com/arcolinuxb/",
                    self.selected_iso,
                    "/blob/master/archiso/packages.x86_64",
                ]

                self.github_source = "".join(github_arcolinuxb)

            r = requests.get(url, headers=headers, allow_redirects=True)

            # read the package list ignore any commented lines
            if r.status_code == 200:
                if len(r.text) > 0:
                    for line in r.text.splitlines():
                        if "#" not in line.strip() and len(line.strip()) > 0:
                            self.package_list.append((line.strip(), None))
            else:
                fn.logger.error("Request for %s returned %s" % (url, r.status_code))

                message_dialog = MessageDialog(
                    "Error",
                    "Request failed",
                    "Failed to request package list",
                    "Request for %s returned status code = %s" % (url, r.status_code),
                    "error",
                    True,
                )

                message_dialog.show_all()
                message_dialog.run()
                message_dialog.hide()
                message_dialog.destroy()

        except Exception as e:
            message_dialog = MessageDialog(
                "Error",
                "Request failed",
                "Failed to request package list",
                e,
                "error",
                True,
            )

            message_dialog.show_all()
            message_dialog.run()
            message_dialog.hide()
            message_dialog.destroy()

    def on_combo_iso_changed(self, combo):
        try:
            iso = combo.get_active_text()
            if iso is not None:
                self.selected_iso = iso
                self.get_packagelist()

                if len(self.package_list) > 0:
                    lbl_github_source_title = Gtk.Label(xalign=0, yalign=0)
                    lbl_github_source_title.set_markup("<b>Package list source</b>")

                    lbl_github_source_value = Gtk.Label(xalign=0, yalign=0)
                    lbl_github_source_value.set_markup(
                        "<a href='%s'>%s</a>" % (self.github_source, self.github_source)
                    )

                    lbl_package_count_title = Gtk.Label(xalign=0, yalign=0)
                    lbl_package_count_title.set_markup("<b>Activated packages</b>")

                    lbl_package_count_value = Gtk.Label(xalign=0, yalign=0)
                    lbl_package_count_value.set_text(str(len(self.package_list)))

                    self.filename = "%s/sofirem-exports/%s-%s-packages.x86_64.txt" % (
                        fn.home,
                        self.selected_iso,
                        fn.datetime.now().strftime("%Y-%m-%d"),
                    )

                    lbl_export_desc_title = Gtk.Label(xalign=0, yalign=0)
                    lbl_export_desc_title.set_markup("<b>Export destination</b>")

                    lbl_export_desc_value = Gtk.Label(xalign=0, yalign=0)
                    lbl_export_desc_value.set_text(self.filename)

                    if self.treeview_loaded is True:
                        self.vbox_package_data.destroy()

                    search_entry = Gtk.SearchEntry()
                    search_entry.set_placeholder_text("Search...")
                    search_entry.set_size_request(450, 0)

                    grid_package_data = Gtk.Grid()

                    treestore_packages_explorer = Gtk.TreeStore(str, str)

                    for item in sorted(self.package_list):
                        treestore_packages_explorer.append(None, list(item))

                    treeview_packages_explorer = Gtk.TreeView()
                    treeview_packages_explorer.set_search_entry(search_entry)

                    treeview_packages_explorer.set_model(treestore_packages_explorer)

                    renderer = Gtk.CellRendererText()
                    column = Gtk.TreeViewColumn("Packages", renderer, text=0)

                    treeview_packages_explorer.append_column(column)

                    path = Gtk.TreePath.new_from_indices([0])

                    selection = treeview_packages_explorer.get_selection()

                    selection.select_path(path)

                    treeview_packages_explorer.expand_all()
                    treeview_packages_explorer.columns_autosize()

                    scrolled_window = Gtk.ScrolledWindow()
                    scrolled_window.set_vexpand(True)
                    scrolled_window.set_hexpand(True)

                    scrolled_window.add(treeview_packages_explorer)

                    grid_treeview = Gtk.Grid()
                    grid_treeview.set_column_homogeneous(True)

                    self.vbox_package_data = Gtk.Box(
                        orientation=Gtk.Orientation.VERTICAL, spacing=0
                    )

                    self.vbox_package_data.pack_start(
                        lbl_github_source_title, False, True, 1
                    )

                    self.vbox_package_data.pack_start(
                        lbl_github_source_value, False, True, 1
                    )

                    self.vbox_package_data.pack_start(
                        lbl_package_count_title, False, True, 1
                    )

                    self.vbox_package_data.pack_start(
                        lbl_package_count_value, False, True, 1
                    )

                    self.vbox_package_data.pack_start(
                        lbl_export_desc_title, False, True, 1
                    )
                    self.vbox_package_data.pack_start(
                        lbl_export_desc_value, False, True, 1
                    )

                    lbl_padding_search_entry1 = Gtk.Label(xalign=0, yalign=0)
                    lbl_padding_search_entry1.set_text("")

                    lbl_padding_search_entry2 = Gtk.Label(xalign=0, yalign=0)
                    lbl_padding_search_entry2.set_text("")

                    grid_search_entry = Gtk.Grid()

                    grid_search_entry.attach(lbl_padding_search_entry1, 0, 1, 1, 1)
                    grid_search_entry.attach(search_entry, 0, 2, 1, 1)
                    grid_search_entry.attach(lbl_padding_search_entry2, 0, 3, 1, 1)

                    self.vbox_package_data.pack_start(
                        grid_search_entry, False, False, 1
                    )

                    self.vbox_package_data.pack_start(scrolled_window, False, True, 1)

                    self.vbox_combo.pack_start(self.vbox_package_data, False, True, 1)

                    self.show_all()

                    self.treeview_loaded = True

        except Exception as e:
            fn.logger.error("Exception in on_combo_iso_changed(): %s" % e)

    def on_iso_package_list_export(self, widget):
        # export the package list to a file inside $HOME/sofirem-exports
        fn.logger.debug("Exporting ArcoLinux ISO package list")
        try:
            if self.filename is not None:
                with open(self.filename, "w", encoding="utf-8") as f:
                    f.write(
                        "# Created by Sofirem on %s\n"
                        % fn.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    f.write("# %s\n" % self.github_source)
                    for line in sorted(self.package_list):
                        f.write("%s\n" % line[0])

                if os.path.exists(self.filename):
                    message_dialog = MessageDialog(
                        "Info",
                        "Package export complete",
                        "Package list exported to %s" % self.filename,
                        "",
                        "info",
                        False,
                    )

                    message_dialog.show_all()
                    message_dialog.run()
                    message_dialog.hide()
                else:
                    message_dialog = MessageDialog(
                        "Error",
                        "Package export failed",
                        "Package list export failed",
                        "",
                        "error",
                        False,
                    )

                    message_dialog.show_all()
                    message_dialog.run()
                    message_dialog.hide()
                # file is created by root, update the permissions to the sudo username
                fn.permissions(self.filename)
            else:
                message_dialog = MessageDialog(
                    "Warning",
                    "Select an ISO",
                    "An ArcoLinux ISO needs to be selected before exporting",
                    "",
                    "warning",
                    False,
                )

                message_dialog.show_all()
                message_dialog.run()
                message_dialog.hide()
        except Exception as e:
            fn.logger.error("Exception in on_iso_package_list_export(): %s" % e)

    def on_close(self, widget):
        self.hide()
        self.destroy()

    def populate_combo_iso(self):
        for arco_iso in arcolinux_isos:
            self.combo_iso.append_text(arco_iso)

        for arco_isob in sorted(arcolinuxb_isos):
            self.combo_iso.append_text(arco_isob)

    def build_gui(self):
        try:
            lbl_select_iso = Gtk.Label(xalign=0, yalign=0)
            lbl_select_iso.set_markup("<b>Select ArcoLinux ISO</b>")

            lbl_padding1 = Gtk.Label(xalign=0, yalign=0)
            lbl_padding1.set_text("")

            lbl_padding2 = Gtk.Label(xalign=0, yalign=0)
            lbl_padding2.set_text("")

            self.combo_iso = Gtk.ComboBoxText()
            self.combo_iso.set_wrap_width(3)
            self.combo_iso.set_entry_text_column(0)
            self.combo_iso.connect("changed", self.on_combo_iso_changed)

            self.populate_combo_iso()

            self.filename = None

            grid_top = Gtk.Grid()

            grid_top.attach(lbl_select_iso, 0, 1, 1, 1)
            grid_top.attach_next_to(
                lbl_padding1, lbl_select_iso, Gtk.PositionType.BOTTOM, 1, 1
            )
            grid_top.attach(self.combo_iso, 0, 2, 1, 1)
            grid_top.attach(lbl_padding2, 0, 3, 1, 1)

            btn_ok = Gtk.Button(label="OK")
            btn_ok.set_size_request(100, 30)
            btn_ok.connect("clicked", self.on_close)
            btn_ok.set_halign(Gtk.Align.END)

            btn_export = Gtk.Button(label="Export")
            btn_export.set_size_request(100, 30)
            btn_export.connect("clicked", self.on_iso_package_list_export)
            btn_export.set_halign(Gtk.Align.END)

            grid_bottom = Gtk.Grid()
            grid_bottom.attach(btn_ok, 0, 1, 1, 1)

            lbl_padding3 = Gtk.Label(xalign=0, yalign=0)
            lbl_padding3.set_text("     ")

            grid_bottom.attach_next_to(
                lbl_padding3, btn_ok, Gtk.PositionType.RIGHT, 1, 1
            )

            grid_bottom.attach_next_to(
                btn_export, lbl_padding3, Gtk.PositionType.RIGHT, 1, 1
            )

            grid_bottom.set_halign(Gtk.Align.END)

            vbox_bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)

            lbl_padding_bottom = Gtk.Label(xalign=0, yalign=0)
            lbl_padding_bottom.set_text("")

            vbox_bottom.pack_start(lbl_padding_bottom, False, True, 0)
            vbox_bottom.pack_start(grid_bottom, False, True, 0)

            self.vbox_combo = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

            self.vbox_combo.pack_start(grid_top, False, True, 0)
            self.vbox_combo.pack_end(vbox_bottom, False, True, 0)

            self.add(self.vbox_combo)

            self.show_all()

        except Exception as e:
            fn.logger.error("Exception in build_gui(): %s" % e)
