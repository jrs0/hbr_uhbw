import sys
from PyQt6.QtWidgets import (
    QCheckBox, QFileDialog, QMainWindow, QApplication,
    QLabel, QMessageBox, QToolBar, QStatusBar
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QSize, Qt, pyqtSlot
from pathlib import Path

from pyhbr import clinical_codes

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Codes Editor")

        self.toolbar = QToolBar("Main toolbar")
        self.addToolBar(self.toolbar)

        width = 500
        height = 500
        
        # setting the minimum size 
        self.setMinimumSize(width, height) 
        
        # If no file is open, this field is None. If a new file is created,
        # it will be either "new_diagnosis_groups.yaml" or "new_procedure_groups.yaml".
        # If the user clicks save as, the name can be changed.
        self.current_file = None

        # This stores the currently-open clinical code tree
        self.codes_tree = None
        
        self.setStatusBar(QStatusBar(self))
        self.update_all()
        
    def update_all(self, busy=False):
        self.update_toolbar()
        self.update_body(busy)
        
    def update_body(self, busy):

        if busy:
            label = QLabel("Please wait...")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setCentralWidget(label)
        if self.current_file is None:
            label = QLabel("Open or create a file for storing groups of codes.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setCentralWidget(label)
        else:
            label = QLabel(f"{self.codes_tree}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setCentralWidget(label)
            
    def update_toolbar(self):

        self.toolbar.clear()
        
        if self.current_file is None:

            new_diagnosis_button = QAction(QIcon("bug.png"), "&New ICD-10", self)
            new_diagnosis_button.setStatusTip("Create a blank file for ICD-10 code groups")
            new_diagnosis_button.triggered.connect(self.new_diagnosis_codes_file)
            self.toolbar.addAction(new_diagnosis_button)
            
            new_procedure_button = QAction(QIcon("bug.png"), "&New OPCS-4", self)
            new_procedure_button.setStatusTip("Create a blank file for OPCS-4 code groups")
            new_procedure_button.triggered.connect(self.new_procedure_codes_file)
            self.toolbar.addAction(new_procedure_button)
            
            open_button = QAction(QIcon("bug.png"), "&Open", self)
            open_button.setStatusTip("Open a diagnosis or procedure codes file")
            open_button.triggered.connect(self.open_dialog)
            self.toolbar.addAction(open_button)
                        
        else:

            self.setWindowTitle(f"Codes Editor: {self.current_file.name}")
            
            save_button = QAction(QIcon("bug.png"), "&Save", self)
            save_button.setStatusTip("Save the currently open diagnosis/procedure codes file")
            save_button.triggered.connect(self.save_file)
            self.toolbar.addAction(save_button)
            
            save_as_button = QAction(QIcon("bug.png"), "&Save As", self)
            save_as_button.setStatusTip("Save the currently open codes file under a different name")
            save_as_button.triggered.connect(self.save_file_as)
            self.toolbar.addAction(save_as_button)
            
            close_button = QAction(QIcon("bug.png"), "&Close", self)
            close_button.setStatusTip("Open the current file")
            close_button.triggered.connect(self.close_file)
            self.toolbar.addAction(close_button)
        
    def alert(self, title, message):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(title)
        dlg.setText(message)
        dlg.exec()

    def save_file(self):
        print(f"Saving file {self.current_file}")

    def save_file_as(self):
        print(f"Saving file as {self.current_file}")
        
    def new_diagnosis_codes_file(self):
        print("Creating blank diagnosis codes file")
        self.current_file = "new_diagnosis_groups.yaml"
        self.update_all()
        
    def new_procedure_codes_file(self):
        print("Creating blank procedure codes file")
        self.current_file = "new_procedure_groups.yaml"
        self.update_all()
        
    def open_file(self):
        self.current_file = "new_something_groups.yaml"
        self.update_all()

    @pyqtSlot()
    def open_dialog(self):
        file_name = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "${HOME}",
            "YAML Files (*.yaml);;",
        )

        current_file_name = file_name[0]
        if current_file_name == "":
            # User cancelled the dialog
            return

        try:
            self.setWindowTitle(f"Codes Editor: Opening File...")
            current_file_name = file_name[0]
            codes_tree = clinical_codes.load_from_file(current_file_name)
        except:
            self.alert("Failed to open file", "The file is not the correct format.")
            return

        # If you get here then the file was opened successfully
        self.current_file = Path(current_file_name)
        self.codes_tree = codes_tree
        self.update_all()
        
    def close_file(self):
        print(f"Closing current file {self.current_file}")
        self.current_file = None
        self.update_all()
        
        
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
