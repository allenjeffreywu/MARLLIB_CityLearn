# MIT License

# Copyright (c) 2023 Allen Wu

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
An example of integrating new tasks into MARLLib
About ma-gym: https://github.com/koulanurag/ma-gym
doc: https://github.com/koulanurag/ma-gym/wiki

Learn how to transform the environment to be compatible with MARLlib:
please refer to the paper: https://arxiv.org/abs/2210.13708
"""

import numpy as np
from ray.rllib.env.multi_agent_env import MultiAgentEnv
from gym.spaces import Dict as GymDict, Box
from marllib import marl
from marllib.envs.base_env import ENV_REGISTRY
import time

# importing CityLearn
from citylearn.citylearn import CityLearnEnv
from citylearn.wrappers import StableBaselines3Wrapper
from citylearn.wrappers import NormalizedObservationWrapper
from pathlib import Path

# FIX THIS
REGISTRY = {}
REGISTRY["CityLearn"] = CityLearnEnv


policy_mapping_dict = {
    "CityLearn": {
        "description": "two buildings cooperate",
        "team_prefix": ("building_1_", "building_2_"),
        "all_agents_one_policy": True,
        "one_agent_one_policy": True,
    }
}

class RLlibCityLearnGym(MultiAgentEnv):

    def __init__(self, env_config):
        map = env_config["map_name"]
        env_config.pop("map_name", None)

        self.env = REGISTRY[map](**env_config)
        # assume all agent same action/obs space
        self.action_space = self.env.action_space[0]
        self.observation_space = GymDict({"obs": Box(
            low=-10000.0,
            high=10000.0,
            shape=(self.env.observation_space[0].shape[0],),
            dtype=np.dtype("float64"))})
        self.agents = ["building_1", "building_2"]
        self.num_agents = len(self.agents)
        env_config["map_name"] = map
        self.env_config = env_config

    def reset(self):
        original_obs = self.env.reset()
        obs = {}
        for i, name in enumerate(self.agents):
            obs[name] = {"obs": np.array(original_obs[i])}
        return obs

    def step(self, action_dict):
        action_ls = [action_dict[key] for key in action_dict.keys()]
        # THIS IS THE WRONG WAY TO HANDLE THE STEP => SEE THE CITYLEARN STEP!!
        # o = observations
        # r = rewards
        # d = done
        # info = get_info of citylearn
        o, r, d, info = self.env.step(action_ls)
        rewards = {}
        obs = {}
        for i, key in enumerate(action_dict.keys()):
            rewards[key] = r[i]
            obs[key] = {
                "obs": np.array(o[i])
            }
        dones = {"__all__": d}
        return obs, rewards, dones, {}
    
    def close(self):
        self.env.close()

    # no render method, you cannot render this env

    def get_env_info(self):
        env_info = {
            "space_obs": self.observation_space,
            "space_act": self.action_space,
            "num_agents": self.num_agents,
            "episode_limit": 100,
            "policy_mapping_info": policy_mapping_dict
        }
        return env_info

if __name__ == '__main__':
    ENV_REGISTRY["CityLearnGym"] = RLlibCityLearnGym

    env = marl.make_env(environment_name="CityLearnGym", map_name="CityLearn")
    # print(env[0].observation_space)
    # env = StableBaselines3Wrapper(env)
    # env[0] = NormalizedObservationWrapper(env[0])
    mappo = marl.algos.mappo(hyperparam_source="test")
    model = marl.build_model(env, mappo, {"core_arch": "mlp", "encode_layer": "128-128"})
    mappo.fit(env, model, stop={'episode_reward_mean': 2000, 'timesteps_total': 10000000}, local_mode=True, num_gpus=1,
              num_workers=2, share_policy='all', checkpoint_freq=50)