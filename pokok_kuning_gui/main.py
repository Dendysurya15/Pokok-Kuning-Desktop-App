import sys
import os
import multiprocessing
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QCoreApplication

# ✅ Critical fix for PyInstaller executable - prevents multiple instances
# This MUST be at the top after imports
if __name__ == "__main__":
    # Enable multiprocessing freeze support for PyInstaller
    multiprocessing.freeze_support()

# Add the current directory to the path so we can import our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import our modules
from ui.main_window import MainWindow
from utils.config_manager import setup_database

def main():
    try:
        print("Starting Pokok Kuning Desktop App...")
        
        # Set application details
        QCoreApplication.setOrganizationName("Pokok Kuning")
        QCoreApplication.setApplicationName("Pokok Kuning Desktop App")
        
        # Create the application
        app = QApplication(sys.argv)
        
        # Setup database if it doesn't exist
        setup_database()
        
        # Create and show the main window
        print("Creating main window...")
        window = MainWindow()
        window.show()
        print("Main window displayed. Ready for user interaction.")
        
        # Execute the application
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Critical application error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
