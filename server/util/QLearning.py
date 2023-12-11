import random
import numpy as np
import pickle
import datetime
import os


def save_learning_state(episodes, q_table):
    folder_path_learning_state = "learning_states"
    if not os.path.exists(folder_path_learning_state):
        os.makedirs(folder_path_learning_state)
 
    learning_state = os.path.join(folder_path_learning_state, f"learning_state.pkl")
 
    data = episodes, q_table
 
    with open(learning_state, 'wb') as file:
        pickle.dump(data, file)  
 
def load_learning_state(filename='learning_states/learning_state.pkl'):
    try:
        with open(filename, 'rb') as file:
            episode, q_table = pickle.load(file)
        return episode, q_table
    except:
        return 1, None

def Q_learning_train(env,alpha,gamma,epsilon,episodes): 
    
    #check if learning state exists
    learning_state_file_path = 'learning_states/learning_state.pkl'
    last_state, q_table = load_learning_state(learning_state_file_path)  
    
    #Initialize Q table of 128 x 8 size (128 states and 8 actions) with all zeroes
    if q_table is None:
        q_table = np.random.rand(env.observation_space.n, env.action_space.n) * 0.1
    
    for i in range(last_state, episodes+1):
        state = env.reset()
    
        reward = 0
        done = False

        while not done:
            if random.uniform(0, 1) < epsilon:
                action = env.action_space.sample() # Explore action space randomly
            else:
                action = np.argmax(q_table[state, :])%8 # Exploit learned values by choosing optimal values

            next_state, reward, done, info = env.step(action) 

            old_value = q_table[state, action]
            next_max = np.max(q_table[next_state, :]) if q_table[next_state].size > 0 else 0

            new_value = (1 - alpha) * old_value + alpha * (reward + gamma * next_max)
            q_table[state, action] = new_value


            state = next_state

            # Save Q-Tables, in case we need them later
            folder_path_learning_qtables = "learning_qtables"
            if not os.path.exists(folder_path_learning_qtables):
                os.makedirs(folder_path_learning_qtables)
            
            current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H")
            filename_qtable = os.path.join(folder_path_learning_qtables, f"learning_qtable_{current_datetime}.pkl")
            
            if os.path.exists(filename_qtable):
                with open(filename_qtable, 'ab') as file:
                    pickle.dump(q_table, file)
            else:
                with open(filename_qtable, 'wb') as file:
                    pickle.dump(q_table, file)  
        
        if i % 10 == 0:
            print(f"Episode: {i}")

        # Save q_table after each episode
        save_learning_state(i, q_table)

    # Start with a random policy
    policy = np.ones([env.observation_space.n, env.action_space.n]) / env.action_space.n

    for state in range(env.observation_space.n):  #for each states
        best_act = np.argmax(q_table[state])%8 #find best action
        policy[state] = np.eye(env.action_space.n)[best_act]  #update 


    folder_path_policies = "final_policies"
    if not os.path.exists(folder_path_policies):
        os.makedirs(folder_path_policies)
    
    folder_path_qtables = "final_qtables"
    if not os.path.exists(folder_path_qtables):
        os.makedirs(folder_path_qtables)
    
    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename_policy = os.path.join(folder_path_policies, f"policy_{current_datetime}.pkl")
    filename_qtable = os.path.join(folder_path_qtables, f"qtable_{current_datetime}.pkl")
    
    
    with open(filename_policy, 'wb') as file:
        pickle.dump(policy, file)
    
    with open(filename_qtable, 'wb') as file:
        pickle.dump(q_table, file)
    

    if os.path.exists(learning_state_file_path):
        os.remove(learning_state_file_path)
        
    print("Training finished.\n")
    print(policy.shape)
    print(policy)
    print(q_table.shape)
    print(q_table)
    return policy, q_table