# This class is used to create a window for package name searches and to display package information

import os
import gi

import Functions as fn
from ui.MessageDialog import MessageDialog

from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

gi.require_version("Gtk", "3.0")

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class PackageSearchWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)

        self.headerbar = Gtk.HeaderBar()
        self.headerbar.set_title("Package Search")
        self.headerbar.set_show_close_button(True)

        # remove the focus on startup from search entry
        self.headerbar.set_property("can-focus", True)
        Gtk.Window.grab_focus(self.headerbar)

        self.set_resizable(True)
        self.set_size_request(700, 500)
        self.set_border_width(10)
        self.set_titlebar(self.headerbar)
        self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))
        self.search_package_activated = False
        self.build_gui()

    def build_gui(self):
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(350)
        self.stack.set_hhomogeneous(False)
        self.stack.set_vhomogeneous(False)

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_orientation(Gtk.Orientation.HORIZONTAL)
        stack_switcher.set_stack(self.stack)
        stack_switcher.set_homogeneous(True)

        searchentry = Gtk.SearchEntry()
        searchentry.set_placeholder_text("Search using package name...")
        searchentry.set_size_request(400, 0)
        searchentry.connect("activate", self.on_search_package_activated)
        searchentry.connect("icon-release", self.on_search_package_cleared)

        btn_ok = Gtk.Button(label="OK")
        btn_ok.set_size_request(100, 30)
        btn_ok.connect("clicked", self.on_close)
        btn_ok.set_halign(Gtk.Align.END)

        grid_bottom = Gtk.Grid()
        grid_bottom.attach(btn_ok, 0, 1, 1, 1)
        grid_bottom.set_halign(Gtk.Align.END)

        vbox_bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        lbl_padding_bottom = Gtk.Label(xalign=0, yalign=0)
        lbl_padding_bottom.set_text("")

        vbox_bottom.pack_start(lbl_padding_bottom, False, True, 0)
        vbox_bottom.pack_start(grid_bottom, False, True, 0)

        self.stack.add_titled(searchentry, "Package Search", "Package Search")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_border_width(10)

        vbox.pack_start(stack_switcher, False, False, 0)
        vbox.pack_start(self.stack, False, False, 0)
        vbox.pack_end(vbox_bottom, False, True, 0)

        self.add(vbox)
        self.show_all()

        thread_pacman_sync_file_db = fn.threading.Thread(
            name="thread_pacman_sync_file_db",
            target=fn.sync_file_db,
            daemon=True,
        )
        thread_pacman_sync_file_db.start()

    def on_close(self, widget):
        self.hide()
        self.destroy()

    def on_search_package_activated(self, searchentry):
        if searchentry.get_text_length() == 0 and self.search_package_activated:
            self.search_package_activated = False
            self.stack.get_child_by_name("Package Information").destroy()

            self.stack.get_child_by_name("Package Files").destroy()
            Gtk.Window.grab_focus(self.headerbar)
        else:
            self.perform_search(searchentry)

    def on_search_package_cleared(self, searchentry, icon_pos, event):
        searchentry.set_placeholder_text("Search using package name...")
        if self.search_package_activated is True:
            self.search_package_activated = False
            self.stack.get_child_by_name("Package Information").destroy()

            self.stack.get_child_by_name("Package Files").destroy()

        Gtk.Window.grab_focus(self.headerbar)

    def perform_search(self, searchentry):
        try:
            if (
                len(searchentry.get_text().rstrip().lstrip()) > 0
                and not searchentry.get_text().isspace()
            ):
                term = searchentry.get_text().rstrip().lstrip()

                if len(term) > 0:
                    fn.logger.info("Searching pacman file database")

                    package_metadata = fn.get_package_information(term)

                    if package_metadata is not None:
                        # package information

                        if self.search_package_activated is True:
                            self.stack.get_child_by_name(
                                "Package Information"
                            ).destroy()

                            self.stack.get_child_by_name("Package Files").destroy()

                        box_outer = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=5
                        )

                        listbox = Gtk.ListBox()
                        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
                        box_outer.pack_start(listbox, True, True, 0)

                        # package name
                        row_package_title = Gtk.ListBoxRow()
                        vbox_package_title = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )
                        row_package_title.add(vbox_package_title)
                        lbl_package_name_title = Gtk.Label(xalign=0)
                        lbl_package_name_title.set_markup("<b>Package Name</b>")

                        lbl_package_name_value = Gtk.Label(xalign=0)
                        lbl_package_name_value.set_text(package_metadata["name"])
                        vbox_package_title.pack_start(
                            lbl_package_name_title, True, True, 0
                        )
                        vbox_package_title.pack_start(
                            lbl_package_name_value, True, True, 0
                        )

                        listbox.add(row_package_title)

                        # repository

                        row_package_repo = Gtk.ListBoxRow()
                        vbox_package_repo = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )
                        row_package_repo.add(vbox_package_repo)
                        lbl_package_repo_title = Gtk.Label(xalign=0)
                        lbl_package_repo_title.set_markup("<b>Repository</b>")

                        lbl_package_repo_value = Gtk.Label(xalign=0)
                        lbl_package_repo_value.set_text(package_metadata["repository"])
                        vbox_package_repo.pack_start(
                            lbl_package_repo_title, True, True, 0
                        )
                        vbox_package_repo.pack_start(
                            lbl_package_repo_value, True, True, 0
                        )

                        listbox.add(row_package_repo)

                        # description

                        row_package_description = Gtk.ListBoxRow()
                        vbox_package_description = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )
                        row_package_description.add(vbox_package_description)
                        lbl_package_description_title = Gtk.Label(xalign=0)
                        lbl_package_description_title.set_markup("<b>Description</b>")

                        lbl_package_description_value = Gtk.Label(xalign=0)
                        lbl_package_description_value.set_text(
                            package_metadata["description"]
                        )
                        vbox_package_description.pack_start(
                            lbl_package_description_title, True, True, 0
                        )
                        vbox_package_description.pack_start(
                            lbl_package_description_value, True, True, 0
                        )

                        listbox.add(row_package_description)

                        # arch

                        row_package_arch = Gtk.ListBoxRow()
                        vbox_package_arch = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )
                        row_package_arch.add(vbox_package_arch)
                        lbl_package_arch_title = Gtk.Label(xalign=0)
                        lbl_package_arch_title.set_markup("<b>Architecture</b>")

                        lbl_package_arch_value = Gtk.Label(xalign=0)
                        lbl_package_arch_value.set_text(package_metadata["arch"])
                        vbox_package_arch.pack_start(
                            lbl_package_arch_title, True, True, 0
                        )
                        vbox_package_arch.pack_start(
                            lbl_package_arch_value, True, True, 0
                        )

                        listbox.add(row_package_arch)

                        # url

                        row_package_url = Gtk.ListBoxRow()
                        vbox_package_url = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )
                        row_package_url.add(vbox_package_url)
                        lbl_package_url_title = Gtk.Label(xalign=0)
                        lbl_package_url_title.set_markup("<b>URL</b>")

                        lbl_package_url_value = Gtk.Label(xalign=0)
                        lbl_package_url_value.set_markup(
                            "<a href='%s'>%s</a>"
                            % (package_metadata["url"], package_metadata["url"])
                        )
                        vbox_package_url.pack_start(
                            lbl_package_url_title, True, True, 0
                        )
                        vbox_package_url.pack_start(
                            lbl_package_url_value, True, True, 0
                        )

                        listbox.add(row_package_url)

                        # download size

                        row_package_size = Gtk.ListBoxRow()
                        vbox_package_size = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )
                        row_package_size.add(vbox_package_size)
                        lbl_package_size_title = Gtk.Label(xalign=0)
                        lbl_package_size_title.set_markup("<b>Download size</b>")

                        lbl_package_size_value = Gtk.Label(xalign=0)
                        lbl_package_size_value.set_text(
                            package_metadata["download_size"]
                        )
                        vbox_package_size.pack_start(
                            lbl_package_size_title, True, True, 0
                        )
                        vbox_package_size.pack_start(
                            lbl_package_size_value, True, True, 0
                        )

                        listbox.add(row_package_size)

                        # installed size

                        row_package_installed_size = Gtk.ListBoxRow()
                        vbox_package_installed_size = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )
                        row_package_installed_size.add(vbox_package_installed_size)
                        lbl_package_installed_size_title = Gtk.Label(xalign=0)
                        lbl_package_installed_size_title.set_markup(
                            "<b>Installed size</b>"
                        )

                        lbl_package_installed_size_value = Gtk.Label(xalign=0)
                        lbl_package_installed_size_value.set_text(
                            package_metadata["installed_size"]
                        )
                        vbox_package_installed_size.pack_start(
                            lbl_package_installed_size_title, True, True, 0
                        )
                        vbox_package_installed_size.pack_start(
                            lbl_package_installed_size_value, True, True, 0
                        )

                        listbox.add(row_package_installed_size)

                        # build date

                        row_package_build_date = Gtk.ListBoxRow()
                        vbox_package_build_date = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )
                        row_package_build_date.add(vbox_package_build_date)
                        lbl_package_build_date_title = Gtk.Label(xalign=0)
                        lbl_package_build_date_title.set_markup("<b>Build date</b>")

                        lbl_package_build_date_value = Gtk.Label(xalign=0)
                        lbl_package_build_date_value.set_text(
                            package_metadata["build_date"]
                        )
                        vbox_package_build_date.pack_start(
                            lbl_package_build_date_title, True, True, 0
                        )
                        vbox_package_build_date.pack_start(
                            lbl_package_build_date_value, True, True, 0
                        )

                        listbox.add(row_package_build_date)

                        # packager

                        row_package_maintainer = Gtk.ListBoxRow()
                        vbox_package_maintainer = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )
                        row_package_maintainer.add(vbox_package_maintainer)
                        lbl_package_maintainer_title = Gtk.Label(xalign=0)
                        lbl_package_maintainer_title.set_markup("<b>Packager</b>")

                        lbl_package_maintainer_value = Gtk.Label(xalign=0)
                        lbl_package_maintainer_value.set_text(
                            package_metadata["packager"]
                        )
                        vbox_package_maintainer.pack_start(
                            lbl_package_maintainer_title, True, True, 0
                        )
                        vbox_package_maintainer.pack_start(
                            lbl_package_maintainer_value, True, True, 0
                        )

                        listbox.add(row_package_maintainer)

                        # depends on

                        expander_depends_on = Gtk.Expander()
                        expander_depends_on.set_expanded(True)
                        expander_depends_on.set_use_markup(True)
                        expander_depends_on.set_resize_toplevel(True)
                        expander_depends_on.set_label("<b>Depends on</b>")

                        row_package_depends_on = Gtk.ListBoxRow()
                        expander_depends_on.add(row_package_depends_on)
                        vbox_package_depends_on = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )
                        row_package_depends_on.add(vbox_package_depends_on)

                        if len(package_metadata["depends_on"]) > 0:
                            treestore_depends = Gtk.TreeStore(str, str)

                            for item in package_metadata["depends_on"]:
                                treestore_depends.append(None, list(item))

                            treeview_depends = Gtk.TreeView(model=treestore_depends)

                            renderer = Gtk.CellRendererText()
                            column = Gtk.TreeViewColumn("Package", renderer, text=0)

                            treeview_depends.append_column(column)

                            vbox_package_depends_on.pack_start(
                                treeview_depends, True, True, 0
                            )

                        else:
                            lbl_package_depends_value = Gtk.Label(xalign=0, yalign=0)
                            lbl_package_depends_value.set_text("None")

                            vbox_package_depends_on.pack_start(
                                lbl_package_depends_value, True, True, 0
                            )

                        listbox.add(expander_depends_on)

                        # conflicts with

                        expander_conflicts_with = Gtk.Expander()
                        expander_conflicts_with.set_use_markup(True)
                        expander_conflicts_with.set_expanded(True)
                        expander_conflicts_with.set_resize_toplevel(True)
                        expander_conflicts_with.set_label("<b>Conflicts with</b>")

                        row_package_conflicts_with = Gtk.ListBoxRow()
                        expander_conflicts_with.add(row_package_conflicts_with)
                        vbox_package_conflicts_with = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )
                        row_package_conflicts_with.add(vbox_package_conflicts_with)

                        if len(package_metadata["conflicts_with"]) > 0:
                            treestore_conflicts = Gtk.TreeStore(str, str)

                            for item in package_metadata["conflicts_with"]:
                                treestore_conflicts.append(None, list(item))

                            treeview_conflicts = Gtk.TreeView(model=treestore_conflicts)

                            renderer = Gtk.CellRendererText()
                            column = Gtk.TreeViewColumn("Package", renderer, text=0)

                            treeview_conflicts.append_column(column)

                            vbox_package_conflicts_with.pack_start(
                                treeview_conflicts, True, True, 0
                            )

                        else:
                            lbl_package_conflicts_with_value = Gtk.Label(
                                xalign=0, yalign=0
                            )
                            lbl_package_conflicts_with_value.set_text("None")

                            vbox_package_conflicts_with.pack_start(
                                lbl_package_conflicts_with_value, True, True, 0
                            )

                        listbox.add(expander_conflicts_with)

                        checkbtn_installed = Gtk.CheckButton(label="Installed")
                        checkbtn_installed.set_active(False)
                        checkbtn_installed.set_sensitive(False)

                        # is the package installed
                        installed = fn.check_package_installed(term)

                        if installed is True:
                            checkbtn_installed.set_active(True)

                        # box_outer.pack_start(checkbtn_installed, True, True, 0)

                        scrolled_window_package_info = Gtk.ScrolledWindow()
                        scrolled_window_package_info.set_propagate_natural_height(True)
                        scrolled_window_package_info.add(box_outer)

                        vbox_package_info = Gtk.Box(
                            orientation=Gtk.Orientation.VERTICAL, spacing=0
                        )

                        lbl_padding_vbox = Gtk.Label(xalign=0, yalign=0)
                        lbl_padding_vbox.set_text("")

                        vbox_package_info.pack_start(
                            scrolled_window_package_info, True, True, 0
                        )
                        vbox_package_info.pack_start(lbl_padding_vbox, True, True, 0)
                        vbox_package_info.pack_start(checkbtn_installed, True, True, 0)

                        self.stack.add_titled(
                            vbox_package_info,
                            "Package Information",
                            "Package Information",
                        )

                        # package files

                        package_files = fn.get_package_files(term)
                        if package_files is not None:
                            lbl_package_title = Gtk.Label(xalign=0, yalign=0)
                            lbl_package_title.set_markup("<b>Package</b>")

                            lbl_package_title_value = Gtk.Label(xalign=0, yalign=0)

                            lbl_package_title_value.set_text(package_metadata["name"])

                            treestore_filelist = Gtk.TreeStore(str, str)

                            for file in package_files:
                                treestore_filelist.append(None, list(file))

                            treeview_files = Gtk.TreeView(model=treestore_filelist)

                            renderer = Gtk.CellRendererText()
                            column = Gtk.TreeViewColumn("Files", renderer, text=0)

                            treeview_files.append_column(column)

                            vbox_package_files = Gtk.Box(
                                orientation=Gtk.Orientation.VERTICAL, spacing=0
                            )

                            vbox_package_files.pack_start(
                                lbl_package_title, True, True, 0
                            )
                            vbox_package_files.pack_start(
                                lbl_package_title_value, True, True, 0
                            )

                            lbl_padding_package_files = Gtk.Label(xalign=0, yalign=0)
                            lbl_padding_package_files.set_text("")

                            vbox_package_files.pack_start(
                                lbl_padding_package_files, True, True, 0
                            )

                            scrolled_window_package_files = Gtk.ScrolledWindow()
                            scrolled_window_package_files.set_propagate_natural_height(
                                True
                            )
                            scrolled_window_package_files.add(treeview_files)

                            vbox_package_files.pack_start(
                                scrolled_window_package_files, True, True, 0
                            )

                            self.stack.add_titled(
                                vbox_package_files,
                                "Package Files",
                                "Package Files",
                            )

                        self.search_package_activated = True
                        self.show_all()

                    else:
                        message_dialog = MessageDialog(
                            "Info",
                            "Search returned 0 results",
                            "Failed to find package name",
                            "Are the correct pacman mirrorlists configured ?\nOr try to search again using the exact package name",
                            "info",
                            False,
                        )

                        message_dialog.show_all()
                        message_dialog.run()
                        message_dialog.hide()

        except Exception as e:
            fn.logger.error("Exception in perform_search(): %s" % e)
