import gymnasium as gym
from gymnasium import spaces
from gymnasium.utils import seeding
import numpy as np
import datetime
import time
import subprocess
from .nimplant import *
from datetime import timedelta as td


class NimPlantEnv(gym.Env):

    def __init__(self, natural=False):
        self.action_space = spaces.Discrete(8, start=0)
        self.observation_space = spaces.Discrete(128)
        self.state = np.zeros(7, dtype=bool)

        self.actionDict = {
            0: "Do Nothing",
            1: "Strategy One",
            2: "Strategy Two",
            3: "Strategy Three",
            4: "Strategy Four",
            5: "Strategy Five",
            6: "Strategy Six",
            7: "Strategy Seven"
        }

        self.alert_weights = {
            1000101: 5, # nimplant keyword
            1000102: 1, # register
            1000103: 2, # task  
            1000104: 2, # result
            1000105: 5, # nimplant keyword
            1000106: 1, # register
            1000107: 2, # task  
            1000108: 2, # result

            1000201: 5, # nimplant keyword
            1000202: 1, # register
            1000203: 2, # task    
            1000204: 2, # result
            1000205: 2, # thresholds 15 in 1minute: frequency
            1000206: 1, # thresholds 10 in 1minute: frequency
            1000207: 2, # thresholds 5 in 1minute 100<>200 
            1000208: 2, # thresholds 5 in 1minute 200<>300 

            1000301: 5, # nimplant keyword
            1000302: 1, # register ->
            1000303: 2, # task     ->  
            1000304: 2, # result   ->
            1000305: 5, # nimplant keyword
            1000306: 1, # register <-
            1000307: 1, # task     <-     
            1000308: 1, # result   <-
            1000309: 2, # thresholds 2 in 0.5 minute 200<>300 
            1000310: 2, # thresholds 2 in 0.5 minute 130<>140 
            1000311: 2, # thresholds 2 in 0.5 minute 100<>200 
            1000312: 1  # IP_IN_HOST_HEADER
        }

        try:
            snort_log_path = '/var/log/snort/alert'
            with open(snort_log_path, 'w'):
                pass  
            print(f"Content of {snort_log_path} deleted successfully.")

        except Exception as e:
            print(f"Error deleting content of {snort_log_path}: {e}")
    
    def state_to_index(self, state):
        # Convert the boolean values to binary representation and concatenate them
        binary_representation = ''.join('1' if value else '0' for value in state)

        # Convert the binary representation to an integer
        index = int(binary_representation, 2)

        return index

    def index_to_state(self, index):
        # Convert the integer index to binary representation
        binary_representation = bin(index)[2:]

        # Pad the binary representation with zeros to match the desired length
        binary_representation = binary_representation.rjust(len(self.initial_state), '0')

        # Convert the binary representation back to a list of boolean values
        state = [bit == '1' for bit in binary_representation]

        return state

    def reset(self):
        self.state = np.zeros(7, dtype=bool)

    def trigger_strategy(self, strategy):
        if strategy == "Strategy One":
            np_server.strategyOneEnabled = not np_server.strategyOneEnabled
            print("Strategy 1 enabled: " + str(np_server.strategyOneEnabled))

        # userAgent  - S2
        elif strategy == "Strategy Two":
            np_server.strategyTwoEnabled = not np_server.strategyTwoEnabled
            print("Strategy 2 enabled: " + str(np_server.strategyTwoEnabled))

        # changing ports - S3, P3
        elif strategy == "Strategy Three":
            np_server.strategyThreeEnabled = not np_server.strategyThreeEnabled
            print("Strategy 3 enabled: " + str(np_server.strategyThreeEnabled))

        # changing endpoints - S4
        elif strategy == "Strategy Four":
            np_server.strategyFourEnabled = not np_server.strategyFourEnabled
            print("Strategy 4 enabled: " + str(np_server.strategyFourEnabled))

        # Changing Host header - S5
        elif strategy == "Strategy Five":
            np_server.strategyFiveEnabled = not np_server.strategyFiveEnabled
            print("Strategy 5 enabled: " + str(np_server.strategyFiveEnabled))

        # changing frequency - S6
        elif strategy == "Strategy Six":
            np_server.strategySixEnabled = not np_server.strategySixEnabled
            print("Strategy 6 enabled: " + str(np_server.strategySixEnabled))

        # changing packet size - S7
        elif strategy == "Strategy Seven":
            np_server.strategySevenEnabled = not np_server.strategySevenEnabled
            print("Strategy 7 enabled: " + str(np_server.strategySevenEnabled))

        else:
            print("Do nothing.")

    def step(self, action):

        assert self.action_space.contains(action)
        done = False
        strategy = self.actionDict[action]
        self.trigger_strategy(strategy)
        self.action_time = datetime.now() 
        print("Sleep for 30 seconds to count alerts ...")
        time.sleep(30)

        # Read and filter Snort alerts based on the time interval
        alerts = self.read_snort_alerts()

        print(f"Number of alerts {len(alerts)}")

        if(action != 0):
            self.state[action-1] = not self.state[action-1]

        print(f"The triggered Strategy {strategy}")
        print(f"State: {self.state}")
        
        #alert dependent
        number_of_alerts = len(alerts)

        # positive reward, but continue until 5 
        if number_of_alerts == 0:
            reward = 10 - self.state.sum()
        else:
            sum_of_weights = 0
            for sid in alerts:
                sum_of_weights+= self.alert_weights[sid]
            reward = -4 * sum_of_weights - self.state.sum()
        print(f"Triggered Alerts SIDs: {alerts}")
        print(f"Reward: {reward}")

        print("\n\n")

        if(reward >= 5):
            done = True

        return self.state_to_index(self.state), reward, done, {}
    
    def read_snort_alerts(self):
        snort_log_path = '/var/log/snort/alert'
        command = ['tail', '-n', '1000', snort_log_path]  # Read enough lines to cover 30 seconds

        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.stderr:
                print(f"Error reading Snort log: {result.stderr}")
                return []
            else:
                # Forward to filtering step
                alerts = self.filter_alerts(result.stdout.splitlines())
                return alerts

        except Exception as e:
            print(f"An error occurred: {e}")
            return []
    
    # return a list of SIDs
    def filter_alerts(self, alerts):
        # Filter alerts based on SIDs and timestamps
        filtered_alerts = []
        for alert in alerts:
            parts = alert.split(" ")
            if len(parts) >= 4:
                # extract SID and time
                sid_str = parts[3].split(":")[1]
                timestamp_str = f"{parts[0]}"


                # print(f"extractd SID {sid_str}, and time {timestamp_str}")

                # convert them
                timestamp = datetime.strptime(f"2023-{timestamp_str}", "%Y-%m/%d-%H:%M:%S.%f").timestamp()
                sid = int(sid_str) if sid_str.isdigit() else None

            if self.is_recent_alert(timestamp) and self.is_bot_related_alert(sid):
                filtered_alerts.append(sid)

        return set(filtered_alerts)

    def is_bot_related_alert(self, sid):
        return sid is not None and sid > 1000000  
    
    def is_recent_alert(self, timestamp):
        # print(f"Action ts: {datetime.datetime.fromtimestamp(self.action_time)}, alert ts: {datetime.datetime.fromtimestamp(timestamp)}")
        # print(f"Action ts: {self.action_time}, alert ts: {timestamp}")

        # waiting additional 10 seconds after taking an action 
        time_delta = td(seconds=15)

        return timestamp is not None and timestamp > (self.action_time + time_delta).timestamp()