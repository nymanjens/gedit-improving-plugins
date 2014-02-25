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

# UI Manager XML
ACTIONS_UI = """
<ui>
    <menubar name="MenuBar">
        <menu name="FileMenu" action="File">
            <placeholder name="FileOps_5">
                <menuitem name="OpenTerminal" action="OpenTerminal"/>
                <menuitem name="OpenTerminalSpecial" action="OpenTerminalSpecial"/>
            </placeholder>
        </menu>
    </menubar>
</ui>
"""

class OpenTerminalPlugin(GObject.Object, Gedit.WindowActivatable):
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)
        self._instances = {}

    def do_activate(self):
        self._instances[self.window] = OpenTerminalWindowHelper(self, self.window)

    def do_deactivate(self):
        self._instances[self.window].deactivate()
        del self._instances[self.window]

    def do_update_state(self):
        self._instances[self.window].update_ui()



class OpenTerminalWindowHelper:
    def __init__(self, plugin, window):
        self._window = window
        self._plugin = plugin
        # Insert menu items
        self._insert_menu()

    def deactivate(self):
        # Remove any installed menu items
        self._remove_menu()
        self._window = None
        self._plugin = None
        self._action_group = None

    def _insert_menu(self):
        # actions
        actions = [
            (
                "OpenTerminal", # name
                None, # icon stock id
                "_Open Terminal", # label
                "<Control>e", # shortcut
                "_Open Terminal", # tooltip
                self.open_terminal # callback
            ),
            (
                "OpenTerminalSpecial", # name
                None, # icon stock id
                "Open Terminal Special", # label
                "<Control><Shift>e", # shortcut
                "Open Terminal Special", # tooltip
                self.open_terminal_special # callback
            ),
        ]

        # Create a new action group
        self._action_group = Gtk.ActionGroup(self.__class__.__name__)
        self._action_group.add_actions(actions)
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()
        # Insert the action group
        manager.insert_action_group(self._action_group, -1)
        # Merge the UI
        self._ui_id = manager.add_ui_from_string(ACTIONS_UI)

    def _remove_menu(self):
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()
        # Remove the ui
        manager.remove_ui(self._ui_id)
        # Remove the action group
        manager.remove_action_group(self._action_group)
        # Make sure the manager updates
        manager.ensure_update()

    def update_ui(self):
        self._action_group.set_sensitive(self._window.get_active_document() != None)

        
    ############ plugin core functions ############
    # Menu activate handlers
    def open_terminal(self, action):
        return self.open_terminal_special(action, False)

    def open_terminal_special(self, action, special=True):
        document = self._window.get_active_document()
        if not document:
            return
        try:
            import subprocess, sys, os
            
            # under_svn_control function
            def under_svn_control(path):
                return os.path.isdir(path + "/.svn")
            
            # get working directory
            directory = document.get_uri_for_display()
            directory = os.path.dirname(directory)
            if directory == '':
                directory = '~/'
            else:
                directory = os.path.realpath(directory)
            
            # we want the top svn directory
            if special:
                if under_svn_control(directory):
                    prev_dir = directory
                    while under_svn_control(directory):
                        prev_dir = directory
                        directory = directory + "/.."
                    directory = prev_dir
            
            # call terminal
            args = '--working-directory=%s' % directory
            subprocess.Popen(['gnome-terminal', args])
        except:
            err = "Exception\n"
            err += traceback.format_exc()
            document.set_text(err)
