Gedit Improving Plugins
=====
These plugins effectively improve your Gedit experience and makes it a powerful editor.

Features
---
* **Indent Key Plugin:** Adds 2 shortcuts (ctrl-T and ctrl-shift-T) for indentation. Also auto-detects lists and changes the bullet.
* **Intelligent Text Completion:** Saves a lot of typing. For more information, see http://code.google.com/p/gedit-intelligent-text-completion/.
* **Line Tools Plugin:** Adds 3 shortcuts of which the duplicate shortcut (ctrl-B) is the most handy.
* **Open Terminal:** Adds a shortcut (ctrl-E) to open the terminal at the current location.
* **Tabs Shortcuts:** Adds shortcuts to switch between tabs like in Firefox
* **Word Completion:** Completes your words by already present words. Works like a charm and saves huge amounts of effort.

Installation
---
### Gedit 3.0-3.7 (Ubuntu 11.10 - 13.04)
1. Unpack the archive
1. Put the files inside `.local/share/gedit/plugins` in your home directory. (create it if it doesn't exist yet)
1. (Re)start Gedit.
1. Go to Edit->Preferences->Plugins and check the boxes:
    * Indent Key Plugin
    * Intelligent Text Completion
    * Line Tools Plugin
    * Open Terminal
    * Tabs Shortcuts
    * Word Completion

### Gedit 3.8 (Ubuntu 13.10 or higher)
1. Get the newest version from svn and put it into `.local/share/gedit/plugins`:

   ```bash
   mkdir -p ~/.local/share/gedit/plugins
   cd ~/.local/share/gedit/plugins
   git clone https://github.com/nymanjens/gedit-improving-plugins.git
   ```
1. (Re)start Gedit.
1. Go to Edit->Preferences->Plugins and check the boxes:
    * Indent Key Plugin
    * Intelligent Text Completion
    * Line Tools Plugin
    * Open Terminal
    * Tabs Shortcuts
