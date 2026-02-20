pyinstaller --windowed main.py --icon=icon.ico --add-data "config.ini:." --add-data "target1.png:." --add-data "target2.png:."
xattr -dr com.apple.quarantine main.app