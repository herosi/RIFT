import idaapi
try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError:
    from PySide6 import QtCore, QtGui, QtWidgets


class RIFTFuncWindow(idaapi.PluginForm):

    def __init__(self):
        super().__init__()
        self.table = None
        self.parent = None
        self.header = None

    def OnCreate(self, form):
        print("Initiating FuncWindow ..")
        self.parent = self.FormToPyQtWidget(form)
        self.PopulateForm()
        print("Populating FuncWindow is done!")
    
    def PopulateForm(self):

        layout = QtWidgets.QVBoxLayout()
        # table 
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Address", "Name", "Ratio", "Description"])
        self.table.setRowCount(0)
        self.header = self.table.horizontalHeader()
        self.header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        layout.addWidget(self.table)
        # make our created layout the dialogs layout
        self.parent.setLayout(layout)

    def get_row_color(self, ratio):
        color = QtGui.QColor("red")
        if ratio >= 0.85:
            color = QtGui.QColor("green")
        elif ratio < 0.85 and ratio >= 0.7:
            color = QtGui.QColor("orange")
        elif ratio < 0.7 and ratio >= 0.55:
            color = QtGui.QColor("darkorange")
        return color

    def OnClose(self, form):
        pass

    def reset_rows(self):
        print("Reseting rows ..")
        self.table.setRowCount(0)

    def update_content(self, addr, hits):
        self.reset_rows()
        addr = hex(addr)
        print("Updating table ..")
        for index, hit in hits.iterrows():
            row_position = self.table.rowCount()
            row_color = self.get_row_color(hit["ratio"])
            self.table.insertRow(row_position)

            name = hit["name2"]
            ratio = str(hit["ratio"])
            reason = hit["description"]

            self.table.setItem(row_position, 0, QtWidgets.QTableWidgetItem(addr))
            self.table.setItem(row_position, 1, QtWidgets.QTableWidgetItem(name))
            self.table.setItem(row_position, 2, QtWidgets.QTableWidgetItem(ratio))
            self.table.setItem(row_position, 3, QtWidgets.QTableWidgetItem(reason))
            for j in range(self.table.columnCount()):
                self.table.item(row_position, j).setBackground(row_color)
