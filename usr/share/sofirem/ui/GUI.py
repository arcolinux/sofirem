# =================================================================
# =                 Author: Cameron Percival                      =
# =================================================================


# ============Functions============
import Functions as fn
from ui.AppFrameGUI import AppFrameGUI
from multiprocessing import cpu_count
from queue import Queue
from threading import Thread

base_dir = fn.os.path.abspath(fn.os.path.join(fn.os.path.dirname(__file__), ".."))
# base_dir = fn.os.path.dirname(fn.os.path.realpath(__file__))


class GUI_Worker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # pull what we need from the queue so we can process properly.
            items = self.queue.get()

            try:
                # make sure we have the required number of items on the queue
                if items is not None:
                    # self, Gtk, vboxStack1, category, package_file = items

                    self, Gtk, vbox_stack, category, packages = items

                    AppFrameGUI.build_ui_frame(
                        self,
                        Gtk,
                        vbox_stack,
                        category,
                        packages,
                    )

            except Exception as e:
                fn.logger.error("Exception in GUI_Worker(): %s" % e)
            finally:
                if items is None:
                    fn.logger.debug("Stopping GUI Worker thread")
                    self.queue.task_done()
                    return False
                self.queue.task_done()


class GUI:
    def setup_gui_search(
        self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango, search_results, search_term
    ):
        try:
            # remove previous vbox
            if self.search_activated == False:
                self.remove(self.vbox)
            else:
                self.remove(self.vbox_search)

            # lets quickly create the latest installed list.
            fn.get_current_installed()

            # =======================================================
            #                       HeaderBar
            # =======================================================

            setup_headerbar(self, Gtk)

            # =======================================================
            #                       App Notifications
            # =======================================================

            hbox0 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

            self.notification_revealer = Gtk.Revealer()
            self.notification_revealer.set_reveal_child(False)

            self.notification_label = Gtk.Label()

            pb_panel = GdkPixbuf.Pixbuf().new_from_file(base_dir + "/images/panel.png")
            panel = Gtk.Image().new_from_pixbuf(pb_panel)

            overlay_frame = Gtk.Overlay()
            overlay_frame.add(panel)
            overlay_frame.add_overlay(self.notification_label)

            self.notification_revealer.add(overlay_frame)

            hbox0.pack_start(self.notification_revealer, True, False, 0)

            # ==========================================================
            #                       CONTAINER
            # ==========================================================

            self.vbox_search = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            vbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

            self.vbox_search.pack_start(hbox, True, True, 0)
            self.add(self.vbox_search)

            # ==========================================================
            #                    PREP WORK
            # ==========================================================

            # This section sets up the tabs, and the array for dealing with the tab content

            # ==========================================================
            #                       GENERATE STACK
            # ==========================================================
            stack = Gtk.Stack()
            # stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
            stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            stack.set_transition_duration(350)

            vbox_stack = []
            stack_item = 0

            # Max Threads
            """
                Fatal Python error: Segmentation fault
                This error happens randomly, due to the for loop iteration on the cpu_count
                old code: for x in range(cpu_count()):
            """

            # spawn only 1 GUI_Worker threads, as any number greater causes a Segmentation fault

            search_worker = GUI_Worker(self.queue)
            search_worker.name = "thread_GUI_search_worker"
            # Set the worker to be True to allow processing, and avoid Blocking
            # search_worker.daemon = True
            search_worker.start()

            # This code section might look a little weird. It is because it was
            # derived from another function before this version was required.

            for category in search_results:
                # NOTE: IF the yaml file name standard changes, be sure to update this, or weirdness will follow.

                # subcategory = search_results[category][0].subcategory
                vbox_stack.append(
                    Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
                )
                stack.add_titled(
                    vbox_stack[stack_item],
                    str("stack" + str(len(vbox_stack))),
                    category,
                )

                # subcategory_desc = search_results[category][0].subcategory_description
                search_res_lst = search_results[category]

                # Multithreading!

                self.queue.put(
                    (
                        self,
                        Gtk,
                        vbox_stack[stack_item],
                        category,
                        search_res_lst,
                    )
                )

                stack_item += 1

            # send a signal that no further items are to be put on the queue
            self.queue.put(None)
            # safety to ensure that we finish threading before we continue on.
            self.queue.join()
            fn.logger.debug("GUI Worker thread completed")

            stack_switcher = Gtk.StackSidebar()
            stack_switcher.set_name("sidebar")
            stack_switcher.set_stack(stack)

            # =====================================================
            #                       LOGO
            # =====================================================

            ivbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            pixbuf = GdkPixbuf.Pixbuf().new_from_file_at_size(
                os.path.join(base_dir, "images/sofirem.png"), 45, 45
            )
            image = Gtk.Image().new_from_pixbuf(pixbuf)

            # remove the focus on startup from search entry
            ivbox.set_property("can-focus", True)
            Gtk.Window.grab_focus(ivbox)

            # =====================================================
            #               RECACHE BUTTON
            # =====================================================

            btn_recache = Gtk.Button(label="Recache Applications")
            btn_recache.connect("clicked", self.recache_clicked)
            # btnReCache.set_property("has-tooltip", True)
            # btnReCache.connect("query-tooltip", self.tooltip_callback,
            #           "Refresh the application cache")

            # =====================================================
            #                   REPOS
            # =====================================================

            # if not (
            #     fn.check_package_installed("arcolinux-keyring")
            #     or fn.check_package_installed("arcolinux-mirrorlist-git")
            # ):
            #     self.btnRepos = Gtk.Button(label="Add ArcoLinux Repo")
            #     self.btnRepos._value = 1
            # else:
            #     self.btnRepos = Gtk.Button(label="Remove ArcoLinux Repo")
            #     self.btnRepos._value = 2
            #
            # self.btnRepos.set_size_request(100, 30)
            # self.btnRepos.connect("clicked", self.on_repos_clicked)

            # =====================================================
            #               QUIT BUTTON
            # =====================================================

            btn_quit_app = Gtk.Button(label="Quit")
            btn_quit_app.set_size_request(100, 30)
            btn_quit_app.connect("clicked", self.on_close, "delete-event")
            btn_context = btn_quit_app.get_style_context()
            btn_context.add_class("destructive-action")

            # =====================================================
            #               SEARCH BOX
            # =====================================================

            self.searchentry = Gtk.SearchEntry()
            self.searchentry.set_text(search_term)
            self.searchentry.connect("activate", self.on_search_activated)
            self.searchentry.connect("icon-release", self.on_search_cleared)

            iv_searchbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

            # =====================================================
            #                      PACKS
            # =====================================================

            # hbox1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            # hbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            # hbox3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

            # hbox3.pack_start(btnReCache, False, False, 0)

            iv_searchbox.pack_start(self.searchentry, False, False, 0)

            ivbox.pack_start(image, False, False, 0)
            ivbox.pack_start(iv_searchbox, False, False, 0)
            ivbox.pack_start(stack_switcher, True, True, 0)

            ivbox.pack_start(btn_quit_app, False, False, 0)

            vbox1.pack_start(hbox0, False, False, 0)
            vbox1.pack_start(stack, True, True, 0)

            hbox.pack_start(ivbox, False, True, 0)
            hbox.pack_start(vbox1, True, True, 0)

            stack.set_hhomogeneous(False)
            stack.set_vhomogeneous(False)

            self.show_all()

        except Exception as err:
            fn.logger.error("Exception in GUISearch(): %s" % err)

    def setup_gui(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango):  # noqa
        try:
            # reset back to main box
            if self.search_activated:
                # remove the search vbox
                self.remove(self.vbox_search)
                self.show_all()

            # lets quickly create the latest installed list.
            fn.get_current_installed()

            # =======================================================
            #                       HeaderBar
            # =======================================================

            setup_headerbar(self, Gtk)

            # =======================================================
            #                       App Notifications
            # =======================================================

            hbox0 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

            self.notification_revealer = Gtk.Revealer()
            self.notification_revealer.set_reveal_child(False)

            self.notification_label = Gtk.Label()

            pb_panel = GdkPixbuf.Pixbuf().new_from_file(base_dir + "/images/panel.png")
            panel = Gtk.Image().new_from_pixbuf(pb_panel)

            overlay_frame = Gtk.Overlay()
            overlay_frame.add(panel)
            overlay_frame.add_overlay(self.notification_label)

            self.notification_revealer.add(overlay_frame)

            hbox0.pack_start(self.notification_revealer, True, False, 0)

            # ==========================================================
            #                       CONTAINER
            # ==========================================================

            self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            vbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

            self.vbox.pack_start(hbox, True, True, 0)
            self.add(self.vbox)

            # ==========================================================
            #                    PREP WORK
            # ==========================================================

            # This section sets up the tabs, and the array for dealing with the tab content
            """
            yaml_files_unsorted = []
            path = base_dir + "/yaml/"
            for file in os.listdir(path):
                if file.endswith(".yaml"):
                    yaml_files_unsorted.append(file)
                else:
                    print(
                        "Unsupported configuration file type. Please contact Arcolinux Support."
                    )
            # Need to sort the list (Or do we? I choose to)
            yaml_files = sorted(yaml_files_unsorted)
            """

            # Check github for updated files
            # fn.check_github(yaml_files)
            # ==========================================================
            #                       GENERATE STACK
            # ==========================================================
            stack = Gtk.Stack()
            # stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
            stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            stack.set_transition_duration(350)

            vbox_stack = []
            stack_item = 0

            # Max Threads
            """
                Fatal Python error: Segmentation fault
                This error happens randomly, due to the for loop iteration on the cpu_count
                old code: for x in range(cpu_count()):
            """

            # spawn only 1 GUI_Worker threads, as any number greater causes a Segmentation fault

            worker = GUI_Worker(self.queue)
            worker.name = "thread_GUI_Worker"
            # Set the worker to be True to allow processing, and avoid Blocking
            # worker.daemon = True
            worker.start()

            for category in self.packages:
                # NOTE: IF the yaml file name standard changes, be sure to update this, or weirdness will follow.

                # this is the side stack listing all categories
                vbox_stack.append(
                    Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
                )
                stack.add_titled(
                    vbox_stack[stack_item],
                    str("stack" + str(len(vbox_stack))),
                    category,
                )

                packages_lst = self.packages[category]

                # Multithreading!
                self.queue.put(
                    (
                        self,
                        Gtk,
                        vbox_stack[stack_item],
                        category,
                        packages_lst,
                    )
                )
                stack_item += 1

            # send a signal that no further items are to be put on the queue
            self.queue.put(None)
            # safety to ensure that we finish threading before we continue on.

            self.queue.join()
            fn.logger.debug("GUI Worker thread completed")

            stack_switcher = Gtk.StackSidebar()
            stack_switcher.set_name("sidebar")
            stack_switcher.set_stack(stack)

            # =====================================================
            #                       LOGO
            # =====================================================

            ivbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            pixbuf = GdkPixbuf.Pixbuf().new_from_file_at_size(
                os.path.join(base_dir, "images/sofirem.png"), 45, 45
            )
            image = Gtk.Image().new_from_pixbuf(pixbuf)

            # remove the focus on startup from search entry
            ivbox.set_property("can-focus", True)
            Gtk.Window.grab_focus(ivbox)

            # =====================================================
            #               RECACHE BUTTON
            # =====================================================

            # btnReCache = Gtk.Button(label="Recache Applications")
            # btnReCache.connect("clicked", self.recache_clicked)
            # btnReCache.set_property("has-tooltip", True)
            # btnReCache.connect("query-tooltip", self.tooltip_callback,
            #           "Refresh the application cache")

            # =====================================================
            #                   REPOS
            # =====================================================

            # =====================================================
            #               QUIT BUTTON
            # =====================================================
            btn_quit_app = Gtk.Button(label="Quit")
            btn_quit_app.set_size_request(100, 30)
            btn_quit_app.connect("clicked", self.on_close, "delete-event")
            btn_context = btn_quit_app.get_style_context()
            btn_context.add_class("destructive-action")
            # =====================================================
            #               SEARCH BOX
            # =====================================================
            self.searchentry = Gtk.SearchEntry()
            self.searchentry.set_placeholder_text("Search...")
            self.searchentry.connect("activate", self.on_search_activated)
            self.searchentry.connect("icon-release", self.on_search_cleared)

            ivsearchbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

            ivsearchbox.pack_start(self.searchentry, False, False, 0)

            ivbox.pack_start(image, False, False, 0)
            ivbox.pack_start(ivsearchbox, False, False, 0)
            ivbox.pack_start(stack_switcher, True, True, 0)
            ivbox.pack_start(btn_quit_app, False, False, 0)

            vbox1.pack_start(hbox0, False, False, 0)
            vbox1.pack_start(stack, True, True, 0)

            hbox.pack_start(ivbox, False, True, 0)
            hbox.pack_start(vbox1, True, True, 0)

            stack.set_hhomogeneous(False)
            stack.set_vhomogeneous(False)

            if self.search_activated:
                self.show_all()

        except Exception as e:
            fn.logger.error("Exception in GUI(): %s" % e)


# setup headerbar including popover settings
def setup_headerbar(self, Gtk):
    try:
        header_bar_title = "Sofirem"
        headerbar = Gtk.HeaderBar()
        headerbar.set_title(header_bar_title)
        headerbar.set_show_close_button(True)

        self.set_titlebar(headerbar)

        toolbuttonSettings = Gtk.ToolButton()
        # icon-name open-menu-symbolic / open-menu-symbolic.symbolic
        toolbuttonSettings.set_icon_name("open-menu-symbolic.symbolic")
        # toolbuttonSettings.set_icon_name(Gtk.STOCK_PREFERENCES)
        toolbuttonSettings.connect("clicked", self.on_settings_clicked)

        headerbar.pack_end(toolbuttonSettings)

        self.popover = Gtk.Popover()
        self.popover.set_relative_to(toolbuttonSettings)

        vbox = Gtk.Box(spacing=0, orientation=Gtk.Orientation.VERTICAL)
        vbox.set_border_width(15)

        # switch to display package versions
        self.switch_pkg_version = Gtk.Switch()
        self.switch_pkg_version.set_halign(Gtk.Align(1))

        # button to open the pacman log monitoring dialog
        self.btn_pacmanlog = Gtk.ModelButton(label="Open Pacman Log File")

        self.btn_pacmanlog.connect("clicked", self.on_pacman_log_clicked)
        self.btn_pacmanlog.set_alignment(xalign=0, yalign=0)

        # button to export list of installed packages to disk
        btn_packages_export = Gtk.ModelButton(label="Show Installed Packages")
        btn_packages_export.connect("clicked", self.on_packages_export_clicked)
        btn_packages_export.set_alignment(xalign=0, yalign=0)

        # button to show about dialog
        btn_about_app = Gtk.ModelButton(label="About Sofirem")
        btn_about_app.connect("clicked", self.on_about_app_clicked)
        btn_about_app.set_alignment(xalign=0, yalign=0)

        if self.display_versions == True:
            self.switch_pkg_version.set_active(True)
        else:
            self.switch_pkg_version.set_active(False)

        self.switch_pkg_version.connect("notify::active", self.version_toggle)

        self.switch_arco_keyring = Gtk.Switch()
        self.switch_arco_keyring.set_halign(Gtk.Align(1))

        lbl_arco_keyring = Gtk.Label(xalign=0, yalign=0)
        lbl_arco_keyring.set_text("Import ArcoLinux Keyring")

        self.switch_arco_mirrorlist = Gtk.Switch()
        self.switch_arco_mirrorlist.set_halign(Gtk.Align(1))

        lbl_arco_mirrorlist = Gtk.Label(xalign=0, yalign=0)
        lbl_arco_mirrorlist.set_text("Import ArcoLinux Mirrorlist")

        if (
            fn.check_package_installed("arcolinux-keyring") is False
            or fn.verify_arco_pacman_conf() is False
        ):
            self.switch_arco_keyring.set_state(False)

        else:
            self.switch_arco_keyring.set_state(True)

        self.switch_arco_keyring.connect("state-set", self.arco_keyring_toggle)

        if (
            fn.check_package_installed("arcolinux-mirrorlist-git") is False
            or fn.verify_arco_pacman_conf() is False
        ):
            self.switch_arco_mirrorlist.set_state(False)

        else:
            self.switch_arco_mirrorlist.set_state(True)

        self.switch_arco_mirrorlist.connect("state-set", self.arco_mirrorlist_toggle)

        # switch to display/hide package install/uninstall progress dialog

        lbl_package_progress = Gtk.Label(xalign=0, yalign=0)
        lbl_package_progress.set_text("Display Package Progress Window")

        self.switch_package_progress = Gtk.Switch()
        self.switch_package_progress.set_halign(Gtk.Align(1))
        self.switch_package_progress.set_active(True)

        self.switch_package_progress.connect(
            "notify::active", self.package_progress_toggle
        )

        lbl_pkg_version = Gtk.Label(xalign=0, yalign=0)
        lbl_pkg_version.set_text("Display Package Version")

        hbox1 = Gtk.Box(spacing=10, orientation=Gtk.Orientation.HORIZONTAL)
        hbox1.set_border_width(5)
        hbox1.pack_start(lbl_pkg_version, True, True, 1)
        hbox1.pack_start(self.switch_pkg_version, True, True, 1)

        hbox2 = Gtk.Box(spacing=10, orientation=Gtk.Orientation.HORIZONTAL)
        hbox2.set_border_width(5)
        hbox2.pack_start(lbl_arco_keyring, True, True, 1)
        hbox2.pack_start(self.switch_arco_keyring, True, True, 1)

        hbox3 = Gtk.Box(spacing=10, orientation=Gtk.Orientation.HORIZONTAL)
        hbox3.set_border_width(5)
        hbox3.pack_start(lbl_arco_mirrorlist, True, True, 1)
        hbox3.pack_start(self.switch_arco_mirrorlist, True, True, 1)

        hbox4 = Gtk.Box(spacing=10, orientation=Gtk.Orientation.HORIZONTAL)
        hbox4.set_border_width(5)
        hbox4.pack_start(lbl_package_progress, True, True, 1)
        hbox4.pack_start(self.switch_package_progress, True, True, 1)

        hbox5 = Gtk.Box(spacing=10, orientation=Gtk.Orientation.HORIZONTAL)
        hbox5.set_border_width(5)
        hbox5.pack_start(self.btn_pacmanlog, True, True, 1)

        hbox6 = Gtk.Box(spacing=10, orientation=Gtk.Orientation.HORIZONTAL)
        hbox6.set_border_width(5)
        hbox6.pack_start(btn_packages_export, True, True, 1)

        hbox7 = Gtk.Box(spacing=10, orientation=Gtk.Orientation.HORIZONTAL)
        hbox7.set_border_width(5)
        hbox7.pack_start(btn_about_app, True, True, 1)

        vbox.pack_start(hbox1, True, True, 1)
        vbox.pack_start(hbox2, True, True, 1)
        vbox.pack_start(hbox3, True, True, 1)
        vbox.pack_start(hbox4, True, True, 1)
        vbox.pack_start(hbox5, True, True, 1)
        vbox.pack_start(hbox6, True, True, 1)
        vbox.pack_start(hbox7, True, True, 1)

        self.popover.add(vbox)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
    except Exception as e:
        fn.logger.error("Exception in setup_headerbar(): %s" % e)
