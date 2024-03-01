from PyQt6.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton

# Only needed for access to command line arguments
import sys

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyHBR Clinical Code Group Editor")
        button = QPushButton("Press Me!")

        # Set the central widget of the Window.
        self.setCentralWidget(button)
        button.setCheckable(True)
        button.clicked.connect(self.the_button_was_clicked)

    def the_button_was_clicked(self):
        print("Clicked!")

def run_app() -> None:
    """Run the main codes editor application
    """

    # You need one (and only one) QApplication instance per application.
    # Pass in sys.argv to allow command line arguments for your app.
    # If you know you won't use command line arguments QApplication([]) works too.
    app = QApplication(sys.argv)

    # Create a Qt widget, which will be our window.
    window = MainWindow()
    window.show()

    # Start the event loop.
    app.exec()
