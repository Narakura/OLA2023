# Authors: A. Borromini, J. Grassi
# Date: 29_08_2023

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm
import random
from scipy.optimize import linear_sum_assignment
from Environment import Environment, NonStationaryEnvironment
from Learners import Learner, UCBLearner, TSLearner, CUSUM, CUSUMUCB, SW_UCBLearner, EXP3Learner
from Utils import simulate_episode, test_seed, greedy_algorithm, hungarian_algorithm, get_reward, clairvoyant


"""Parameters Set Up"""

node_classes = 3
product_classes = 3
products_per_class = 3
means = np.random.uniform(10, 20, (3,3))
std_dev = np.ones((3,3))
rewards_parameters = (means, std_dev)
customer_assignments = np.random.choice([0,1,2], size=30)
n_arms = 30
n_phases = 3
T = 365
n_experiments = 100
def generate_graph_probabilities(n_nodes, edge_rate):
    graph_structure = np.random.binomial(1, edge_rate, (n_nodes, n_nodes))
    graph_probabilities = np.random.uniform(0.1, 0.9, (n_nodes, n_nodes)) * graph_structure
    return graph_probabilities

n_nodes = 30
edge_rate = 0.1

prob_phase1 = np.reshape(generate_graph_probabilities(n_nodes=n_nodes,edge_rate=edge_rate),(n_nodes,n_nodes))
prob_phase2 = np.reshape(generate_graph_probabilities(n_nodes=n_nodes,edge_rate=edge_rate),(n_nodes,n_nodes))
prob_phase3 = np.reshape(generate_graph_probabilities(n_nodes=n_nodes,edge_rate=edge_rate),(n_nodes,n_nodes))

# Array containing three (30*30) different probabilities tables.
p = np.stack((prob_phase1, prob_phase2, prob_phase3), axis=0)
# Array K will contain 30 arrays containing each 5 rows: row[i] of probability table of phase1, row[i] of the one of phase2, row[i] of the one of phase3, and so on
K = np.array([p[:, i] for i in range(p.shape[1])])

"""Estimating edge activation probabilities with Sliding Window UCB"""

window_size = int(T/6)
def SW_Generate_Probability_Estimates(p, n_arms=n_arms, n_phases=n_phases, T=T, window_size=window_size, n_experiments=10):
    phases_len = int(T / n_phases)

    experimentS_means_at_each_round = np.empty((n_experiments, T, n_arms))

    for e in tqdm(range(0, n_experiments)):
        # Initialize environment
        swucb_env = NonStationaryEnvironment(p, T)
        # Initialize learner
        swucb_learner = SW_UCBLearner(n_arms=n_arms, window_size=window_size)

        for t in range(0, T):
            # SW-UCB Learner
            pulled_arm = swucb_learner.pull_arm()
            reward = swucb_env.round(pulled_arm)
            swucb_learner.update(pulled_arm, reward)

            # At each round memorize a copy of the means of each arm
            expected_rew = swucb_learner.expectations()
            experimentS_means_at_each_round[e, t] = expected_rew.copy()

    return experimentS_means_at_each_round

SW_rounds_probabilities_for_each_arm = []

for index in range(len(K)):
    print("Learning for row:",index)
    estimates = SW_Generate_Probability_Estimates(K[index])
    SW_rounds_probabilities_for_each_arm.append(estimates)

SW_rounds_probabilities_for_each_arm = np.mean(SW_rounds_probabilities_for_each_arm, axis=1)


"""Estimating edge activation probabilities with Change Detection CUSUM UCB"""

def CUSUM_Generate_Probability_Estimates(p, n_arms=n_arms, n_phases=n_phases, T=T, n_experiments=5):
    phases_len = int(T / n_phases)
    experimentS_means_at_each_round = np.empty((n_experiments, T, n_arms))

    for e in tqdm(range(0, n_experiments)):
        # Initialize environment
        cusum_env = NonStationaryEnvironment(probabilities=p, horizon=T)
        # Initialize learner
        cusum_learner = CUSUMUCB(n_arms=n_arms, M=1, eps=0.1, h=0.5, alpha=0.2)

        for t in range(0, T):
            pulled_arm = cusum_learner.pull_arm()
            reward = cusum_env.round(pulled_arm)
            cusum_learner.update(pulled_arm, reward)

            # At each round memorize a copy of the means of each arm
            expected_rew = cusum_learner.expectations()
            experimentS_means_at_each_round[e, t] = expected_rew.copy()

    return experimentS_means_at_each_round

CUSUM_rounds_probabilities_for_each_arm = []

for index in range(len(K)):
    print("Learning for row:",index)
    estimates = CUSUM_Generate_Probability_Estimates(K[index])
    CUSUM_rounds_probabilities_for_each_arm.append(estimates)

CUSUM_rounds_probabilities_for_each_arm = np.mean(CUSUM_rounds_probabilities_for_each_arm, axis=1)


"""Estimating edge activation probabilities with EXP3"""

gamma = 0.5

def EXP3_Generate_Probability_Estimates(p, n_arms=n_arms, n_phases=n_phases, T=T, n_experiments=10):
    phases_len = int(T / n_phases)

    experimentS_means_at_each_round = np.empty((n_experiments, T, n_arms))

    for e in tqdm(range(0, n_experiments)):
        # Initialize environment
        exp3_env = NonStationaryEnvironment(probabilities=p, horizon=T)
        # Initialize learner
        exp3_learner = EXP3Learner(n_arms=n_arms, gamma=gamma)

        for t in range(0, T):
            # SW-UCB Learner
            pulled_arm = exp3_learner.pull_arm()
            reward = exp3_env.round(pulled_arm)
            exp3_learner.update(pulled_arm, reward)

            # At each round memorize a copy of the means of each arm
            expected_rew = exp3_learner.expectations()
            experimentS_means_at_each_round[e, t] = expected_rew.copy()

    return experimentS_means_at_each_round

EXP3_rounds_probabilities_for_each_arm = []

for index in range(len(K)):
    print("Learning for row:",index)
    estimates = EXP3_Generate_Probability_Estimates(K[index])
    EXP3_rounds_probabilities_for_each_arm.append(estimates)

EXP3_rounds_probabilities_for_each_arm = np.mean(EXP3_rounds_probabilities_for_each_arm, axis=1)


"""Aligning probability estimates to each round"""
def Reshape(LIST):
  # Convert the lists into a NumPy array
  array_of_lists = np.array(LIST)
  # Transpose the array to swap the axes
  transposed_array = array_of_lists.T
  # Split the transposed array into separate arrays along axis=1
  return np.split(transposed_array, transposed_array.shape[1], axis=1)

estimated_tables_SW = Reshape(SW_rounds_probabilities_for_each_arm)
estimated_tables_CUSUM = Reshape(CUSUM_rounds_probabilities_for_each_arm)
estimated_tables_EXP3 = Reshape(EXP3_rounds_probabilities_for_each_arm)

phases_array = np.empty((T, n_nodes, n_nodes))
T = 365
phases_len = int(T / n_phases)

for t in range(T):
    if t <= 121:
        phases_array[t] = p[0]
    elif t in range(122, 244):
        phases_array[t] = p[1]
    elif t > 243:
        phases_array[t] = p[2]

SW_reward = [np.sum(i) for i in estimated_tables_SW]
CUSUM_reward = [np.sum(i) for i in estimated_tables_CUSUM]
EXP3_reward = [np.sum(i) for i in estimated_tables_EXP3]
Clairv = [np.sum(i) for i in phases_array]



"""Instantaneous reward of edge activation probability estimation"""

time_periods = range(1, 366)
plt.figure(figsize=(10, 6))
plt.plot(time_periods, Clairv, color='lightgreen', linestyle='-', label='Optimum', linewidth=4)
plt.plot(time_periods, SW_reward, color='blue', linestyle='-', label='Sliding Window')
plt.plot(time_periods, CUSUM_reward, color='red', linestyle='-', label='CUSUM')
plt.plot(time_periods, EXP3_reward, color='purple', linestyle='-', label='EXP3')
plt.xlabel('Time')
plt.ylabel('Instantaneous Reward')
plt.title('Instantaneous Reward of UCB and TS probability estimations')
plt.legend()
plt.grid()
plt.show()


"""Cumulative regrets of edge activation probability estimation"""

estimated_tables_SW = np.array(estimated_tables_SW)
estimated_tables_CUSUM = np.array(estimated_tables_CUSUM)
estimated_tables_EXP3 = np.array(estimated_tables_EXP3)

original_shape = estimated_tables_SW.shape
estimated_tables_SW = estimated_tables_SW.reshape(original_shape[0], original_shape[1], original_shape[3])
estimated_tables_CUSUM = estimated_tables_CUSUM.reshape(original_shape[0], original_shape[1], original_shape[3])
estimated_tables_EXP3 = estimated_tables_EXP3.reshape(original_shape[0], original_shape[1], original_shape[3])

SW_regret = np.sum((phases_array - estimated_tables_SW),axis=(1,2))
CUSUM_regret = np.sum((phases_array - estimated_tables_CUSUM),axis=(1,2))
EXP3_regret = np.sum((phases_array - estimated_tables_EXP3),axis=(1,2))
SW_cumulative_regret = np.cumsum(SW_regret)
CUSUM_cumulative_regret = np.cumsum(CUSUM_regret)
EXP3_cumulative_regret = np.cumsum(EXP3_regret)

plt.figure(figsize=(10, 6))
plt.plot(SW_cumulative_regret, label='SW Cumulative Regret', color="blue")
plt.plot(CUSUM_cumulative_regret, label='CUSUM Cumulative Regret', color = "red")
plt.plot(EXP3_cumulative_regret, label='EXP3 Cumulative Regret', color = "purple")
plt.xlabel('Time')
plt.ylabel('Cumulative Regret')
plt.title('Cumulative Regret Comparison')
plt.legend()
plt.grid()
plt.show()



"""COMPUTING OVERALL REWARDS (Influence Propagation + Matching) using estimated edge probabilities"""

n_exp = 4

SW_mean_rewards_per_round = []
SW_std_dev_rewards_per_round = []
for table in tqdm(range(len(estimated_tables_SW))):
    true_p = phases_array[table]
    table = np.reshape(estimated_tables_SW[table],(30,30))
    clairvoyant_output = clairvoyant(table, true_p, customer_assignments, rewards_parameters, rewards_parameters, n_exp)
    SW_mean_rewards_per_round.append(clairvoyant_output[0])
    SW_std_dev_rewards_per_round.append(clairvoyant_output[1])

CUSUM_mean_rewards_per_round = []
CUSUM_std_dev_rewards_per_round = []
for table in tqdm(range(len(estimated_tables_CUSUM))):
    true_p = phases_array[table]
    table = np.reshape(estimated_tables_CUSUM[table],(30,30))
    clairvoyant_output = clairvoyant(table, true_p, customer_assignments, rewards_parameters, rewards_parameters, n_exp)
    CUSUM_mean_rewards_per_round.append(clairvoyant_output[0])
    CUSUM_std_dev_rewards_per_round.append(clairvoyant_output[1])

EXP3_mean_rewards_per_round = []
EXP3_std_dev_rewards_per_round = []
for table in tqdm(range(len(estimated_tables_EXP3))):
    true_p = phases_array[table]
    table = np.reshape(estimated_tables_EXP3[table],(30,30))
    clairvoyant_output = clairvoyant(table, true_p, customer_assignments, rewards_parameters, rewards_parameters, n_exp)
    EXP3_mean_rewards_per_round.append(clairvoyant_output[0])
    EXP3_std_dev_rewards_per_round.append(clairvoyant_output[1])

optimum_means = []
for table in p:
    a = []
    for i in tqdm(range(30)):
        z = clairvoyant(table, table, customer_assignments, rewards_parameters, rewards_parameters, n_exp=10)[0]
        a.append(z)
    clairvoyant_output = max(a)

    for i in range(int(365 / 3) + 1):
        optimum_means.append(clairvoyant_output)
optimum_means = optimum_means[:-1]


"""Plotting overall instantaneous rewards"""

plt.figure(figsize=(10, 6))
time_periods = range(len(SW_mean_rewards_per_round))
for t in time_periods:
    mean = SW_mean_rewards_per_round[t]
    std_dev = SW_std_dev_rewards_per_round[t]
    plt.vlines(t, mean - std_dev, mean + std_dev, color='lightblue')
plt.plot(time_periods, optimum_means, color='green', linestyle='-', linewidth=5)
plt.plot(time_periods, SW_mean_rewards_per_round, color='blue', linestyle='-')
plt.xlabel('Time')
plt.ylabel('Reward')
plt.title('Sliding Window UCB')
plt.xticks(time_periods[::30])
plt.show()


plt.figure(figsize=(12, 7))
time_periods = range(len(CUSUM_mean_rewards_per_round))
for t in time_periods:
    mean = CUSUM_mean_rewards_per_round[t]
    std_dev = CUSUM_std_dev_rewards_per_round[t]
    plt.vlines(t, mean - std_dev, mean + std_dev, color='lightpink')
plt.plot(time_periods, optimum_means, color='green', linestyle='-', linewidth=5)
plt.plot(time_periods, CUSUM_mean_rewards_per_round, color='red', linestyle='-')
plt.xlabel('Time')
plt.ylabel('Reward')
plt.title('Change Detection CUSUM UCB')
plt.xticks(time_periods[::30])
plt.show()


plt.figure(figsize=(12, 7))
time_periods = range(len(EXP3_mean_rewards_per_round))
for t in time_periods:
    mean = EXP3_mean_rewards_per_round[t]
    std_dev = EXP3_std_dev_rewards_per_round[t]
    plt.vlines(t, mean - std_dev, mean + std_dev, color='pink')
plt.plot(time_periods, optimum_means, color='green', linestyle='-', linewidth=5)
plt.plot(time_periods, EXP3_mean_rewards_per_round, color='purple', linestyle='-')
plt.xlabel('Time')
plt.ylabel('Reward')
plt.title('Change Detection CUSUM UCB')
plt.xticks(time_periods[::30])
plt.show()


"""Plotting overall cumulative regret"""

plt.figure(figsize=(10, 6))
SW_cumulative_regret = [sum([abs(x - y) for x, y in zip(optimum_means[:t+1], SW_mean_rewards_per_round[:t+1])]) for t in time_periods]
CD_cumulative_regret = [sum([abs(x - y) for x, y in zip(optimum_means[:t+1], CUSUM_mean_rewards_per_round[:t+1])]) for t in time_periods]
EXP3_cumulative_regret = [sum([abs(x - y) for x, y in zip(optimum_means[:t+1], EXP3_mean_rewards_per_round[:t+1])]) for t in time_periods]
plt.plot(time_periods, SW_cumulative_regret, color='blue', linestyle='-', label="SW_UCB")
plt.plot(time_periods, CD_cumulative_regret, color="red", linestyle="-", label="CD_UCB")
plt.plot(time_periods, EXP3_cumulative_regret, color="purple", linestyle="-", label="EXP3")
plt.xlabel('Time')
plt.ylabel('Cumulative Regret')
plt.title('Cumulative Regrets')
plt.xticks(time_periods[::30])
plt.legend()
plt.show()
