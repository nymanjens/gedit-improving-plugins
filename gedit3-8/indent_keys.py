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
        <menu name="EditMenu" action="Edit">
            <placeholder name="EditOps_6">
                <menuitem name="IndentKeys" action="IndentKeys"/>
                <menuitem name="UnindentKeys" action="UnindentKeys"/>
            </placeholder>
        </menu>
    </menubar>
</ui>
"""

class IndentKeysPlugin(GObject.Object, Gedit.WindowActivatable):
    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)
        self._instances = {}

    def do_activate(self):
        self._instances[self.window] = IndentKeysWindowHelper(self, self.window)

    def do_deactivate(self):
        self._instances[self.window].deactivate()
        del self._instances[self.window]

    def do_update_state(self):
        self._instances[self.window].update_ui()


class IndentKeysWindowHelper:
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
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()

        # Create a new action group
        self._action_group = Gtk.ActionGroup("IndentKeysPluginActions")
        self._action_group.add_actions([("IndentKeys", None, "_Indent",
                                         "<Control>t", "_Indent",
                                         self.indent),
                                         ("UnindentKeys", None, "_Unindent",
                                         "<Control><shift>t", "_Unindent",
                                         self.unindent)])

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
    def get_selected(self):
        """Return the index of the selected row."""

        view = self._window.get_active_view() 
        selection = view.get_selection()
        return str(selection)
        return selection.get_selected_rows()[1][0][0]
    
    # Menu activate handlers
    def indent(self, action):
        self.indent_or_unindent(action, False)
    def unindent(self, action):
        self.indent_or_unindent(action, True)
    def indent_or_unindent(self, action, unindent):
        document = self._window.get_active_document()
        if not document:
            return
        try:
            bounds = document.get_selection_bounds()
            if len(bounds) == 0:
                ### INDENT SELECTED LINE ###
                cursor = document.get_iter_at_mark(document.get_insert())
                self.indent_or_unindent_at_cursor(document, cursor.get_line(), unindent)
            else:
                ### INDENT SELECTED LINES ###
                # Note:
                #   Bug: when moving a line, the next line also gets selected
                #   Solution: subtract 1 char from end offset, but this would change manual selection,
                #             which can or cannot be desired
                #if bounds[1].get_offset() != document.get_iter_at_mark(document.get_insert()).get_offset():
                bounds[1].set_offset(bounds[1].get_offset() - 1);
                
                cursor = bounds[0].copy()
                start_ln_index = bounds[0].get_line()
                end_ln_index = bounds[1].get_line()
                
                for line_index in range(start_ln_index, end_ln_index + 1):
                    self.indent_or_unindent_at_cursor(document, line_index, unindent)
        except:
            err = "Exception\n"
            err += traceback.format_exc()
            document.set_text(err)
    
    def indent_or_unindent_at_cursor(self, document, line_index, unindent):
        # get cursor
        cursor = document.get_iter_at_mark(document.get_insert())
        cursor.set_line(line_index)
        # get tab code
        view = self._window.get_active_view() 
        tab_width = view.get_tab_width()
        tab_spaces = view.get_insert_spaces_instead_of_tabs()
        tab_code = ""
        if tab_spaces:
            for x in range(tab_width):
                tab_code += " "
        else:
            tab_code = "\t"
        # get cursor at start
        if not cursor.starts_line():
            cursor.set_line_offset(0)
        # get line
        end = cursor.copy()
        if not end.ends_line():
            end.forward_to_line_end()
        line = document.get_text(cursor, end, False)
        index = 0
        if unindent:
            # calculate removelen
            if index < len(line) and line[index] == "\t":
                removelen = 1
            else:
                removelen = 0
                for x in range(tab_width):
                    if index + removelen < len(line) and line[index + removelen] == ' ':
                        removelen += 1
                
            # remove indent
            cursor.set_line_offset(index)
            end = cursor.copy()
            end.set_line_offset(index + removelen)
            document.delete(cursor, end)
        else:
            # add indent
            cursor.get_buffer().insert(cursor, tab_code)
        
        ######## check if this is a list ########
        if not unindent or removelen:
             # constants
             list_bullets = ['- ', '+ ', '> ']
             ignore_whitespace = '\t '
             # get cursor
             cursor = document.get_iter_at_mark(document.get_insert())
             cursor.set_line(line_index)
             # get line at cursor
             line_start = cursor.copy()
             line_start.set_line_offset(0)
             line_end = cursor.copy()
             if not cursor.ends_line():
                 line_end.forward_to_line_end()
             line = document.get_text(line_start, line_end, False)
             # get whitespace in front of line
             whitespace_pos = 0
             whitespace = ""
             while len(line) > whitespace_pos and line[whitespace_pos] in ignore_whitespace:
                 whitespace += line[whitespace_pos]
                 whitespace_pos += 1
             
             # check all bullets
             for bullet_index in range(len(list_bullets)):
                 bullet = list_bullets[bullet_index]
                 if len(line) >= whitespace_pos + len(bullet):
                     if line[whitespace_pos:whitespace_pos + len(bullet)] == bullet:
                         if unindent:
                             newbullet_index = bullet_index - 1
                         else:
                             newbullet_index = bullet_index + 1
                         # bullet cycling disabled
                         newbullet = list_bullets[newbullet_index % len(list_bullets)]
                         # replace bullet
                         left = cursor.copy()
                         left.set_line_offset(whitespace_pos)
                         right = cursor.copy()
                         right.set_line_offset(whitespace_pos + len(bullet))
                         document.delete(left, right)
                         # renew cursor
                         cursor = document.get_iter_at_mark(document.get_insert())
                         cursor.set_line(line_index)
                         cursor.set_line_offset(whitespace_pos)
                         cursor.get_buffer().insert(cursor, newbullet)
                         break
