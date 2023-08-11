import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (
    QLineEdit,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QComboBox
)
from PyQt5.QtCore import Qt
import sqlite3
import pyqtgraph as pg


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()

        self.activePlayerId = None
        
        self.query = QLineEdit()
        self.query.setPlaceholderText("Search")
        self.query.textChanged.connect(self.search)

        # select * from the table containing all players where the position is goalie
        conn = sqlite3.connect("nhl.db")
        curr = conn.cursor()

        # rows that will be a part of the query and ultimately the display for
        # the player table
        playerSelection = {
            "playerId": "Player ID",
            "firstName": "First Name",
            "lastName": "Last Name",
            "shootsCatches": "Catches"
        }
        queryable = ", ".join([x for x in playerSelection.keys()])

        curr.execute(f"SELECT {queryable} FROM players")
        rows = curr.fetchall()
        data = rows

        self.playerTable = QTableWidget()
        self.playerTable.setRowCount(len(rows))
        self.playerTable.setColumnCount(len(playerSelection))

        self.rowWidgets = []
        
        # This seems like a bad way of doing things but let's brute force
        # fill the table with all of the Goalie information
        for r in range(len(rows)):
            for c in range(len(playerSelection)):
                item = QTableWidgetItem(str(rows[r][c]))
                self.rowWidgets.append(item)
                self.playerTable.setItem(r, c, item)

        # rows that will be a part of the query and ultimarely the display for
        # the event table
        self.eventSelection = {
            "eventType": "Event Type",
            "season": "Season",
            "gameType": "Game Type",
            "goalieId": "Goalie ID",
            "period": "Period",
            "periodType": "Period Type",
            "xCoordinate": "X Coodinate",
            "yCoordinate": "Y Coordinate"
        }
        queryable = ', '.join([x for x in self.eventSelection.keys()])
                
        # create a mapping of goalies to the events that they were a part of
        self.goalieEvents = {row[0]: {} for row in rows}

        # get all events
        curr.execute(f"SELECT {queryable} FROM shots")
        events = curr.fetchall()

        # separate all events by the goalie that was part of the event
        for event in events:
            if event[3] in self.goalieEvents:
                # separate by season
                if event[1] not in self.goalieEvents[event[3]]:
                    self.goalieEvents[event[3]][event[1]] = []
                self.goalieEvents[event[3]][event[1]].append(event)


        # The event table will only show data when a player has been selected 
        self.eventTable = QTableWidget()
        self.eventTable.setColumnCount(len(self.eventSelection))
        
        # controls the season number for the display 
        self.seasonComboBox = QComboBox()

        # display to show where goals/shots have been scored
        self.canvas = pg.plot()
        self.scatter = None
        self.canvas.showGrid(x=True, y=True)
        self.canvas.setXRange(-120, 120)
        self.canvas.setYRange(-80, 80)
        
        # main Container
        mainContainer = QWidget()
        mainContainerLayout = QHBoxLayout()
        mainContainer.setLayout(mainContainerLayout)        
        
        leftContainer = QWidget()
        leftContainerLayout = QVBoxLayout()
        leftContainer.setLayout(leftContainerLayout)
        # Fill in the widget information for the display
        leftContainerLayout.addWidget(self.query)
        leftContainerLayout.addWidget(self.playerTable)

        rightContainer = QWidget()
        rightContainerLayout = QVBoxLayout()
        rightContainer.setLayout(rightContainerLayout)
        # Fill in the widget information for the display
        rightContainerLayout.addWidget(self.seasonComboBox)
        rightContainerLayout.addWidget(self.eventTable)
        rightContainerLayout.addWidget(self.canvas)
        
        # Add the left and right components to the main container
        mainContainerLayout.addWidget(leftContainer)
        mainContainerLayout.addWidget(rightContainer)

        # setup the signals that are needed for changes to the table selection
        self.playerTable.itemSelectionChanged.connect(self.table_selection_changed)
        self.seasonComboBox.currentIndexChanged.connect(self.combo_box_changed)
        
        # Set the main widget 
        self.setCentralWidget(mainContainer)

    def table_selection_changed(self):
        """
        When the table has a selected item then it will change the display of the right
        side of the display. If more than one item is selected then nothing will be displayed.
        """
        # clear out everything in the table.
        # if 0 items or more than 1 item is selected in the player table, then
        # nothing should be displayed anyways. 
        while self.eventTable.rowCount() > 0:
            self.eventTable.removeRow(0)

        # clear out the combo box too
        self.seasonComboBox.clear()

        # clear the current canvas
        if self.scatter:
            self.scatter.clear()
        
        rows = set()
        items = self.playerTable.selectedItems()
        for item in items:
            rows.add(item.row())
        rows = list(rows)
            
        if len(rows) == 1:
            # set the combo box
            playerId = self.playerTable.item(rows[0], 0).text()
            self.activePlayerId = playerId

            if playerId in self.goalieEvents:
                values = []
                for value in self.goalieEvents[playerId]:
                    values.append(f"{value[0:4]} - {value[4:]}")
                self.seasonComboBox.addItems(values)
                self.seasonComboBox.setCurrentIndex(0)

    
    def combo_box_changed(self, index):
        """
        Combo box index changed, update the data that is stored in the event table
        """
        while self.eventTable.rowCount() > 0:
            self.eventTable.removeRow(0)

        # clear the canvas so that we can redraw later
        if self.scatter:
            self.scatter.clear()
            
        season = self.seasonComboBox.itemText(index)
        season = season.replace(" - ", "")

        if self.activePlayerId is not None:
            if self.activePlayerId in self.goalieEvents and \
               season in self.goalieEvents[self.activePlayerId]:

                xData = []
                yData = []
                
                events = self.goalieEvents[self.activePlayerId][season]

                self.eventTable.setRowCount(len(events))
                
                for r in range(len(events)):
                    for c in range(len(self.eventSelection)):
                        item = QTableWidgetItem(str(events[r][c]))
                        self.eventTable.setItem(r, c, item)

                    xData.append(float(events[r][len(self.eventSelection)-2]))
                    yData.append(float(events[r][len(self.eventSelection)-1]))


            # TODO: color different types of events differently
            # TODO: Create analysis of the results
            self.scatter = self.canvas.plot(xData, yData, pen=None, symbol='o')

        
    def search(self, s):
        """
        Display only the rows of data where the user entered text is found. When
        empty all rows in the table should appear.
        """
        if s:
            for i in range(self.playerTable.rowCount()):
                self.playerTable.hideRow(i)
        
        items = self.playerTable.findItems(s, Qt.MatchContains)
        if items:
            for item in items:
                self.playerTable.showRow(item.row())


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.resize(800, 800)
    window.show()
    app.exec_()
