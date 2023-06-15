# This class stores static information about the app, and is displayed in the about dialog
import os
import gi

from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

gi.require_version("Gtk", "3.0")

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# base_dir = os.path.dirname(os.path.realpath(__file__))


class AboutDialog(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self)

        app_name = "Sofirem"
        app_title = "About Sofirem"
        app_main_description = "%s - %s" % (app_name, "Software Installer Remover")
        app_secondary_message = "Install or remove software from your ArcoLinux system"
        app_secondary_description = "Report issues to make it even better"
        app_version = "pkgversion-pkgrelease"
        app_discord = "https://discord.gg/stBhS4taje"
        app_website = "https://arcolinux.info"
        app_github = "https://github.com/arcolinux/sofirem-dev"
        app_authors = []
        app_authors.append(("Cameron Percival", None))
        app_authors.append(("Fennec", None))
        app_authors.append(("Erik Dubois", None))

        pixbuf = GdkPixbuf.Pixbuf().new_from_file_at_size(
            os.path.join(base_dir, "images/sofirem.png"), 100, 100
        )
        app_image = Gtk.Image().new_from_pixbuf(pixbuf)

        self.set_resizable(False)
        self.set_size_request(560, 350)
        self.set_icon_from_file(os.path.join(base_dir, "images/sofirem.png"))
        self.set_border_width(10)

        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(True)
        headerbar.set_title(app_title)
        self.set_titlebar(headerbar)

        btn_about_close = Gtk.Button(label="OK")
        btn_about_close.connect("clicked", self.on_response, "response")

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        stack.set_transition_duration(350)
        stack.set_hhomogeneous(False)
        stack.set_vhomogeneous(False)

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_orientation(Gtk.Orientation.HORIZONTAL)
        stack_switcher.set_stack(stack)
        stack_switcher.set_homogeneous(True)

        lbl_main_description = Gtk.Label(xalign=0, yalign=0)
        lbl_main_description.set_markup(
            "<b>                                %s</b>" % app_main_description
        )

        lbl_secondary_message = Gtk.Label(xalign=0, yalign=0)
        lbl_secondary_message.set_text(
            "                                %s" % app_secondary_message
        )

        lbl_secondary_description = Gtk.Label(xalign=0, yalign=0)
        lbl_secondary_description.set_text(
            "                                %s" % app_secondary_description
        )

        lbl_version = Gtk.Label(xalign=0, yalign=0)
        lbl_version.set_markup(
            "                                <b>Version:</b> %s" % app_version
        )

        ivbox_about = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        ivbox_about.pack_start(app_image, True, True, 0)
        ivbox_about.pack_start(lbl_main_description, True, True, 0)
        ivbox_about.pack_start(lbl_version, True, True, 0)
        ivbox_about.pack_start(lbl_secondary_message, True, True, 0)
        ivbox_about.pack_start(lbl_secondary_description, True, True, 0)

        stack.add_titled(ivbox_about, "About Sofirem", "About")

        grid_support = Gtk.Grid()

        lbl_padding1 = Gtk.Label(xalign=0, yalign=0)
        lbl_padding1.set_text(" ")

        grid_support.attach(lbl_padding1, 0, 1, 1, 1)

        lbl_support_title = Gtk.Label(xalign=0, yalign=0)
        lbl_support_title.set_markup("<b>Discord    </b>")

        lbl_support_value = Gtk.Label(xalign=0, yalign=0)
        lbl_support_value.set_markup("<a href='%s'>%s</a>" % (app_discord, app_discord))

        lbl_website_title = Gtk.Label(xalign=0, yalign=0)
        lbl_website_title.set_markup("<b>ArcoLinux website  </b>")

        lbl_website_value = Gtk.Label(xalign=0, yalign=0)
        lbl_website_value.set_markup("<a href='%s'>%s</a>" % (app_website, app_website))

        lbl_github_title = Gtk.Label(xalign=0, yalign=0)
        lbl_github_title.set_markup("<b>GitHub  </b>")

        lbl_github_value = Gtk.Label(xalign=0, yalign=0)
        lbl_github_value.set_markup("<a href='%s'>%s</a>" % (app_github, app_github))

        grid_support.attach(lbl_support_title, 0, 2, 1, 1)

        grid_support.attach_next_to(
            lbl_support_value, lbl_support_title, Gtk.PositionType.RIGHT, 20, 1
        )

        grid_support.attach(lbl_website_title, 0, 3, 1, 1)
        grid_support.attach_next_to(
            lbl_website_value, lbl_website_title, Gtk.PositionType.RIGHT, 20, 1
        )

        grid_support.attach(lbl_github_title, 0, 4, 1, 1)
        grid_support.attach_next_to(
            lbl_github_value, lbl_github_title, Gtk.PositionType.RIGHT, 20, 1
        )

        stack.add_titled(grid_support, "Support", "Support")

        box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box_outer.set_border_width(10)

        lbl_padding2 = Gtk.Label(xalign=0, yalign=0)
        lbl_padding2.set_text(" ")

        lbl_padding3 = Gtk.Label(xalign=0, yalign=0)
        lbl_padding3.set_text(" ")

        lbl_authors_title = Gtk.Label(xalign=0, yalign=0)
        lbl_authors_title.set_text(
            "The following people have contributed to the development of %s" % app_name
        )

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        box_outer.pack_start(lbl_authors_title, True, True, 0)
        box_outer.pack_start(listbox, True, True, 0)

        treestore_authors = Gtk.TreeStore(str, str)
        for item in app_authors:
            treestore_authors.append(None, list(item))

        treeview_authors = Gtk.TreeView(model=treestore_authors)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(None, renderer, text=0)

        treeview_authors.append_column(column)

        path = Gtk.TreePath.new_from_indices([0])

        selection = treeview_authors.get_selection()

        selection.select_path(path)

        treeview_authors.expand_all()
        treeview_authors.columns_autosize()

        row_authors = Gtk.ListBoxRow()
        vbox_authors = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        row_authors.add(vbox_authors)

        vbox_authors.pack_start(treeview_authors, True, True, 0)

        listbox.add(row_authors)

        stack.add_titled(box_outer, "Authors", "Authors")

        self.connect("response", self.on_response)

        self.vbox.add(stack_switcher)
        self.vbox.add(stack)

        self.show_all()

    def on_response(self, dialog, response):
        self.hide()
        self.destroy()
