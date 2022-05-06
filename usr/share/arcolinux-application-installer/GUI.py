# =================================================================
# =                 Author: Cameron Percival                      =
# =================================================================


# ============Functions============
import Functions
import App_Frame_GUI
from queue import Queue
from threading import Thread

class GUI_Worker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            #pull what we need from the queue so we can process properly.
            self, Gtk, vboxStack1, Functions, category, package_file = self.queue.get()
            try:
                App_Frame_GUI.GUI(self, Gtk, vboxStack1, Functions, category, package_file)
            finally:
                self.queue.task_done()

def GUI(self, Gtk, Gdk, GdkPixbuf, base_dir, os, Pango):  # noqa
    process = Functions.subprocess.run(["sh", "-c", "echo \"$SHELL\""],
                             stdout=Functions.subprocess.PIPE)

    output = process.stdout.decode().strip()

    # =======================================================
    #                       App Notifications
    # =======================================================

    hbox0 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

    self.notification_revealer = Gtk.Revealer()
    self.notification_revealer.set_reveal_child(False)

    self.notification_label = Gtk.Label()

    pb_panel = GdkPixbuf.Pixbuf().new_from_file(base_dir + '/images/panel.png')
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

    #This section sets up the tabs, and the array for dealing with the tab content
    conf_files_unsorted = []
    yaml_files_unsorted = []
    path = base_dir + "/yaml/"
    for file in os.listdir(path):
        if file.endswith(".yaml"):
            #TODO: Add a function or series of steps to compare file dates
            # against an online location, for e.g. github or website, and update
            # if need be.
            yaml_files_unsorted.append(file)
        else:
            print("Unsupported configuration file type. Please contact Arcolinux Support.")
    #Need to sort the list (Or do we? I choose to)
    yaml_files = sorted(yaml_files_unsorted)


    # ==========================================================
    #                       GENERATE STACK
    # ==========================================================
    stack = Gtk.Stack()
    #stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
    stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    stack.set_transition_duration(350)

    vboxStack = [ ]
    stack_item = 0

    #8 threads
    for x in range (8):
        worker = GUI_Worker(self.queue)
        #Set the worker to be True to allow processing, and avoid Blocking
        worker.daemon = True
        worker.start()

    #This code section might look a little weird. It is because it was
    #derived from another function before this version was required.
    for item in yaml_files:
        # NOTE: IF the yaml file name standard changes, be sure to update this, or weirdness will follow.
        name = item[11:-5].strip().capitalize()#.strip(".yaml")
        vboxStack.append(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10))
        stack.add_titled(vboxStack[stack_item], str("stack"+str(len(vboxStack))), name)
        #Multithreading!
        self.queue.put((self, Gtk, vboxStack[stack_item], Functions, name, path+yaml_files[stack_item]))
        stack_item+=1
    #TODO: REWRITE THIS CODE TO WORK WITH NEW FILE STRUCTURE
    #for item in conf_files:
    #    with open(path+item, "r") as f:
    #            content = f.readlines()
    #            f.close()
    #    pos = Functions._get_position(content, "title: ")
    #    # Okay, this is a little odd at first look. Strip whitespace, THEN strip title,
    #    # then strip whitespace, then strip quotation marks. (Each strip only removes front and end character matches)
    #    name = content[pos].strip().strip("title:").strip().strip('"')
    #    vboxStack.append(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10))
    #    stack.add_titled(vboxStack[stack_item], str("stack"+str(len(vboxStack))), name)
    #    #Multithreading!
    #    self.queue.put((self, Gtk, vboxStack[stack_item], Functions, name, path+yaml_files[stack_item]))
    #    stack_item+=1

    #safety to ensure that we finish threading before we continue on.
    self.queue.join()

    stack_switcher = Gtk.StackSidebar()
    stack_switcher.set_name("sidebar")
    stack_switcher.set_stack(stack)

    # =====================================================
    #                       LOGO
    # =====================================================
    ivbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    pixbuf = GdkPixbuf.Pixbuf().new_from_file_at_size(
        os.path.join(base_dir, 'images/arcolinux-stock.png'), 45, 45)
    image = Gtk.Image().new_from_pixbuf(pixbuf)


    # =====================================================
    #               RESTART BUTTON
    # =====================================================

    #btnReStartAtt = Gtk.Button(label="Restart ATT")
    #btnReStartAtt.connect('clicked', self.on_refresh_att_clicked)
    #btnReStartAtt.set_property("has-tooltip", True)
    #btnReStartAtt.connect("query-tooltip", self.tooltip_callback,
    #           "Restart the ArcoLinux Tweak Tool")

    # =====================================================
    #                      PACKS
    # =====================================================

    hbox1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
    hbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
    hbox3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

    #hbox3.pack_start(btnReStartAtt, False, False, 0)

    ivbox.pack_start(image, False, False, 0)
    ivbox.pack_start(stack_switcher, True, True, 0)

    ivbox.pack_start(hbox2, False, False, 0)
    ivbox.pack_start(hbox3, False, False, 0)

    vbox1.pack_start(hbox0, False, False, 0)
    vbox1.pack_start(stack, True, True, 0)

    hbox.pack_start(ivbox, False, True, 0)
    hbox.pack_start(vbox1, True, True, 0)

    stack.set_hhomogeneous(False)
    stack.set_vhomogeneous(False)
