# =================================================================
# =                 Author: Cameron Percival                      =
# =================================================================


# ============Functions============
import Functions as fn
import App_Frame_GUI
from multiprocessing import cpu_count
from queue import Queue
from threading import Thread

base_dir = fn.os.path.dirname(fn.os.path.realpath(__file__))


class GUI_Worker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # pull what we need from the queue so we can process properly.
            items = self.queue.get()
            try:
                # reached the end of items on the queue
                if items is None:
                    break

                # make sure we have the required number of items on the queue
                if len(items) == 5:
                    # self, Gtk, vboxStack1, category, package_file = items
                    self, Gtk, vboxStack1, category, packages = items
                    App_Frame_GUI.GUI(
                        self,
                        Gtk,
                        vboxStack1,
                        category,
                        packages,
                    )

            except Exception as e:
                print("Exception in GUI_Worker(): %s" % e)
            finally:
                self.queue.task_done()


def GUISearch(
    self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango, search_results, search_term
):
    try:
        # remove previous vbox
        if self.search_activated == False:
            self.remove(self.vbox_main)
        else:
            self.remove(self.vbox_search)

        # lets quickly create the latest installed list.
        fn.get_current_installed()

        # =======================================================
        #                       App Notifications
        # =======================================================

        hbox0 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.notification_revealer = Gtk.Revealer()
        self.notification_revealer.set_reveal_child(False)

        self.notification_label = Gtk.Label()

        pb_panel = GdkPixbuf.Pixbuf().new_from_file(base_dir + "/images/panel.png")
        panel = Gtk.Image().new_from_pixbuf(pb_panel)

        overlayFrame = Gtk.Overlay()
        overlayFrame.add(panel)
        overlayFrame.add_overlay(self.notification_label)

        self.notification_revealer.add(overlayFrame)

        hbox0.pack_start(self.notification_revealer, True, False, 0)

        # ==========================================================
        #                       CONTAINER
        # ==========================================================

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        vbox.pack_start(hbox, True, True, 0)
        self.add(vbox)

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

        vboxStack = []
        stack_item = 0

        # Max Threads
        """
            Fatal Python error: Segmentation fault
            This error happens randomly, due to the for loop iteration on the cpu_count
            old code: for x in range(cpu_count()):
        """

        # spawn only 1 GUI_Worker threads, as any number greater causes a Segmentation fault

        search_worker = GUI_Worker(self.queue)
        # Set the worker to be True to allow processing, and avoid Blocking
        search_worker.daemon = True
        search_worker.start()

        # This code section might look a little weird. It is because it was
        # derived from another function before this version was required.

        for category in search_results:
            # NOTE: IF the yaml file name standard changes, be sure to update this, or weirdness will follow.

            # subcategory = search_results[category][0].subcategory
            vboxStack.append(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10))
            stack.add_titled(
                vboxStack[stack_item], str("stack" + str(len(vboxStack))), category
            )

            # subcategory_desc = search_results[category][0].subcategory_description
            search_res_lst = search_results[category]

            # Multithreading!

            self.queue.put(
                (
                    self,
                    Gtk,
                    vboxStack[stack_item],
                    category,
                    search_res_lst,
                )
            )

            stack_item += 1

        # send a signal that no further items are to be put on the queue
        self.queue.put(None)
        # safety to ensure that we finish threading before we continue on.
        self.queue.join()

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

        btnReCache = Gtk.Button(label="Recache Applications")
        btnReCache.connect("clicked", self.recache_clicked)
        # btnReCache.set_property("has-tooltip", True)
        # btnReCache.connect("query-tooltip", self.tooltip_callback,
        #           "Refresh the application cache")

        # =====================================================
        #                   REPOS
        # =====================================================

        if not (
            fn.check_package_installed("arcolinux-keyring")
            or fn.check_package_installed("arcolinux-mirrorlist-git")
        ):
            self.btnRepos = Gtk.Button(label="Add repos")
            self.btnRepos._value = 1
        else:
            self.btnRepos = Gtk.Button(label="Remove repos")
            self.btnRepos._value = 2

        self.btnRepos.set_size_request(100, 30)
        self.btnRepos.connect("clicked", self.on_repos_clicked)

        # =====================================================
        #               QUIT BUTTON
        # =====================================================

        btnQuitSofi = Gtk.Button(label="Quit")
        btnQuitSofi.set_size_request(100, 30)
        btnQuitSofi.connect("clicked", self.on_close, "delete-event")

        # =====================================================
        #               SEARCH BOX
        # =====================================================

        self.searchEntry = Gtk.SearchEntry()
        self.searchEntry.set_text(search_term)
        self.searchEntry.connect("activate", self.on_search_activated)
        self.searchEntry.connect("icon-release", self.on_search_cleared)

        ivSearchbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # =====================================================
        #                      PACKS
        # =====================================================

        # hbox1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        # hbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        # hbox3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

        # hbox3.pack_start(btnReCache, False, False, 0)

        ivSearchbox.pack_start(self.searchEntry, False, False, 0)

        ivbox.pack_start(image, False, False, 0)
        ivbox.pack_start(ivSearchbox, False, False, 0)
        ivbox.pack_start(stack_switcher, True, True, 0)

        # ivbox.pack_start(btnReCache, False, False, 0)
        ivbox.pack_start(self.btnRepos, False, False, 0)
        ivbox.pack_start(btnQuitSofi, False, False, 0)

        vbox1.pack_start(hbox0, False, False, 0)
        vbox1.pack_start(stack, True, True, 0)

        hbox.pack_start(ivbox, False, True, 0)
        hbox.pack_start(vbox1, True, True, 0)

        stack.set_hhomogeneous(False)
        stack.set_vhomogeneous(False)

        self.show_all()

        return vbox

    except Exception as err:
        print("Exception in GUISearch(): %s" % err)


def GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango):  # noqa
    try:
        # reset back to main box

        if self.search_activated:
            # remove the search vbox
            self.remove(self.vbox_search)
            self.show_all()

        # lets quickly create the latest installed list.
        fn.get_current_installed()

        # =======================================================
        #                       App Notifications
        # =======================================================

        hbox0 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.notification_revealer = Gtk.Revealer()
        self.notification_revealer.set_reveal_child(False)

        self.notification_label = Gtk.Label()

        pb_panel = GdkPixbuf.Pixbuf().new_from_file(base_dir + "/images/panel.png")
        panel = Gtk.Image().new_from_pixbuf(pb_panel)

        overlayFrame = Gtk.Overlay()
        overlayFrame.add(panel)
        overlayFrame.add_overlay(self.notification_label)

        self.notification_revealer.add(overlayFrame)

        hbox0.pack_start(self.notification_revealer, True, False, 0)

        # ==========================================================
        #                       CONTAINER
        # ==========================================================

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox1 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        vbox.pack_start(hbox, True, True, 0)
        self.add(vbox)

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

        vboxStack = []
        stack_item = 0

        # Max Threads
        """
            Fatal Python error: Segmentation fault
            This error happens randomly, due to the for loop iteration on the cpu_count
            old code: for x in range(cpu_count()):
        """

        # spawn only 1 GUI_Worker threads, as any number greater causes a Segmentation fault

        worker = GUI_Worker(self.queue)
        # Set the worker to be True to allow processing, and avoid Blocking
        worker.daemon = True
        worker.start()

        for category in self.packages:
            # NOTE: IF the yaml file name standard changes, be sure to update this, or weirdness will follow.

            # this is the side stack listing all categories
            vboxStack.append(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10))
            stack.add_titled(
                vboxStack[stack_item], str("stack" + str(len(vboxStack))), category
            )

            packages_lst = self.packages[category]

            # Multithreading!
            self.queue.put(
                (
                    self,
                    Gtk,
                    vboxStack[stack_item],
                    category,
                    packages_lst,
                )
            )
            stack_item += 1

        # send a signal that no further items are to be put on the queue
        self.queue.put(None)
        # safety to ensure that we finish threading before we continue on.
        self.queue.join()

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

        btnReCache = Gtk.Button(label="Recache Applications")
        btnReCache.connect("clicked", self.recache_clicked)
        # btnReCache.set_property("has-tooltip", True)
        # btnReCache.connect("query-tooltip", self.tooltip_callback,
        #           "Refresh the application cache")

        # =====================================================
        #                   REPOS
        # =====================================================

        if not (
            fn.check_package_installed("arcolinux-keyring")
            or fn.check_package_installed("arcolinux-mirrorlist-git")
        ):
            self.btnRepos = Gtk.Button(label="Add repos")
            self.btnRepos._value = 1
        else:
            self.btnRepos = Gtk.Button(label="Remove repos")
            self.btnRepos._value = 2

        self.btnRepos.set_size_request(100, 30)
        self.btnRepos.connect("clicked", self.on_repos_clicked)

        # =====================================================
        #               QUIT BUTTON
        # =====================================================
        btnQuitSofi = Gtk.Button(label="Quit")
        btnQuitSofi.set_size_request(100, 30)
        btnQuitSofi.connect("clicked", self.on_close, "delete-event")

        # =====================================================
        #               SEARCH BOX
        # =====================================================
        self.searchEntry = Gtk.SearchEntry()
        self.searchEntry.set_placeholder_text("Search...")
        self.searchEntry.connect("activate", self.on_search_activated)
        self.searchEntry.connect("icon-release", self.on_search_cleared)

        ivSearchbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        ivSearchbox.pack_start(self.searchEntry, False, False, 0)

        ivbox.pack_start(image, False, False, 0)
        ivbox.pack_start(ivSearchbox, False, False, 0)
        ivbox.pack_start(stack_switcher, True, True, 0)

        # leaving cache button out
        # ivbox.pack_start(btnReCache, False, False, 0)
        ivbox.pack_start(self.btnRepos, False, False, 0)
        ivbox.pack_start(btnQuitSofi, False, False, 0)

        vbox1.pack_start(hbox0, False, False, 0)
        vbox1.pack_start(stack, True, True, 0)

        hbox.pack_start(ivbox, False, True, 0)
        hbox.pack_start(vbox1, True, True, 0)

        stack.set_hhomogeneous(False)
        stack.set_vhomogeneous(False)

        if self.search_activated:
            self.show_all()

        return vbox
    except Exception as e:
        print("Exception in GUI(): %s" % e)
