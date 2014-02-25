# Copyright (C) 2010 - Jens Nyman (nymanjens.nj@gmail.com)
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.

from gi.repository import Gtk, GObject, Gedit
import re
import traceback

class TabsShortcutsPlugin(GObject.Object, Gedit.WindowActivatable):
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)
        self._instances = {}

    def do_activate(self):
        self._instances[self.window] = TabsShortcutsWindowHelper(self, self.window)

    def do_deactivate(self):
        self._instances[self.window].deactivate()
        del self._instances[self.window]

    def do_update_state(self):
        self._instances[self.window].update_ui()

class TabsShortcutsWindowHelper:

    def __init__(self, plugin, window):
        """Activate plugin."""
        self.window     = window
        self.notebook = self.get_notebook()
        callback = self._on_window_tab_added
        id_1 = window.connect("tab-added", callback)
        callback = self._on_window_tab_removed
        id_2 = window.connect("tab-removed", callback)
        window.tabs_shortcuts_id = (id_1, id_2)
        views = window.get_views()
        for view in views:
            self._connect_view(view, window)
    
    def update_ui(self):
        """Update the sensitivities of actions."""
        pass
        
    def get_notebook(self):
        return self.lookup_widget(self.window, 'GeditNotebook')[0]
    
    def lookup_widget(self, base, widget_name):
        widgets = []
        for widget in base.get_children():
            if widget.get_name() == widget_name:
                widgets.append(widget)
            if isinstance(widget, Gtk.Container):
                widgets += self.lookup_widget(widget, widget_name)
        return widgets

    #### key press event ####
    def _connect_view(self, view, window):
        """Connect to view's editing signals."""
        callback = self._on_view_key_press_event
        id = view.connect("key-press-event", callback, window)
        view.tabs_shortcuts_id = (id,)

    def _on_window_tab_added(self, window, tab):
        """Connect to signals of the document and view in tab."""
        name = self.__class__.__name__
        view = tab.get_view()
        if not hasattr(view, 'tabs_shortcuts_id'):
            self._connect_view(view, window)

    def _on_window_tab_removed(self, window, tab):
        pass
    
    def _on_view_key_press_event(self, view, event, window):
        control = 'GDK_CONTROL_MASK' in event.get_state().value_names
        alt = 'GDK_MOD1_MASK' in event.get_state().value_names
        shift = 'GDK_SHIFT_MASK' in event.get_state().value_names
        tab = event.keyval == 65289 or event.keyval == 65056
        pgdwn = event.keyval == 65366
        pgup = event.keyval == 65365
        
        if tab and control and not shift and not alt:
            self.next_page()
            return True
        if tab and control and shift and not alt:
            self.prev_page()
            return True
        if pgdwn and control and not shift and not alt:
            self.next_page()
            return True

        if pgup and control and not shift and not alt:
            self.prev_page()
            return True
        
    def next_page(self):
        self.next_prev_page(1)

    def prev_page(self):
        self.next_prev_page(-1)

    def next_prev_page(self, offset):
        currentPageNum = self.notebook.get_current_page()
        newPageNum = currentPageNum + offset
        numPages = self.notebook.get_n_pages()
        if newPageNum < 0:
            newPageNum = numPages - 1
        elif newPageNum >= numPages:
            newPageNum = 0
        self.notebook.set_current_page(newPageNum)
