# Copyright (C) 2006-2008 Osmo Salomaa
# Edited by Jens Nyman <nymanjens.nj@gmail.com>
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
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""Complete words with the tab key.

This plugin provides a 'stupid' word completion plugin, one that is aware of
all words in all open documents, but knows nothing of any context or syntax.
This plugin can be used to speed up writing and to avoid spelling errors in
either regular text documents or in programming documents if no programming
language -aware completion is available.

Words are automatically scanned at regular intervals. Once you have typed a
word and the interval has passed, the word is available in the completion
system. A completion window listing possible completions is shown and updated
as you type. You can complete to the topmost word in the window with the Tab
key, or choose another completion with the arrow keys and complete with the Tab
key. The keybindinds are configurable only by editing the source code.
"""

from gi.repository import Gtk, GObject, Gedit
import pango
import re
import traceback
import os

#class CompletionWindow(Gtk.Window):
class CompletionWindow:

    """Window for displaying a list of words to complete to.

    This is a popup window merely to display words. This window is not meant
    to receive or handle input from the user, rather the various methods should
    be called to chang the list of words and which one of them is selected.
    """

    def __init__(self, parent):
        self.gtkwindow = Gtk.Window.new(Gtk.WindowType.POPUP)
        # Gtk.Window.__init__(self)
        # self.type = Gtk.WindowType.POPUP
        self._store = None
        self._view = None
        self.gtkwindow.set_transient_for(parent)
        self._init_view()
        self._init_containers()

    def _init_containers(self):
        """Initialize the frame and the scrolled window."""

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(*((Gtk.PolicyType.NEVER,) * 2))
        scroller.add(self._view)
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.OUT)
        frame.add(scroller)
        self.gtkwindow.add(frame)

    def _init_view(self):
        """Initialize the tree view listing the complete words."""

        self._store = Gtk.ListStore(GObject.TYPE_STRING)
        self._view = Gtk.TreeView(self._store)
        renderer = Gtk.CellRendererText()
        renderer.xpad = renderer.ypad = 6
        column = Gtk.TreeViewColumn("", renderer, text=0)
        self._view.append_column(column)
        self._view.set_enable_search(False)
        self._view.set_headers_visible(False)
        self._view.set_rules_hint(True)
        selection = self._view.get_selection()
        selection.set_mode(Gtk.SelectionMode.SINGLE)

    def get_selected(self):
        """Return the index of the selected row."""

        selection = self._view.get_selection()
        return selection.get_selected_rows()[1][0].get_indices()[0]
        #return selection.get_selected_rows()[1][0][0]

    def select_next(self):
        """Select the next complete word."""

        row = min(self.get_selected() + 1, len(self._store) - 1)
        selection = self._view.get_selection()
        selection.unselect_all()
        selection.select_path(row)
        self._view.scroll_to_cell(row)

    def select_previous(self):
        """Select the previous complete word."""

        row = max(self.get_selected() - 1, 0)
        selection = self.gtkwindow._view.get_selection()
        selection.unselect_all()
        selection.select_path(row)
        self._view.scroll_to_cell(row)

    def set_completions(self, completions):
        """Set the completions to display."""

        # 'Gtk.Window.resize' followed later by 'Gtk.TreeView.columns_autosize'
        # will allow the window to either grow or shrink to fit the new data.
        self.gtkwindow.resize(1, 1)
        self._store.clear()
        for word in completions:
            self._store.append((word,))
        self._view.columns_autosize()
        self._view.get_selection().select_path(0)

    def set_font_description(self, font_desc):
        """Set the font description used in the view."""
        pass
        #self._view.modify_font(font_desc)


class CompletionPlugin(GObject.Object, Gedit.WindowActivatable):
    """Complete words with the tab key.

    Instance variables are as follows. '_completion_windows' is a dictionary
    mapping 'Gedit.Windows' to 'CompletionWindows'.

    '_all_words' is a dictionary mapping documents to a frozen set containing
    all words in the document. '_favorite_words' is a dictionary mapping
    documents to a set of words that the user has completed to. Favorites are
    thus always document-specific and there are no degrees to favoritism. These
    favorites will be displayed at the top of the completion window. As
    '_all_words' and '_favorite_words' are both sets, the exact order in which
    the words are listed in the completion window is unpredictable.

    '_completions' is a list of the currently active complete words, shown in
    the completion window, that the user can complete to. Similarly '_remains'
    is a list of the untyped parts the _completions, i.e. the part that will be
    inserted when the user presses the Tab key. '_completions' and '_remains'
    always contain words for the gedit window, document and text view that has
    input focus.

    '_font_ascent' is the ascent of the font used in gedit's text view as
    reported by pango. It is needed to be able to properly place the completion
    window right below the caret regardless of the font and font size used.
    """

    window = GObject.property(type=Gedit.Window)

    # Unlike gedit itself, consider underscores alphanumeric characters
    # allowing completion of identifier names in many programming languages.
    _re_alpha = re.compile(r"\w+", re.UNICODE | re.MULTILINE)
    _re_non_alpha = re.compile(r"\W+", re.UNICODE | re.MULTILINE)

    # TODO: Are these sane defaults? Do we need a configuration dialog?
    _scan_frequency = 10000 # ms
    _max_completions_to_show = 6

    def __init__(self):
        GObject.Object.__init__(self)

        self._all_words = {}
        self._completion_windows = {}
        self._completions = []
        self._favorite_words = {}
        self._font_ascent = 0
        self._remains = []

    def _complete_current(self):
        """Complete the current word."""

        window = self.window
        doc = window.get_active_document()
        index = self._completion_windows[window].get_selected()
        doc.insert_at_cursor(self._remains[index])
        words = self._favorite_words.setdefault(doc, set(()))
        words.add(self._completions[index])
        self._terminate_completion()

    def _connect_document(self, doc):
        """Connect to document's 'loaded' signal."""

        callback = lambda doc, x, self: self._scan_document(doc)
        handler_id = doc.connect("loaded", callback, self)
        doc.completion_plugin_id = (handler_id, )

    def _connect_view(self, view, window):
        """Connect to view's editing signals."""

        callback = lambda x, y, self: self._terminate_completion()
        id_1 = view.connect("focus-out-event", callback, self)
        callback = self._on_view_key_press_event
        id_2 = view.connect("key-press-event", callback, window)
        view.completion_plugin_id = (id_1, id_2)

    def _display_completions(self, view, event):
        """Find completions and display them in the completion window."""

        doc = view.get_buffer()
        insert = doc.get_iter_at_mark(doc.get_insert())
        start = insert.copy()
        while start.backward_char():
            char = unicode(start.get_char())
            if not self._re_alpha.match(char):
                start.forward_char()
                break
        incomplete = unicode(doc.get_text(start, insert, False))
        incomplete += unicode(event.string)
        if incomplete.isdigit():
            # Usually completing numbers is not a good idea.
            return self._terminate_completion()
        self._find_completions(doc, incomplete)
        if not self._completions:
            return self._terminate_completion()
        self._show_completion_window(view, insert)

    def _find_completions(self, doc, incomplete):
        """Find completions for incomplete word and save them."""

        self._completions = []
        self._remains = []
        favorites = self._favorite_words.get(doc, ())
        _all_words = set(())
        for words in self._all_words.itervalues():
            _all_words.update(words)
        limit = self._max_completions_to_show
        for sequence in (favorites, _all_words):
            for word in sequence:
                if not word.startswith(incomplete): continue
                if word == incomplete: continue
                if word in self._completions: continue
                self._completions.append(word)
                self._remains.append(word[len(incomplete):])
                if len(self._remains) >= limit: break

    def _on_view_key_press_event(self, view, event, window):
        """Manage actions for completions and the completion window."""

        control = 'GDK_CONTROL_MASK' in event.get_state().value_names
        alt = 'GDK_MOD1_MASK' in event.get_state().value_names
        shift = 'GDK_SHIFT_MASK' in event.get_state().value_names
        tab = event.keyval == 65289 or event.keyval == 65056
        if control:
            return self._terminate_completion()
        if alt:
            return self._terminate_completion()
        if tab and self._remains:
            return not self._complete_current()
        completion_window = self._completion_windows[window]
        if (event.keyval == 65362) and self._remains: # 65362 = up
            return not completion_window.select_previous()
        if (event.keyval == 65364) and self._remains: # 65364 = down
            return not completion_window.select_next()
        string = unicode(event.string)
        if len(string) != 1:
            # Do not suggest completions after pasting text.
            return self._terminate_completion()
        if self._re_alpha.match(string) is None:
            return self._terminate_completion()
        doc = view.get_buffer()
        insert = doc.get_iter_at_mark(doc.get_insert())
        if self._re_alpha.match(unicode(insert.get_char())):
            # Do not suggest completions in the middle of a word.
            return self._terminate_completion()
        return self._display_completions(view, event)

    def _on_window_tab_added(self, window, tab):
        """Connect to signals of the document and view in tab."""

        self._update_fonts(tab.get_view())
        doc = tab.get_document()
        handler_id = getattr(doc, 'completion_plugin_id', None)
        if handler_id is None:
            self._connect_document(doc)
        view = tab.get_view()
        handler_id = getattr(view, 'completion_plugin_id', None)
        if handler_id is None:
            self._connect_view(view, window)

    def _on_window_tab_removed(self, window, tab):
        """Remove closed document's word and favorite sets."""

        doc = tab.get_document()
        self._all_words.pop(doc, None)
        self._favorite_words.pop(doc, None)

    def _scan_active_document(self, window):
        """Scan all the words in the active document in window."""

        # Return False to not scan again.
        if window is None: return False
        doc = window.get_active_document()
        if doc is not None:
            self._scan_document(doc)
        return True

    def _scan_document(self, doc):
        """Scan and save all words in document."""

        # add filename to words
        path = doc.get_uri_for_display()
        fname = os.path.basename(path)
        fname_without_ext = os.path.splitext(fname)[0]
        fname_words = [fname_without_ext, fname]

        text = unicode(doc.get_text(doc.get_bounds()[0], doc.get_bounds()[1], False))
        self._all_words[doc] = frozenset(self._re_non_alpha.split(text) + fname_words)


    def _show_completion_window(self, view, itr):
        """Show the completion window below the caret."""

        text_window = Gtk.TextWindowType.WIDGET
        rect = view.get_iter_location(itr)
        x, y = view.buffer_to_window_coords(text_window, rect.x, rect.y)
        window = self.window
        x, y = view.translate_coordinates(window, x, y)
        x += window.get_position()[0] + self._font_ascent
        # Use 24 pixels as an estimate height for window title bar.
        # TODO: There must be a better way than a hardcoded pixel value.
        y += window.get_position()[1] + 24 + (2 * self._font_ascent)
        completion_window = self._completion_windows[window]
        completion_window.set_completions(self._completions)
        completion_window.gtkwindow.move(int(x), int(y))
        completion_window.gtkwindow.show_all()

    def _terminate_completion(self):
        """Hide the completion window and cancel completions."""

        window = self.window
        self._completion_windows[window].gtkwindow.hide()
        self._completions = []
        self._remains = []

    def _update_fonts(self, view):
        """Update font descriptions and ascent metrics."""
        return # disable this method because it doesn't work anymore in gedit 3.6.2

        context = view.get_pango_context()
        font_desc = context.get_font_description()
        if self._font_ascent == 0:
            # Acquiring pango metrics is a bit slow,
            # so do this only when absolutely needed.
            metrics = context.get_metrics(font_desc, None)
            self._font_ascent = metrics.get_ascent() / pango.SCALE
        for completion_window in self._completion_windows.itervalues():
            completion_window.set_font_description(font_desc)

    def do_activate(self):
        """Activate plugin."""
        window = self.window
        callback = self._on_window_tab_added
        id_1 = window.connect("tab-added", callback)
        callback = self._on_window_tab_removed
        id_2 = window.connect("tab-removed", callback)
        window.completion_plugin_id = (id_1, id_2)
        for doc in window.get_documents():
            self._connect_document(doc)
            self._scan_document(doc)
        views = window.get_views()
        for view in views:
            self._connect_view(view, window)
        if views: self._update_fonts(views[0])
        self._completion_windows[window] = CompletionWindow(window)
        # Scan the active document in window if it has input focus
        # for new words at constant intervals.
        def scan(self, window):
            if not window.is_active(): return True
            return self._scan_active_document(window)
        freq = self._scan_frequency
        priority = GObject.PRIORITY_LOW
        GObject.timeout_add(freq, scan, self, window, priority=priority)

    def do_deactivate(self):
        """Deactivate plugin."""

        window = self.window
        widgets = [window]
        widgets.extend(window.get_views())
        widgets.extend(window.get_documents())
        for widget in widgets:
            for handler_id in getattr(widget, 'completion_plugin_id', []):
                widget.disconnect(handler_id)
            widget.completion_plugin_id = None
        self._terminate_completion()
        self._completion_windows.pop(window)
        for doc in window.get_documents():
            self._all_words.pop(doc, None)
            self._favorite_words.pop(doc, None)
