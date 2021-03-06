import time
import torch
import numpy as np
import torch.nn.functional as F
from collections import deque
import matplotlib.pyplot as plt
from agents.base_agent import Agent

class DQN(Agent):
    
    def __init__(self, env, params):
        super().__init__(env, params)
    
    def optimize_model(self):
        if self.frames_seen > self.params["burn_in"]:
            self.optimizer.zero_grad()
            replays = self.replay_buffer.sample(self.params["batch_size"])
            state_batch = torch.cat([rep[0] for rep in replays]).to(self.device)
            action_batch = torch.cat([rep[1] for rep in replays]).to(self.device)
            next_state_batch = torch.cat([rep[2] for rep in replays]).to(self.device)
            reward_batch = torch.cat([rep[3] for rep in replays]).to(self.device)
            mask = torch.FloatTensor([int(not rep[4]) for rep in replays]).to(self.device).unsqueeze(1)

            #non_final_mask = torch.tensor(tuple(map(lambda d: not d, done_batch)), device=self.device, dtype=torch.bool)
            #non_final_next_states = torch.stack([s for s, d in zip(next_state_batch, non_final_mask) if d])

            state_action_values = self.Q(state_batch).gather(1, action_batch)
            target_state_action_values = self.Q_target(next_state_batch).max(1)[0].detach().unsqueeze(1)
            y = reward_batch + self.params["gamma"] * mask * target_state_action_values
            #y[not done_batch] = y[not done_batch] + self.params["gamma"] * target_state_action_values
            
            #print(self.Q(state_batch))
            
            loss = F.mse_loss(state_action_values, y)
            loss.backward()
            self.optimizer.step()
            self.update_epsilon()
            
    def train(self):
        self.frames_seen = 0
        for e in range(self.params["train_episodes"]):
            #Reset environment and get initial state
            frame = self.env.reset()
            state = self.extract_state(frame, frame)
            done = False
            total_reward = 0.0
            t = 0
            prev_lives = -1
            while not done:
                action = self.epsilon_greedy_action(state.to(self.device))
                next_frame, reward, done, info = self.env.step(action.item())
                if prev_lives > info["ale.lives"]:
                    reward = reward - 1
                    my_done = True
                else:
                    my_done = False
                prev_lives = info["ale.lives"]
                total_reward += reward
                reward = torch.tensor([[reward]])
                next_state = self.extract_state(frame, next_frame)
                self.replay_buffer.push(state, action, next_state, reward, done)
                state = next_state
                frame = next_frame
                self.optimize_model()
                self.frames_seen += 1
                t += 1
                if (self.frames_seen+1) % self.params["update_period"] == 0:
                    self.update_target()
                    print("UPDATING TARGET!!!!!!")
                if (self.frames_seen+1) % self.params["eval_period"] == 0:
                    self.evaluate_policy()
                    self.record_video()
            print("Frames seen:", self.frames_seen)
            print("Training episode", e, "completed in", t, "steps.")
            print("Reward achieved:", total_reward)
            print("Epsilon:", self.epsilon)
            
      
