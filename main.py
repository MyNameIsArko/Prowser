import gi
gi.require_version("Gtk", "3.0")
gi.require_version('WebKit2', '4.0')
from gi.repository import Gtk, WebKit2, Gdk
import json

bookmarks = {}

button_bookmarks = {}

# Add protocol when it's adress, otherwise add search engine
def fulfill_uri(uri):
    if uri[:4] != "http":
            if "." in uri:
                url = "https://" + uri
            else:
                url = "https://duckduckgo.com/?q=" + uri
    else:
        url = uri
    return url

# * Main Window Class
class WebWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Browser")
        self.set_size_request(1000, 1000)

        # Vertical box for page and bookmark tab
        view_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(view_box)

        self.bookmark_view = Gtk.Box()
        self.bookmark_view.set_size_request(0,40)
        view_box.pack_start(self.bookmark_view, False, False, 0)

        # Allow to scroll pages and add web window
        scrolled_window = Gtk.ScrolledWindow()
        self.webview = WebKit2.WebView()
        self.webview.connect("notify::estimated-load-progress", self.indicate_progress)
        scrolled_window.add(self.webview)
        view_box.pack_start(scrolled_window, True, True, 0)

        # Create top panel and add buttons
        top_bar = Gtk.HeaderBar()
        top_bar.set_show_close_button(True)
        self.set_titlebar(top_bar)

        # Url input
        self.url_entry = Gtk.Entry()
        self.url_entry.connect("activate", self.request_website)
        self.url_entry.set_placeholder_text("Website")
        self.url_entry.set_hexpand(True)
        top_bar.set_custom_title(self.url_entry)

        # Add button to go to previous page
        self.back_button = Gtk.Button()
        self.back_button.set_label("<")
        self.back_button.connect("clicked", self.back)
        self.back_button.set_sensitive(False)
        top_bar.pack_start(self.back_button)

        # Add button to go to next page
        self.forward_button = Gtk.Button()
        self.forward_button.set_label(">")
        self.forward_button.connect("clicked", self.forward)
        self.forward_button.set_sensitive(False)
        top_bar.pack_start(self.forward_button)

        # Add button to add website to bookmark
        self.bookmark_button = Gtk.Button()
        self.bookmark_button.set_label("B")
        self.bookmark_button.connect("clicked", self.bookmark)
        self.bookmark_button.set_sensitive(False)
        top_bar.pack_end(self.bookmark_button)
    
    # Show requested url
    def request_website(self, _widget):
        url = self.url_entry.get_text()
        url = fulfill_uri(url)
        self.webview.load_uri(WebKit2.uri_for_display(url))
        
    # Show how much of the website was loaded
    def indicate_progress(self, widget, *args):
        amount = widget.props.estimated_load_progress
        self.url_entry.set_progress_fraction(amount)
        if amount == 1.0:
            self.url_entry.set_progress_fraction(0)
            self.url_entry.set_text(self.webview.get_uri())
            # Allow for bookmarking page
            self.bookmark_button.set_sensitive(True)

            # If previous page is available, unlock button
            if self.webview.can_go_back():
                self.back_button.set_sensitive(True)
            else:
                self.back_button.set_sensitive(False)
            
            # If next page is available, unlock button
            if self.webview.can_go_forward():
                self.forward_button.set_sensitive(True)
            else:
                self.forward_button.set_sensitive(False)

    # Go to previous page
    def back(self, button):
        self.webview.go_back()
        self.url_entry.set_text(self.webview.get_uri())

    # Go to next page
    def forward(self, button):
        self.webview.go_forward()
        self.url_entry.set_text(self.webview.get_uri())

    # Bookmark page, set its name and adress
    def bookmark(self, button, is_changing = False):
        # Run dialog for configuring bookmark
        dialog = BookmarkDialog(self, button, is_changing)
        response = dialog.run()
        
        # Get entered name and url
        entry = dialog.entry_name.get_text()
        url = dialog.entry_url.get_text()

        # If user pressed "Set"
        if response == Gtk.ResponseType.OK:
            entry = dialog.entry_name.get_text()
            url = dialog.entry_url.get_text()
            # If bookmark already exists, rename button and replace bookmark
            if is_changing:
                bookmarks.pop(button.name, -1)
                button_bookmarks.pop(button.name, -1)
                bookmarks[entry] = url
                button_bookmarks[entry] = button
                button.set_label(entry)
                button.name = entry
            # If not, create new bookmark button and add to bookmarks
            else:
                bookmarks[entry] = url
                bt = BookmarkContainer(entry, url, self)
                bt.show()
                button_bookmarks[entry] = bt
                self.bookmark_view.pack_start(bt, False, False, 0)
        # If user pressed "Remove"
        elif response == Gtk.ResponseType.CANCEL:
            # If bookmark exists, remove it, else don't do anything
            try:
                bookmarks.pop(button.name, -1)
                bt = button_bookmarks[button.name]
                self.bookmark_view.remove(bt)
                button_bookmarks.pop(button.name, -1)
            except AttributeError:
                pass
        # Save bookmarks to file
        with open("bookmarks.json", "w") as file:
            json.dump(bookmarks, file)
            
        dialog.destroy()

# ! Not connected
class ErrorDialog(Gtk.Dialog):
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, title="Error", transient_for=parent, flags=0)
        self.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        label = Gtk.Label(label="Couldn't connect to the website")

        box = self.get_content_area()
        box.add(label)
        self.show_all()

# Dialog for creating/editing bookmarks
class BookmarkDialog(Gtk.Dialog):
    def __init__(self, parent, button, is_changing):
        Gtk.Dialog.__init__(self, title="Set Bookmark", transient_for=parent, flags=0)
        self.add_buttons("Remove", Gtk.ResponseType.CANCEL, "Set", Gtk.ResponseType.OK)
        self.set_size_request(300, 0)
        
        # Box for name and url labels
        box_label = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        label_name = Gtk.Label(label="Name:")
        box_label.pack_start(label_name, True, True, 0)

        label_url = Gtk.Label(label="Url:")
        box_label.pack_start(label_url, True, True, 0)

        # Box for name and url entries
        box_entry = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.entry_name = Gtk.Entry()
        # If editing bookmark, set name to previous one
        if is_changing:
            self.entry_name.set_text(button.name)
        box_entry.pack_start(self.entry_name, True, True, 0)

        self.entry_url = Gtk.Entry()
        self.entry_url.set_text(parent.webview.get_uri())
        box_entry.pack_start(self.entry_url, True, True, 0)

        # Box holding labels and entries
        all_box = Gtk.Box()
        all_box.pack_start(box_label, True, True, 0)
        all_box.pack_start(box_entry, True, True, 0)

        # Get dialog area
        box = self.get_content_area()
        box.add(all_box)
        self.show_all()

# Button containing bookmark
class BookmarkContainer(Gtk.Button):
    def __init__(self, name, url, parent):
        Gtk.Button.__init__(self, label=name)
        self.name = name
        self.url = url
        self.connect("event", self.pressed)
        self.parent = parent

    def pressed(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            # If right-clicked, edit bookmark
            if event.button.button == 3:
                self.parent.bookmark(self, is_changing = True)
            # If left-clicked, open bookmark website
            if event.button.button == 1:
                self.parent.url_entry.set_text(self.url)
                self.parent.request_website(self)


win = WebWindow()
win.connect("destroy", Gtk.main_quit)
win.show_all()

# Load bookmarks from file
try:
    with open("bookmarks.json", "r") as file:
        bookmarks = json.load(file)   
        for key in bookmarks:
            bt = BookmarkContainer(key, bookmarks[key], win)
            bt.show()
            button_bookmarks[key] = bt
            win.bookmark_view.pack_start(bt, False, False, 0)   
except FileNotFoundError:
    pass

Gtk.main()