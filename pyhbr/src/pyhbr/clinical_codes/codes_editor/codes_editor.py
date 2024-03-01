from PyQt6.QtWidgets import QApplication, QWidget

# Only needed for access to command line arguments
import sys

def run_app() -> None:
    """Run the main codes editor application
    """

    # You need one (and only one) QApplication instance per application.
    # Pass in sys.argv to allow command line arguments for your app.
    # If you know you won't use command line arguments QApplication([]) works too.
    app = QApplication(sys.argv)

    # Create a Qt widget, which will be our window.
    window = QWidget()
    window.setWindowTitle("PyHBR Clinical Code Group Editor")
    window.show()

    # Start the event loop.
    app.exec()
