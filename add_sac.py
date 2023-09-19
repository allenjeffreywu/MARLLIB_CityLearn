from ray.rllib.utils.framework import try_import_torch
from ray.rllib.agents.sac.sac_torch_policy import SACTorchPolicy
from ray.rllib.agents.sac.sac import DEFAULT_CONFIG as SAC_CONFIG, SACTrainer
from ray import tune
from ray.tune.utils import merge_dicts
from ray.tune import CLIReporter
from ray.rllib.models import ModelCatalog
from marllib.marl.algos.utils.log_dir_util import available_local_dir
from marllib.marl.algos.utils.setup_utils import AlgVar
from marllib import marl
import json

from marllib.envs.base_env import ENV_REGISTRY
from add_citylearn_env import RLlibCityLearnGym


torch, nn = try_import_torch()

###########
### SAC ###
###########

SACTorchPolicy = SACTorchPolicy.with_updates(
    name="SACTorchPolicy",
    get_default_config=lambda: SAC_CONFIG,
)

def get_policy_class_sac(config_):
    if config_["framework"] == "torch":
        return SACTorchPolicy
    
# SACTrainer = SACTrainer.with_updates(
#     name="SACTrainer",
#     default_policy=None,
#     get_policy_class=get_policy_class_sac,
# )

def run_sac(model_class, config_dict, common_config, env_dict, stop, restore):
    ModelCatalog.register_custom_model(
        "Base_Model", model_class)

    _param = AlgVar(config_dict)

    train_batch_size = _param["batch_episode"] * env_dict["episode_limit"]
    if "fixed_batch_timesteps" in config_dict:
        train_batch_size = config_dict["fixed_batch_timesteps"]
    episode_limit = env_dict["episode_limit"]

    batch_mode = _param["batch_mode"]
    lr = _param["lr"]

    config = {
        "train_batch_size": train_batch_size,
        "batch_mode": batch_mode,
        "lr": lr if restore is None else 1e-10,
        "model": {
            "custom_model": "Base_Model",
            "max_seq_len": episode_limit,
            "custom_model_config": merge_dicts(config_dict, env_dict),
        },
    }

    config.update(common_config)

    algorithm = config_dict["algorithm"]
    map_name = config_dict["env_args"]["map_name"]
    arch = config_dict["model_arch_args"]["core_arch"]
    RUNNING_NAME = '_'.join([algorithm, arch, map_name])

    if restore is not None:
        with open(restore["params_path"], 'r') as JSON:
            raw_config = json.load(JSON)
            raw_config = raw_config["model"]["custom_model_config"]['model_arch_args']
            check_config = config["model"]["custom_model_config"]['model_arch_args']
            if check_config != raw_config:
                raise ValueError("is not using the params required by the checkpoint model")
        model_path = restore["model_path"]
    else:
        model_path = None

    results = tune.run(SACTrainer,
                       name=RUNNING_NAME,
                       checkpoint_at_end=config_dict['chesckpoint_end'],
                       checkpoint_freq=config_dict['checkpoint_freq'],
                       restore=model_path,
                       stop=stop,
                       config=config,
                       verbose=1,
                       progress_reporter=CLIReporter(),
                       local_dir=available_local_dir if config_dict["local_dir"] == "" else config_dict["local_dir"])

    return results

if __name__ == '__main__':
    ENV_REGISTRY["CityLearnGym"] = RLlibCityLearnGym

    env = marl.make_env(environment_name="CityLearnGym", map_name="CityLearn")
    # register new algorithm
    marl.algos.register_algo(algo_name="sac", style="cc", script=run_sac)

    # initialize algorithm
    sac = marl.algos.sac(hyperparam_source="test")

    # build agent model based on env + algorithms + user preference if checked available
    model = marl.build_model(env, sac, {"core_arch": "mlp", "encode_layer": "128-128"})

    # start learning + extra experiment settings if needed. remember to check ray.yaml before use
    sac.fit(env, model, stop={'timesteps_total': 8759}, local_mode=True, num_gpus=1,
             num_workers=2, share_policy='all', checkpoint_freq=500)


    # # choose environment + scenario
    # env = marl.make_env(environment_name="mpe", map_name="simple_spread", force_coop=True)

    # # register new algorithm
    # marl.algos.register_algo(algo_name="sac", style="cc", script=run_sac)

    # # initialize algorithm
    # sac = marl.algos.sac(hyperparam_source="mpe")

    # # build agent model based on env + algorithms + user preference if checked available
    # model = marl.build_model(env, sac, {"core_arch": "mlp", "encode_layer": "128-256"})

    # # start learning + extra experiment settings if needed. remember to check ray.yaml before use
    # sac.fit(env, model, stop={'timesteps_total': 8759}, local_mode=True, num_gpus=1,
    #          num_workers=0, share_policy='all', checkpoint_freq=10)