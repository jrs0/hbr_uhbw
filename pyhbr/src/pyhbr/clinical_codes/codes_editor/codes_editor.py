import sys
import os

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLineEdit, QMainWindow, QApplication,
    QLabel, QMessageBox, QPushButton, QToolBar, QStatusBar, QVBoxLayout, QWidget
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

    def main_codes_editor(self):

        self.codes_tree.groups

        layout = QVBoxLayout()

        # Page title
        title = QLabel("Edit Code Groups")
        font = title.font()
        font.setPointSize(30)
        title.setFont(font)
        layout.addWidget(title)

        # Add description
        description = QLabel("Use the groups selector to pick a group, and then use the checkboxes to include or exclude categories or codes from the group. When you are finished, save the resulting groups to a file.")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        self.search_label = QLabel("Search")
        self.search_bar = QLineEdit()
        self.search_bar.setMaxLength(10)
        self.search_bar.setPlaceholderText("Search for codes...")
        self.search_bar.returnPressed.connect(self.search_bar_return_pressed)
        self.search_bar.selectionChanged.connect(self.search_bar_selection_changed)
        self.search_bar.textChanged.connect(self.search_bar_text_changed)
        self.search_bar.textEdited.connect(self.search_bar_text_edited)
        self.search_layout = QHBoxLayout()
        self.search_layout.addWidget(self.search_label)
        self.search_layout.addWidget(self.search_bar)
        layout.addLayout(self.search_layout)

        self.group_label= QLabel("Group")
        self.group_picker = QComboBox()
        self.group_picker.addItems(self.codes_tree.groups)
        self.group_picker.currentTextChanged.connect(self.code_group_changed)
        self.add_new_group = QPushButton("Add New Group")
        self.change_group_name = QPushButton("Change Group Name")
        self.delete_group = QPushButton("Delete Group")
        self.group_layout = QHBoxLayout()
        self.group_layout.addWidget(self.group_label)
        self.group_layout.addWidget(self.group_picker)
        self.group_layout.addWidget(self.add_new_group)
        self.group_layout.addWidget(self.change_group_name)
        self.group_layout.addWidget(self.delete_group)
        layout.addLayout(self.group_layout)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        
    def code_group_changed(self, new_group):
        print(f"Coded group changed to {new_group}")
    
    def update_body(self, busy):

        if busy:
            label = QLabel("Please wait...")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setCentralWidget(label)
        elif self.current_file is None:
            label = QLabel("Open or create a file for storing groups of codes.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setCentralWidget(label)
        else:
            self.main_codes_editor()

    def search_bar_return_pressed(self):
        print("Return pressed!")

    def search_bar_selection_changed(self):
        pass

    def search_bar_text_changed(self, s):
        print("Text changed...")
        print(s)

    def search_bar_text_edited(self, s):
        print("Text edited...")
        print(s)
        
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
        self.setWindowTitle(f"Codes Editor: Saving {self.current_file.name}...")
        clinical_codes.save_to_file(self.codes_tree, str(self.current_file))
        self.setWindowTitle(f"Codes Editor: {self.current_file.name}")
        
    def save_file_as(self):
        print(f"Opening saving file as dialog")

        file_name = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            str(self.current_file),
            "YAML Files (*.yaml);;",
        )
        
        current_file = file_name[0]
        if current_file == "":
            # User cancelled the dialog
            return

        try:
            self.setWindowTitle(f"Codes Editor: Saving File As...")
            clinical_codes.save_to_file(self.codes_tree, str(current_file))

        except:
            self.alert("Failed to save file",
                       f"Working file will remain {self.current_file.name}")
            self.setWindowTitle(f"Codes Editor: {self.current_file.name}...")
            return

        # If you get here then the file was opened successfully
        self.current_file = Path(current_file)
        self.update_all()

        
        
    def new_codes_file(self, diagnosis):

        if diagnosis:
            file_name = Path("new_diagnosis_groups.yaml")
            kind = "ICD-10"
            package_source = "icd10_blank.yaml"
        else:
            file_name = Path("new_procedure_groups.yaml")
            kind = "OPCS-10"
            package_source = "opcs4_blank.yaml"

        print(f"Creating blank {kind} codes file")

            
        # Create the default path to the new file
        working_dir = Path(os.getcwd())
        self.current_file = working_dir / file_name

        print(f"Loading new file with save-path {self.current_file}")
        self.setWindowTitle(f"Codes Editor: Opening blank {kind} file...")
        
        # Load the blank codes tree
        self.codes_tree = clinical_codes.load_from_package(package_source)
        self.update_all()
    
    def new_procedure_codes_file(self):
        self.new_codes_file(False)
        
    def new_diagnosis_codes_file(self):
        self.new_codes_file(True)
    
        
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

        current_file = file_name[0]
        if current_file == "":
            # User cancelled the dialog
            return

        try:
            self.setWindowTitle(f"Codes Editor: Opening File...")
            codes_tree = clinical_codes.load_from_file(current_file)
        except:
            self.alert("Failed to open file", "The file is not the correct format.")
            return

        # If you get here then the file was opened successfully
        self.current_file = Path(current_file)
        self.codes_tree = codes_tree
        self.update_all()
        
    def close_file(self):
        print(f"Closing current file {self.current_file}")

        # Check if the user wants to save?
        
        self.current_file = None
        self.codes_tree = None

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
