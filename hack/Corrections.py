"""
The script is used for corrections to the available data in the database.

The corrections include the value for shootsCatches to the goalies. Some of
the data is not found or available during the live game data search. 
"""
import os
import sqlite3
from requests import get
from termcolor import colored
from json import dumps

# Base endpoint for people
NhlPeopleEndpoint = "https://statsapi.web.nhl.com/api/v1/people/"

# The database file should be located in ../app
currentDir = os.path.dirname(os.path.abspath(__file__))
splitDir = currentDir.split("/")
splitDir.pop()
currentDir = "/".join(splitDir)
dbfile = os.path.join(currentDir, "app/nhl.db")

# open the database and read the data to make corrections
con = sqlite3.connect(dbfile)
cur = con.cursor()

# test get all players
cur.execute("SELECT playerId, firstName, lastName, shootsCatches FROM players WHERE shootsCatches='None'")
rows = cur.fetchall()

for row in rows:
    endpoint = f"{NhlPeopleEndpoint}{row[0]}"
    print(colored(f"Attempting to correct shootsCatches for {row[1]} {row[2]}", 'green'))

    try:
        jsonData = get(endpoint).json()
    except:
        print(colored(f"failed to find data for {row[1]} {row[2]}", 'red'))
        continue

    if "people" in jsonData:
        if "shootsCatches" in jsonData["people"][0]:
            shootsCatches = jsonData["people"][0]["shootsCatches"]
            cur.execute(f"UPDATE players SET shootsCatches = '{shootsCatches}' WHERE playerId = '{row[0]}'")
            print(colored(f"Corrected {row[1]} {row[2]} set shootsCatches to {shootsCatches}", 'blue'))

con.commit()  # commit all corrections

    
