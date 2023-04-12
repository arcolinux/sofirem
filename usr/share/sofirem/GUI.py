# =================================================================
# =                 Author: Cameron Percival                      =
# =================================================================


# ============Functions============
import Functions
import App_Frame_GUI
from multiprocessing import cpu_count
from queue import Queue
from threading import Thread

base_dir = Functions.os.path.dirname(Functions.os.path.realpath(__file__))


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
                    self, Gtk, vboxStack1, category, package_file = items
                    App_Frame_GUI.GUI(self, Gtk, vboxStack1, category, package_file)

            except Exception as e:
                print("Exception in GUI_Worker(): %s" % e)
            finally:
                self.queue.task_done()


def GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango):  # noqa
    try:
        process = Functions.subprocess.run(
            ["sh", "-c", 'echo "$SHELL"'], stdout=Functions.subprocess.PIPE
        )

        output = process.stdout.decode().strip()

        # lets quickly create the latest installed list.
        Functions.get_current_installed(base_dir + "/cache/installed.lst")

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
        conf_files_unsorted = []
        yaml_files_unsorted = []
        path = base_dir + "/yaml/"
        for file in os.listdir(path):
            if file.endswith(".yaml"):
                # TODO: Add a function or series of steps to compare file dates
                # against an online location, for e.g. github or website, and update
                # if need be.
                yaml_files_unsorted.append(file)
            else:
                print(
                    "Unsupported configuration file type. Please contact Arcolinux Support."
                )
        # Need to sort the list (Or do we? I choose to)
        yaml_files = sorted(yaml_files_unsorted)

        # Check github for updated files
        # Functions.check_github(yaml_files)
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

        # This code section might look a little weird. It is because it was
        # derived from another function before this version was required.
        for item in yaml_files:
            # NOTE: IF the yaml file name standard changes, be sure to update this, or weirdness will follow.
            name = item[11:-5].strip().capitalize()  # .strip(".yaml")
            vboxStack.append(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10))
            stack.add_titled(
                vboxStack[stack_item], str("stack" + str(len(vboxStack))), name
            )
            # Multithreading!
            self.queue.put(
                (
                    self,
                    Gtk,
                    vboxStack[stack_item],
                    name,
                    path + yaml_files[stack_item],
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

        # =====================================================
        #               RECACHE BUTTON
        # =====================================================

        btnReCache = Gtk.Button(label="Recache Applications")
        btnReCache.connect("clicked", self.recache_clicked)
        # btnReCache.set_property("has-tooltip", True)
        # btnReCache.connect("query-tooltip", self.tooltip_callback,
        #           "Refresh the application cache")

        # =====================================================
        #               QUIT BUTTON
        # =====================================================
        btnQuitSofi = Gtk.Button(label="Quit")
        btnQuitSofi.set_size_request(100, 30)
        btnQuitSofi.connect("clicked", self.on_close, "delete-event")

        # =====================================================
        #                      PACKS
        # =====================================================

        # hbox1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        # hbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        # hbox3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

        # hbox3.pack_start(btnReCache, False, False, 0)

        ivbox.pack_start(image, False, False, 0)
        ivbox.pack_start(stack_switcher, True, True, 0)

        # ivbox.pack_start(hbox2, False, False, 0)
        ivbox.pack_start(btnReCache, False, False, 0)
        ivbox.pack_start(btnQuitSofi, False, False, 0)

        vbox1.pack_start(hbox0, False, False, 0)
        vbox1.pack_start(stack, True, True, 0)

        hbox.pack_start(ivbox, False, True, 0)
        hbox.pack_start(vbox1, True, True, 0)

        stack.set_hhomogeneous(False)
        stack.set_vhomogeneous(False)
    except Exception as e:
        print("Exception in GUI(): %s" % e)
