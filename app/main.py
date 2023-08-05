import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QLineEdit, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt
import sqlite3

        
class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        
        self.query = QLineEdit()
        self.query.setPlaceholderText("Search")
        self.query.textChanged.connect(self.search)

        container = QWidget()
        containerLayout = QVBoxLayout()
        container.setLayout(containerLayout)

        # select * from the table containing all players where the position is goalie
        conn = sqlite3.connect("nhl_players.db")
        curr = conn.cursor()


        selection = {
            "playerId": "Player ID",
            "firstName": "First Name",
            "lastName": "Last Name",
            "shootsCatches": "Catches"
        }
        queryable = ", ".join([x for x in selection.keys()])

        curr.execute(f"SELECT {queryable} FROM players WHERE position='Goalie'")
        rows = curr.fetchall()
        data = rows

        self.table = QTableWidget()
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(len(selection))

        self.row_widgets = []
        
        # This seems like a bad way of doing things but let's brute force
        # fill the table with all of the Goalie information
        for r in range(len(rows)):
            for c in range(len(selection)):
                item = QTableWidgetItem(str(rows[r][c]))
                self.row_widgets.append(item)
                self.table.setItem(r, c, item)

        # Fill in the main widget information for the display
        containerLayout.addWidget(self.query)
        containerLayout.addWidget(self.table)
        
        self.setCentralWidget(container)

    
    def search(self, s):
        """
        Display only the rows of data where the user entered text is found. When
        empty all rows in the table should appear.
        """
        if s:
            for i in range(self.table.rowCount()):
                self.table.hideRow(i)
        
        items = self.table.findItems(s, Qt.MatchContains)
        if items:
            for item in items:
                self.table.showRow(item.row())

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.resize(400, 800)
    window.show()
    app.exec_()
