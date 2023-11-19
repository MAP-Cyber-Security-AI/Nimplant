#!/usr/bin/python3

# -----
#
#   NimPlant Server - The "C2-ish"™ handler for the NimPlant payload
#   By Cas van Cooten (@chvancooten)
#
# -----

import threading
import time
import datetime
import random

from .api.server import api_server, server_ip, server_port
from .util.db import initDb, dbInitNewServer, dbPreviousServerSameConfig
from .util.func import nimplantPrint, periodicNimplantChecks
from .util.listener import *
from .util.nimplant import *
from .util.input import *


def main(xor_key=459457925, name=""):
    # Initialize the SQLite database
    initDb()

    # Restore the previous server session if config remains unchanged
    # Otherwise, initialize a new server session
    if dbPreviousServerSameConfig(np_server, xor_key):
        nimplantPrint("Existing server session found, restoring...")
        np_server.restoreServerFromDb()
    else:
        np_server.initNewServer(name, xor_key)
        dbInitNewServer(np_server)

    # Start daemonized Flask server for API communications
    t1 = threading.Thread(name="Listener", target=api_server)
    t1.setDaemon(True)
    t1.start()
    nimplantPrint(f"Started management server on http://{server_ip}:{server_port}.")

    t_reserve = threading.Thread(name="Listener", target=flaskListener, args=(xor_key, np_server.listenerPort))
    t_reserve.setDaemon(True)
    t_reserve.start()
    nimplantPrint(
        f"Started NimPlant reserve listener on {listenerType.lower()}://{listenerIp}:{np_server.listenerPort}. CTRL-C to cancel waiting for NimPlants."
    )
    configPort = np_server.listenerPort

    # Start another thread for NimPlant listener
    def startListener(port = listenerPort):
        try:
            t2._delete()
        except:
            pass

        t2 = threading.Thread(name="Listener", target=flaskListener, args=(xor_key, port))
        t2.setDaemon(True)
        t2.start()
        nimplantPrint(
            f"Started NimPlant listener on {listenerType.lower()}://{listenerIp}:{port}. CTRL-C to cancel waiting for NimPlants."
        )

    currentPort = listenerPort

    # Start another thread to periodically check if nimplants checked in on time
    t3 = threading.Thread(name="Listener", target=periodicNimplantChecks)
    t3.setDaemon(True)
    t3.start()

    possiblePorts = [8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087]
    list_length = len(possiblePorts)

    serverNamePortDict = {"Apache": 8080, "IIS": 8081, "Nginx": 8082, "Lighttpd": 8083, "NetWare": 8084, "GWS": 8085, "Domino": 8086, "NimPlant C2 Server": 80}

    def changeListenerPort(currentPort):
        while True:
            while(np_server.strategyThreeEnabled):
                if(np_server.strategyOneEnabled):
                    try:
                        newPort = serverNamePortDict[np_server.ident.split('/')[0]]
                    except:
                        newPort = np_server.listenerPort
                else:
                    minutes = int(datetime.now().minute//10)
                    random.seed(minutes)
                    index = random.randint(0, list_length - 1)
                    newPort = possiblePorts[index]

                if(newPort != np_server.listenerPort):
                    try:
                        np_server.listenerPort = newPort
                        startListener(newPort)
                    except:
                        pass

                time.sleep(1)
            np_server.listenerPort = configPort
            time.sleep(1)

    t4 = threading.Thread(name="PortChanger", target=changeListenerPort, args=([currentPort]))
    t4.start()

    # Run the console as the main thread
    while True:
        try:
            userInput = input()

            if np_server.isActiveNimplantSelected():
                promptUserForCommand()

            # This was commented out such that it is possible to activate/deactivate Strategies in the command line
            # Otherwise Nimplants would be automatically selected in the command line and then no Strategies can be commanded
            # elif np_server.containsActiveNimplants():
                # np_server.selectNextActiveNimplant()

            # server name - S1
            elif userInput == "Strategy One":
                np_server.strategyOneEnabled = not np_server.strategyOneEnabled
                print("Strategy 1 enabled: " + str(np_server.strategyOneEnabled))

            # userAgent  - S2
            elif userInput == "Strategy Two":
                np_server.strategyTwoEnabled = not np_server.strategyTwoEnabled
                print("Strategy 2 enabled: " + str(np_server.strategyTwoEnabled))
 
            # changing ports - S3, P3
            elif userInput == "Strategy Three":
                np_server.strategyThreeEnabled = not np_server.strategyThreeEnabled
                print("Strategy 3 enabled: " + str(np_server.strategyThreeEnabled))

            # changing endpoints - S4
            elif userInput == "Strategy Four":
                np_server.strategyFourEnabled = not np_server.strategyFourEnabled
                print("Strategy 4 enabled: " + str(np_server.strategyFourEnabled))

            # Changing Host header - S5
            elif userInput == "Strategy Five":
                np_server.strategyFiveEnabled = not np_server.strategyFiveEnabled
                print("Strategy 5 enabled: " + str(np_server.strategyFiveEnabled))

            # changing frequency - S6
            elif userInput == "Strategy Six":
                np_server.strategySixEnabled = not np_server.strategySixEnabled
                print("Strategy 6 enabled: " + str(np_server.strategySixEnabled))

            # changing packet size - S7
            elif userInput == "Strategy Seven":
                np_server.strategySevenEnabled = not np_server.strategySevenEnabled
                print("Strategy 7 enabled: " + str(np_server.strategySevenEnabled))

            else:
                pass

            time.sleep(0.5)

        except KeyboardInterrupt:
            exitServerConsole()
