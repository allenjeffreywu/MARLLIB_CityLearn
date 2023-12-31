# MIT License

# Copyright (c) 2023 Replicable-MARL

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

from ray.rllib.utils.framework import try_import_torch
from marllib.marl.models.zoo.mixer import QMixer, VDNMixer
from marllib.marl.models.zoo.rnn.base_rnn import BaseRNN

torch, nn = try_import_torch()


class ValueDecompRNN(BaseRNN):

    def __init__(
            self,
            obs_space,
            action_space,
            num_outputs,
            model_config,
            name,
            **kwargs,
    ):
        super().__init__(obs_space, action_space, num_outputs, model_config,
                         name, **kwargs)

        # mixer:
        if self.custom_config["global_state_flag"]:
            state_dim = self.custom_config["space_obs"]["state"].shape
        else:
            state_dim = self.custom_config["space_obs"]["obs"].shape + (self.custom_config["num_agents"], )
        if self.custom_config["algo_args"]["mixer"] == "qmix":
            self.mixer = QMixer(self.custom_config, state_dim)
        elif self.custom_config["algo_args"]["mixer"] == "vdn":
            self.mixer = VDNMixer()
        else:
            raise ValueError("Unknown mixer type {}".format(self.custom_config["algo_args"]["mixer"]))

    def mixing_value(self, all_agents_vf, state):
        # compatiable with rllib qmix mixer
        all_agents_vf = all_agents_vf.view(-1, 1, self.n_agents)
        v_tot = self.mixer(all_agents_vf, state)

        # shape to [B]
        return v_tot.flatten(start_dim=0)
