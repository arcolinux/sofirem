from gi.repository import Gtk, GLib
import gi


# Since a system can have multiple versions
# of GTK + installed, we want to make
# sure that we are importing GTK + 3.
gi.require_version("Gtk", "3.0")


class ProgressBarWindow(Gtk.Window):
    new_value = 0.0

    def __init__(self):
        Gtk.Window.__init__(self, title="Progress Bar")
        self.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add(vbox)

        # Create a ProgressBar
        self.progressbar = Gtk.ProgressBar()
        vbox.pack_start(self.progressbar, True, True, 0)

        # Create CheckButton with labels "Show text",
        # "Activity mode", "Right to Left" respectively
        # button = Gtk.CheckButton(label="Show text")
        # button.connect("toggled", self.on_show_text_toggled)
        # vbox.pack_start(button, True, True, 0)

        # button = Gtk.CheckButton(label="Activity mode")
        # button.connect("toggled", self.on_activity_mode_toggled)
        # vbox.pack_start(button, True, True, 0)

        # button = Gtk.CheckButton(label="Right to Left")
        # button.connect("toggled", self.on_right_to_left_toggled)
        # vbox.pack_start(button, True, True, 0)

        # self.timeout_id = GLib.timeout_add(5000, self.on_timeout, None)
        self.activity_mode = False

    def set_text(self, text):
        self.progressbar.set_text(text)
        self.progressbar.set_show_text(True)

    def reset_timer(self):
        new_value = 0.0
        self.progressbar.set_fraction(new_value)

    def on_activity_mode_toggled(self, button):
        self.activity_mode = button.get_active()
        if self.activity_mode:
            self.progressbar.pulse()
        else:
            self.progressbar.set_fraction(0.0)

    def on_right_to_left_toggled(self, button):
        value = button.get_active()
        self.progressbar.set_inverted(value)

    def update(self, fraction):
        new_value = self.progressbar.get_fraction() + fraction
        self.progressbar.set_fraction(new_value)
        if new_value >= 1.0:
            return False
        return True

    def get_complete(self):
        if self.progressbar.get_fraction() >= 1.0:
            return True
        return False

    def on_timeout(self, user_data=0.01):
        """
        Update value on the progress bar
        """
        if self.activity_mode:
            self.progressbar.pulse()
        else:
            new_value = self.progressbar.get_fraction() + user_data

            if new_value > 1:
                new_value = 0.0
                return False

            self.progressbar.set_fraction(new_value)
        return True
