"""
The script will create and fill the sqlite data base for this project.

Create two tables including the players(goalies) and the events that include:
- Shots
- Missed Shots
- Blocked Shots
- Goals
"""
import os
from json import dumps, loads
from enum import Enum
import sqlite3
from termcolor import colored
from os.path import exists


# Assume that the directory is in this same directory as this script
directory = 'nhl_data'
readArtifacts = "ReadFiles.json"

class Goalie:

    def __init__(self, jsonData=None):
        self.playerId = None
        self.firstName = None
        self.lastName = None
        self.shootsCatches = None

        if jsonData:
            self.fromJson(jsonData)

    def fromJson(self, jsonData):
        if "id" in jsonData:
            self.playerId = str(jsonData["id"])
        
        if "firstName" in jsonData:
            self.firstName = jsonData["firstName"]

        if "lastName" in jsonData:
            self.lastName = jsonData["lastName"]

        if "shootsCatches" in jsonData:
            self.shootsCatches = jsonData["shootsCatches"]

    @property
    def json(self):
        data = {
            "id": self.playerId,
            "firstName": self.firstName,
            "lastName": self.lastName,
            "shootsCatches": self.shootsCatches,
        }

        return data

    
class EventType(Enum):
    SHOT = 'Shot'
    GOAL = 'Goal'
    BLOCKED_SHOT = 'Blocked Shot'
    MISSED_SHOT = 'Missed Shot'

def eventTypeToStr(eventType):
    for x in EventType:
        if x.value == eventType:
            return x.value

    return None


eventTypes = [x.value for x in EventType]

    
class Event:
    def __init__(self, jsonData=None):
        self.season = None
        self.gameId = None
        self.gameType = None

        self.goaliId = None
        
        self.eventId = None
        self.period = None
        self.periodType = None
        self.periodTime = None
        self.dateTime = None
        self.coordinates = {}
        self.eventType = None
        
        if jsonData:
            if isinstance(jsonData, list):
                for x in jsonData:
                    self.fromJson(x)
            else:
                self.fromJson(jsonData)

    def fromJson(self, jsonData):
        if "about" in jsonData:
            self.eventId = jsonData["about"]["eventId"]
            self.period = jsonData["about"]["period"]
            self.periodType = jsonData["about"]["periodType"]
            self.periodTime = jsonData["about"]["periodTime"]
            self.dateTime = jsonData["about"]["dateTime"]
        if "coordinates" in jsonData:
            self.coordinates = jsonData["coordinates"]
        if "result" in jsonData:
            self.eventType = eventTypeToStr(jsonData["result"]["event"])

        if "game" in jsonData:
            self.gameId = str(jsonData["game"]["pk"])
            self.season = str(jsonData["game"]["season"])
            self.gameType = jsonData["game"]["type"]

        if "player" in jsonData:
            self.goalieId = str(jsonData["player"]["id"])

    @property
    def json(self):
        return {
            "gameId": self.gameId,
            "season": self.season,
            "gameType": self.gameType,
            "period": self.period,
            "periodType": self.periodType,
            "periodTime": self.periodTime,
            "dateTime": self.dateTime,
            "coordinates": self.coordinates,
            "eventType": self.eventType,
            "playerId": self.goalieId
        }
            

goalies = {}
events = []
readFiles = []

if exists(readArtifacts):
    with open(readArtifacts) as jsonFile:
        loadedData = loads(jsonFile.read())
    if "files" in loadedData:
        readFiles = loadedData["files"]


# Go through the list of files. Make sure that we have all players (these may
# require some corrections, see Corrections.py for more information). Retrieve
# all of the events from each game too; these will be added to the database. 
# 
# NOTE: Future consideration to only read files that haven't been included
# in this study yet.
for root, dirs, files in os.walk(directory):
    for filename in files:
        if filename in readFiles:
            print(colored(f"Skipping {filename}", 'yellow'))
            continue
        
        fname = os.path.join(root, filename)        
        print(colored(f"processing: {fname}", 'green'))

        jsonData = None
        with open(fname) as jsonFile:
            jsonData = loads(jsonFile.read())

        if jsonData:

            gameInfo = jsonData["gameData"]

            # Grab all player data, this will only add the player to the dictionary
            # if it does not already exist, indicating no wasted updates
            for playerId, playerData in jsonData["gameData"]["players"].items():
                if "primaryPosition" in playerData and "type" in playerData["primaryPosition"]:
                    if playerData["primaryPosition"]["type"] == "Goalie":
                        _playerId = str(playerData["id"])
                        if _playerId not in goalies:
                            goalies[_playerId] = Goalie(playerData)


            # All events are unique, so these will all be added to the database
            for event in jsonData["liveData"]["plays"]["allPlays"]:
                if event["result"]["event"] in eventTypes:
                    for player in event["players"]:
                        if str(player["player"]["id"]) in goalies:
                            events.append(Event([gameInfo, event, player]))

            # mark the file as read if the Json Data was converted and read correctly
            readFiles.append(filename)


# Create the connection to the database - create the file
# If there is not a file one will be created
# from this current script file, the database file should be located in ../app. 
currentDir = os.path.dirname(os.path.abspath(__file__))
splitDir = currentDir.split("/")
splitDir.pop()
currentDir = "/".join(splitDir)
dbfile = os.path.join(currentDir, "app/nhl.db")


con = sqlite3.connect(db_file)
cur = con.cursor()
# only create the tables we need if they dont already exist
cur.execute("CREATE TABLE IF NOT EXISTS players(playerId, firstName, lastName, shootsCatches)")
cur.execute("CREATE TABLE IF NOT EXISTS shots(eventType, season, gameId, gameType, goalieId, period, periodType, periodTime, dateTime, xCoordinate, yCoordinate)")

# insert the goalie player information
for _, goalie in goalies.items():
    cur.execute(f"INSERT INTO players VALUES(\"{goalie.playerId}\", \"{goalie.firstName}\", \"{goalie.lastName}\", \"{goalie.shootsCatches}\")")
con.commit()  # commit all goalie information

# insert all event information
for event in events:
    # older games did not have coordinates and the size of the arena was different.
    # Because this data was not tracked it should be nulled out to make sure that the
    # events are still added to the database
    if "x" not in event.coordinates or "y" not in event.coordinates:
        xcoord = ""
        ycoord = ""
    else:
        xcoord = event.coordinates["x"]
        ycoord = event.coordinates["y"]
    
    cur.execute(f"INSERT INTO shots VALUES (\"{event.eventType}\", \"{event.season}\", \"{event.gameId}\", \"{event.gameType}\", \"{event.goalieId}\", \"{event.period}\", \"{event.periodType}\", \"{event.periodTime}\", \"{event.dateTime}\", \"{xcoord}\", \"{ycoord}\")")
con.commit()  # commit all event information


with open("ReadFiles.json", "w") as jsonFile:
    jsonFile.write(dumps({"files": readFiles}, indent=2))
