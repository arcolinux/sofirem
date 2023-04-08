# =================================================================
# =                 Author: Cameron Percival                      =
# =================================================================
from socket import TIPC_ADDR_NAME
from urllib.parse import scheme_chars
import Functions


def GUI(self, Gtk, vboxStack1, category, package_file):
    try:
        # Lets set some variables that we know we will need later
        # hboxes and items to make the page look sensible
        cat_name = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        seperator = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl1 = Gtk.Label(xalign=0)
        lbl1.set_text(category)
        lbl1.set_name("title")
        hseparator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        seperator.pack_start(hseparator, True, True, 0)
        cat_name.pack_start(lbl1, False, False, 0)

        # Stack for the different subcategories - I like crossfade as a transition, but you choose
        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        stack.set_transition_duration(350)
        stack.set_hhomogeneous(False)
        stack.set_vhomogeneous(False)

        # Stack needs a stack switcher to allow the user to make different choices
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_orientation(Gtk.Orientation.HORIZONTAL)
        stack_switcher.set_stack(stack)
        stack_switcher.set_homogeneous(True)

        # We will need a vbox later for storing the stack and stack switcher together at the end
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # create scroller for when/if these items go "off the page"
        scrolledSwitch = Gtk.ScrolledWindow()
        scrolledSwitch.add(stack_switcher)

        # These lists will ensure that we can keep track of the individual windows and their names
        # stack of vboxes
        vboxStacks = []
        # name of each vbox - derived from the sub category name
        vboxStackNames = []

        # page variables - reset these when making multiple subcategories:
        # List of packages for any given subcategory
        packages = []
        # labels:
        name = ""
        description = ""
        # Lets start by reading in the package list and saving it as a file
        with open(package_file, "r") as f:
            content = f.readlines()
            # f.close()

        # Add a line to the end of content to force the page to be packed.
        content.append(
            "pack now"
        )  # Really, this can be any string, as long as it doesn't match the if statement below.
        # Now lets read the file, and use some logic to drive what goes where
        # Optomised for runspeed: the line most commonly activated appears first.
        for line in content:
            # this line will handle code in the yaml that we simply don't need or care about
            # MAINTENANCE; if the structure of the .yaml file ever changes, this WILL likely need to be updated
            if line.startswith("  packages:"):
                continue
            elif line.startswith("    - "):
                # add the package to the packages list
                package = line.strip("    - ")
                packages.append(package)
                # TODO: Add list and function to obtain package description from pacman and store it (maybe? Maybe the yaml file has what we need?)
            elif line.startswith("  description: "):
                # Set the label text for the description line
                description = (
                    line.strip("  description: ").strip().strip('"').strip("\n")
                )
            else:
                # We will only hit here for category changes, or to pack the page, or if the yaml is changed.
                # Yaml changes are handled in the first if statement.
                # Pack page;

                if len(packages) > 0:
                    # Pack the page
                    # Packing list:
                    # vbox to pack into - pop it off the list
                    page = vboxStacks.pop()
                    # grid it
                    grid = Gtk.Grid()
                    # Subcat
                    lblName = Gtk.Label(xalign=0)
                    lblName.set_markup("<b>" + name + "</b>")
                    page.pack_start(lblName, False, False, 0)
                    # description
                    lblDesc = Gtk.Label(xalign=0)
                    lblDesc.set_markup("Description: <i>" + description + "</i>")
                    page.pack_start(lblDesc, False, False, 0)
                    # packages
                    sep_text = "     "
                    for i in range(len(packages)):
                        grid.insert_row(i)
                        # hbox_pkg = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
                        lblSep1 = Gtk.Label(xalign=0, yalign=0)
                        lblSep1.set_text(sep_text)
                        grid.attach(lblSep1, 0, i, 1, 1)
                        lblPkg = Gtk.Label(xalign=0, yalign=0)  # was in for loop
                        lblPkg.set_text(packages[i])  # was in for loop
                        # hbox_pkg.pack_start(lblPkg, False, False, 100)
                        grid.attach_next_to(
                            lblPkg, lblSep1, Gtk.PositionType.RIGHT, 1, 1
                        )
                        lblSep2 = Gtk.Label(xalign=0, yalign=0)
                        lblSep2.set_text(sep_text)
                        grid.attach_next_to(
                            lblSep2, lblPkg, Gtk.PositionType.RIGHT, 1, 1
                        )
                        lbl_pkg_desc = Gtk.Label(xalign=0, yalign=0)
                        lbl_pkg_desc.set_text(
                            Functions.obtain_pkg_description(packages[i])
                        )
                        # hbox_pkg.pack_start(lbl_pkg_desc, False, False, 0)
                        grid.attach_next_to(
                            lbl_pkg_desc, lblSep2, Gtk.PositionType.RIGHT, 1, 1
                        )
                        # grid.attach(lbl_pkg_desc, 1, i, 1, 1)
                        lblSep3 = Gtk.Label(xalign=0, yalign=0)
                        lblSep3.set_text(sep_text)
                        grid.attach_next_to(
                            lblSep3, lbl_pkg_desc, Gtk.PositionType.RIGHT, 1, 1
                        )
                        switch = Gtk.Switch()
                        switch.set_active(Functions.query_pkg(packages[i]))
                        switch.connect(
                            "notify::active",
                            self.app_toggle,
                            packages[i],
                            Gtk,
                            vboxStack1,
                            Functions,
                            category,
                            packages,
                        )
                        # hbox_pkg.pack_end(switch, False, False, 500)
                        grid.attach_next_to(
                            switch, lblSep3, Gtk.PositionType.RIGHT, 1, 1
                        )
                        # grid.attach(switch, 2, i, 1, 1)

                    # make the page scrollable
                    grid_sc = Gtk.ScrolledWindow()
                    grid_sc.add(grid)

                    grid_sc.set_propagate_natural_height(True)
                    # pack the grid to the page.
                    page.pack_start(grid_sc, False, False, 0)
                    # save the page - put it back (now populated)
                    vboxStacks.append(page)
                    # reset the things that we need to.
                    packages.clear()
                    grid = Gtk.Grid()
                # category change
                if line.startswith("- name: "):
                    # Generate the vboxStack item and name for use later (and in packing)
                    name = line.strip("- name: ").strip().strip('"')
                    vboxStackNames.append(name)
                    vboxStacks.append(
                        Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
                    )

        # Now we pack the stack
        item_num = 0
        for item in vboxStacks:
            stack.add_titled(item, "stack" + str(item_num), vboxStackNames[item_num])
            item_num += 1

        # Place the stack switcher and the stack together into a vbox
        vbox.pack_start(scrolledSwitch, False, False, 0)
        vbox.pack_start(stack, True, True, 0)

        # Stuff the vbox with the title and seperator to create the page
        vboxStack1.pack_start(cat_name, False, False, 0)
        vboxStack1.pack_start(seperator, False, False, 0)
        vboxStack1.pack_start(vbox, False, False, 0)

    except Exception as e:
        print("Exception in GUI(): %s" % e)
