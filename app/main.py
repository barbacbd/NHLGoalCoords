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
        self.playerSelection = {
            "playerId": "Player ID",
            "firstName": "First Name",
            "lastName": "Last Name",
            "shootsCatches": "Catches"
        }
        queryable = ", ".join([x for x in self.playerSelection.keys()])

        curr.execute(f"SELECT {queryable} FROM players")
        rows = curr.fetchall()
        data = rows

        self.playerTable = QTableWidget()
        self.playerTable.setRowCount(len(rows))
        self.playerTable.setColumnCount(len(self.playerSelection))
        self.playerTable.setHorizontalHeaderLabels(list(self.playerSelection.values()))

        self.rowWidgets = []
        
        # This seems like a bad way of doing things but let's brute force
        # fill the table with all of the Goalie information
        for r in range(len(rows)):
            for c in range(len(self.playerSelection)):
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
        self.eventTable.setHorizontalHeaderLabels(list(self.eventSelection.values()))

        # The evaluation table will only show data when a season is selected
        self.evalTable = QTableWidget()
        # Columns = side (glove vs stick), shots, goals, save percentage
        # The side will indicate the rows (should always be 2)
        self.evalTable.setColumnCount(4)
        self.evalTable.setHorizontalHeaderLabels(["Shot Side", "Shots", "Goals", "Save Percentage"])

        self.evalTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.evalTable.resizeColumnsToContents()

        
        # controls the season number for the display 
        self.seasonComboBox = QComboBox()

        # display to show where goals/shots have been scored
        self.canvas = pg.plot()
        self.scatter = None
        self.canvas.showGrid(x=True, y=True)
        # A hockey arena is 200 x 805 ft. The coordinates are [-100, 100] and [-42.5, 42.5]
        # lets provide a slight buffer here.
        self.canvas.setXRange(-105, 105)
        self.canvas.setYRange(-45, 45)
        
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
        rightContainerLayout.addWidget(self.evalTable)
        
        # Add the left and right components to the main container
        mainContainerLayout.addWidget(leftContainer)
        mainContainerLayout.addWidget(rightContainer)

        # setup the signals that are needed for changes to the table selection
        self.playerTable.itemSelectionChanged.connect(self.table_selection_changed)
        self.seasonComboBox.currentIndexChanged.connect(self.combo_box_changed)
        
        # Set the main widget 
        self.setCentralWidget(mainContainer)

    def _get_player_table_rows(self):
        rows = set()
        items = self.playerTable.selectedItems()
        for item in items:
            rows.add(item.row())
        rows = list(rows)
        return rows
        
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

        # clear the table containing the save percentage info
        while self.evalTable.rowCount() > 0:
            self.evalTable.removeRow(0)
            
        # clear out the combo box too
        self.seasonComboBox.clear()

        # clear the current canvas
        if self.scatter:
            self.scatter.clear()
        
        rows = self._get_player_table_rows()
            
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

        while self.evalTable.rowCount() > 0:
            self.evalTable.removeRow(0)

        # clear the canvas so that we can redraw later
        if self.scatter:
            self.scatter.clear()
            
        season = self.seasonComboBox.itemText(index)
        season = season.replace(" - ", "")

        xData = []
        yData = []
        records = {
            "left": {
                "side": "",
                "shots": 0,
                "goals": 0,
                "savePercentage": 0.0
            },
            "right": {
                "side": "",
                "shots": 0,
                "goals": 0,
                "savePercentage": 0.0
            }
        }
        setRecords = False
                        
        if self.activePlayerId is not None:
            if self.activePlayerId in self.goalieEvents and \
               season in self.goalieEvents[self.activePlayerId]:
                events = self.goalieEvents[self.activePlayerId][season]
                
                self.eventTable.setRowCount(len(events))
                
                for r in range(len(events)):
                    for c in range(len(self.eventSelection)):
                        item = QTableWidgetItem(str(events[r][c]))
                        self.eventTable.setItem(r, c, item)

                    if events[r][len(self.eventSelection)-2] == '' or \
                       events[r][len(self.eventSelection)-1] == '':
                        continue
                    
                    xcoord = float(events[r][len(self.eventSelection)-2])
                    xData.append(xcoord)
                    ycoord = float(events[r][len(self.eventSelection)-1]) 
                    yData.append(ycoord)
                    
                    if events[r][0] in ("Goal", "Blocked Shot", "Shot"):
                        shotToSide = "right"  # Q2 or Q4 - this is a shot to the goalies left
                        if (xcoord >= 0 and ycoord >= 0) or (xcoord < 0 and ycoord < 0):
                            # Q1 or Q3 - this is a shot to the goalies right
                            shotToSide = "left"
                        if shotToSide in records:
                            if events[r][0] == "Goal":
                                records[shotToSide]["goals"] += 1
                            records[shotToSide]["shots"] += 1

                    setRecords = True
                    

                # Columns = side (glove vs stick), shots, goals, save percentage
                # The side will indicate the rows (should always be 2)
                rows = self._get_player_table_rows()
                if len(rows) == 1 and setRecords:
                    shootsCatches = self.playerTable.item(rows[0], len(self.playerSelection)-1).text()

                    if shootsCatches == "L":  # more than likely right handed
                        records["left"]["side"] = "glove"
                        records["right"]["side"] = "stick"
                    else:
                        records["left"]["side"] = "stick"
                        records["right"]["side"] = "glove"

                    weakKey = None
                    weakPercent = 100
                    for key, value in records.items():
                        savePercent = float(value["shots"] - value["goals"]) / float(value["shots"]) * 100.0
                        records[key]["savePercentage"] = savePercent

                        if savePercent < weakPercent:
                            weakPercent = savePercent
                            weakKey = key
                        
                    # update the eval table
                    self.evalTable.setRowCount(len(records))
                    keys = list(records.keys())
                    for r in range(len(records)):
                        shouldHighlight = keys[r] == weakKey
                        
                        innerKeys = list(records[keys[r]].keys())
                        for c in range(len(records[keys[r]])):
                            item = QTableWidgetItem(str(records[keys[r]][innerKeys[c]]))

                            # highlight the cells where the key is the weaker of the sides
                            if shouldHighlight:
                                item.setBackground(QtGui.QColor(255, 255, 0))
                            
                            self.evalTable.setItem(r, c, item)
                        
            # pen=None disables line drawing
            self.scatter = self.canvas.plot(xData, yData, pen=None, symbol='+')

        
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
