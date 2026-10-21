"""PyInstaller entry point for the HeyClone desktop application.

Build a standalone Windows GUI executable from the project root:

    python -m PyInstaller --noconfirm --clean --onefile --windowed \
        --name HeyClone --paths . packaging/windows/heyclone_entry.py
"""

from heyclone.gui import launch_gui

if __name__ == "__main__":
    launch_gui()
