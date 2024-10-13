import sys
import threading
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QLineEdit, QPushButton, QMessageBox, QDialog, QFormLayout, QSpinBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QMouseEvent
from SIX_SERVER_READER import PotentiostatReader
import AMUZA_Master

# Global variables
t_buffer = 65
t_sampling = 91
connection = None  # This will be initialized after the user clicks 'Connect'
selected_wells = set()  # Set to store wells selected with click-and-drag (used for RUNPLATE)
ctrl_selected_wells = set()  # Set to store wells selected with Ctrl+Click (used for MOVE)

class WellLabel(QLabel):
    """Custom QLabel for well plate cells that supports click-and-drag and Ctrl+Click selection."""
    def __init__(self, well_id):
        super().__init__(well_id)
        self.well_id = well_id
        self.setFixedSize(50, 50)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: white; border: 1px solid black;")
        self.selected = False
        self.ctrl_selected = False

    def select(self):
        """Mark this cell as selected and change its color."""
        self.selected = True
        self.setStyleSheet("background-color: lightblue; border: 1px solid black;")

    def deselect(self):
        """Mark this cell as deselected and change its color."""
        self.selected = False
        self.setStyleSheet("background-color: white; border: 1px solid black;")

    def ctrl_select(self):
        """Mark this cell as Ctrl+selected for MOVE command."""
        self.ctrl_selected = True
        self.setStyleSheet("background-color: lightgreen; border: 1px solid black;")

    def ctrl_deselect(self):
        """Deselect this cell for MOVE command."""
        self.ctrl_selected = False
        self.setStyleSheet("background-color: white; border: 1px solid black;")


class SettingsDialog(QDialog):
    """Settings window to adjust t_sampling and t_buffer."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Settings")

        # Layout for the form
        layout = QFormLayout()

        # Spin boxes for t_sampling and t_buffer
        self.sampling_time_spinbox = QSpinBox()
        self.sampling_time_spinbox.setRange(1, 1000)
        self.sampling_time_spinbox.setValue(t_sampling)

        self.buffer_time_spinbox = QSpinBox()
        self.buffer_time_spinbox.setRange(1, 1000)
        self.buffer_time_spinbox.setValue(t_buffer)

        # Add to layout
        layout.addRow("Sampling Time (t_sampling):", self.sampling_time_spinbox)
        layout.addRow("Buffer Time (t_buffer):", self.buffer_time_spinbox)

        # Add Ok and Cancel buttons
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def accept(self):
        """Update t_sampling and t_buffer when OK is pressed."""
        global t_sampling, t_buffer
        t_sampling = self.sampling_time_spinbox.value()
        t_buffer = self.buffer_time_spinbox.value()
        super().accept()


class AMUZAGUI(QWidget):
    def __init__(self):
        super().__init__()

        # Set up the window
        self.setWindowTitle("AMUZA Controller")
        self.setGeometry(100, 100, 900, 400)

        # Main layout - Horizontal
        self.main_layout = QHBoxLayout(self)

        # Left side layout for commands
        self.command_layout = QVBoxLayout()

        # Right side layout for the well plate
        self.plate_layout = QGridLayout()

        # Filename label and input (aligned closer, no gap)
        filename_layout = QVBoxLayout()
        self.filename_label = QLabel("Enter Filename:")
        self.filename_entry = QLineEdit(self)
        filename_layout.addWidget(self.filename_label)
        filename_layout.addWidget(self.filename_entry)
        self.command_layout.addLayout(filename_layout)

        # Connect button
        self.connect_button = QPushButton("Connect to AMUZA", self)
        self.connect_button.clicked.connect(self.connect_to_amuza)
        self.command_layout.addWidget(self.connect_button)

        # Control buttons (initially disabled)
        self.start_datalogger_button = QPushButton("Start DataLogger", self)
        self.start_datalogger_button.setEnabled(False)
        self.start_datalogger_button.clicked.connect(self.start_datalogger)
        self.command_layout.addWidget(self.start_datalogger_button)

        self.insert_button = QPushButton("INSERT", self)
        self.insert_button.setEnabled(False)
        self.insert_button.clicked.connect(self.on_insert)
        self.command_layout.addWidget(self.insert_button)

        self.eject_button = QPushButton("EJECT", self)
        self.eject_button.setEnabled(False)
        self.eject_button.clicked.connect(self.on_eject)
        self.command_layout.addWidget(self.eject_button)

        self.runplate_button = QPushButton("RUNPLATE", self)
        self.runplate_button.setEnabled(False)
        self.runplate_button.clicked.connect(self.on_runplate)
        self.command_layout.addWidget(self.runplate_button)

        self.move_button = QPushButton("MOVE", self)
        self.move_button.setEnabled(False)
        self.move_button.clicked.connect(self.on_move)
        self.command_layout.addWidget(self.move_button)

        # Settings button
        self.settings_button = QPushButton("Settings", self)
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.command_layout.addWidget(self.settings_button)

        # Add the command layout to the main layout (on the left side)
        self.main_layout.addLayout(self.command_layout)

        # Well Plate layout (8x12 grid of labels, clickable)
        self.well_labels = {}
        self.start_row, self.start_col = None, None  # To track drag selection
        self.is_dragging = False

        self.setup_well_plate()

        # Add the well plate layout to the main layout (on the right side)
        self.main_layout.addLayout(self.plate_layout)

        # Set the layout for the QWidget
        self.setLayout(self.main_layout)

    def setup_well_plate(self):
        """Create a grid of 8x12 QLabel items representing the well plate."""
        rows = "ABCDEFGH"
        columns = range(1, 13)

        # Add clear button to the top left corner of the plate
        clear_button = QPushButton("Clear", self)
        clear_button.clicked.connect(self.clear_plate_selection)
        self.plate_layout.addWidget(clear_button, 0, 0, 1, 2)  # Spanning 2 columns

        for i, row in enumerate(rows):
            for j, col in enumerate(columns):
                well_id = f"{row}{col}"
                label = WellLabel(well_id)
                self.well_labels[(i, j)] = label
                self.plate_layout.addWidget(label, i + 1, j)  # Add one to row to account for Clear button

    def clear_plate_selection(self):
        """Clear all selected wells (both drag and Ctrl+Click selections)."""
        for label in self.well_labels.values():
            label.deselect()
            label.ctrl_deselect()
        selected_wells.clear()
        ctrl_selected_wells.clear()

    def open_settings_dialog(self):
        """Open the settings dialog to adjust t_sampling and t_buffer."""
        dialog = SettingsDialog()
        dialog.exec_()  # Wait for the dialog to be closed

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press event to start a selection or toggle a single well."""
        if event.button() == Qt.LeftButton:
            # Check if Ctrl key is pressed for Ctrl+Click functionality
            if event.modifiers() & Qt.ControlModifier:
                for (i, j), label in self.well_labels.items():
                    if label.geometry().contains(self.mapFromGlobal(event.globalPos())):
                        self.toggle_ctrl_well(i, j)  # Ctrl+Click to toggle single well
                        break
            else:
                # Start regular drag selection
                for (i, j), label in self.well_labels.items():
                    if label.geometry().contains(self.mapFromGlobal(event.globalPos())):
                        self.start_row, self.start_col = i, j
                        self.is_dragging = True
                        self.update_selection(i, j)
                        break

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move event to update the selection during drag."""
        if self.is_dragging:
            pos = event.pos()
            for (i, j), label in self.well_labels.items():
                if label.geometry().contains(self.mapFromGlobal(event.globalPos())):
                    self.update_selection(i, j)
                    break

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release event to finish the selection."""
        if self.is_dragging:
            self.is_dragging = False

    def update_selection(self, end_row, end_col):
        """Update the selection from the start position to the current cursor position."""
        min_row, max_row = min(self.start_row, end_row), max(self.start_row, end_row)
        min_col, max_col = min(self.start_col, end_col), max(self.start_col, end_col)

        # Deselect all wells first
        for label in self.well_labels.values():
            label.deselect()

        # Select wells in the dragged range
        for i in range(min_row, max_row + 1):
            for j in range(min_col, max_col + 1):
                self.well_labels[(i, j)].select()
                selected_wells.add(self.well_labels[(i, j)].well_id)

    def toggle_ctrl_well(self, row, col):
        """Toggle the well selection for the MOVE command (Ctrl+Click functionality)."""
        label = self.well_labels[(row, col)]
        well_id = label.well_id
        if well_id in ctrl_selected_wells:
            ctrl_selected_wells.remove(well_id)
            label.ctrl_deselect()
        else:
            ctrl_selected_wells.add(well_id)
            label.ctrl_select()

    def connect_to_amuza(self):
        """Connect to the AMUZA system."""
        global connection
        try:
            connection = AMUZA_Master.AmuzaConnection(True)
            connection.connect()
            QMessageBox.information(self, "Info", "Connected to AMUZA successfully!")
            self.enable_control_buttons()  # Enable other options after connection
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to connect to AMUZA: {str(e)}")
            connection = None

    def enable_control_buttons(self):
        """Enable the control buttons after successful connection."""
        self.start_datalogger_button.setEnabled(True)
        self.insert_button.setEnabled(True)
        self.eject_button.setEnabled(True)
        self.runplate_button.setEnabled(True)
        self.move_button.setEnabled(True)

    def on_insert(self):
        self.run_command("INSERT")

    def on_eject(self):
        self.run_command("EJECT")

    def on_runplate(self):
        self.run_command("RUNPLATE")

    def on_move(self):
        """Run the MOVE command using the Ctrl+Click selected wells."""
        self.run_command("MOVE", use_ctrl_selection=True)

    def run_command(self, command, use_ctrl_selection=False):
        """Execute the given command with the AMUZA system."""
        global connection
        method = []
        if connection is None:
            QMessageBox.critical(self, "Error", "Please connect to AMUZA first!")
            return

        if command == "RUNPLATE":
            connection.AdjustTemp(6)  # Chill the plate temp
            if not selected_wells:
                QMessageBox.critical(self, "Error", "No wells selected. Please select wells from the layout.")
                return
            locations = list(selected_wells)  # Convert set to list
            locations = connection.well_mapping(locations)
            for loc in locations:
                method.append(AMUZA_Master.Sequence([AMUZA_Master.Method([loc], t_sampling)]))
            self.Control_Move(method, [t_sampling])

        elif command == "MOVE":
            connection.AdjustTemp(6)
            wells_to_move = ctrl_selected_wells if use_ctrl_selection else selected_wells
            if not wells_to_move:
                QMessageBox.critical(self, "Error", "No wells selected for MOVE. Please Ctrl+Click wells to select.")
                return
            locations = list(wells_to_move)  # Convert set to list
            locations = connection.well_mapping(locations)
            for i in range(len(locations)):
                loc = locations[i]
                method.append(AMUZA_Master.Sequence([AMUZA_Master.Method([loc], t_sampling)]))
            self.Control_Move(method, [t_sampling])

        elif command == "EJECT":
            connection.Eject()

        elif command == "INSERT":
            connection.Insert()

    def Control_Move(self, method, duration):
        """Simulate movement of the AMUZA system."""
        for i in range(0, len(method)):
            time.sleep(t_buffer)
            connection.Move(method[i])
            delay = 1
            time.sleep(duration[0] + 9 + delay)

    def start_datalogger(self):
        """Start the data logger in a separate thread."""
        filename = self.filename_entry.text() + ".txt"
        threading.Thread(target=self.run_datalogger, args=(filename,), daemon=True).start()

    def run_datalogger(self, filename):
        """Run the data logger and log data."""
        path = r'/home/pi/Documents/Medium-Analysis-Automation/Data_Collected/'
        file_path = path + filename
        COM_PORT = '/dev/ttyUSB0'
        BAUD = 9600
        TIMEOUT = 0.5
        DataLogger = PotentiostatReader(com_port=COM_PORT, baud_rate=9600, timeout=TIMEOUT, output_filename=file_path)
        while True:
            data_list = DataLogger.run()

    def resizeEvent(self, event):
        """Lock the aspect ratio of the window."""
        width = event.size().width()
        height = event.size().height()

        aspect_ratio = 9 / 4  # Adjust aspect ratio (900:400 in this case)

        new_height = int(width / aspect_ratio)

        # Resize the window to maintain the aspect ratio
        self.resize(QSize(width, new_height))

        # Call the base class implementation
        super().resizeEvent(event)


# Start the application
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AMUZAGUI()
    window.show()
    sys.exit(app.exec_())

       
    