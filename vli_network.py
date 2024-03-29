

from collections import defaultdict
import torch.nn.functional as f

import numpy as np
import torch
from sample_factory.algorithms.appo.model_utils import EncoderBase, \
    ResBlock, nonlinearity, get_obs_shape
from sample_factory.algorithms.utils.pytorch_utils import calc_num_elements
from sample_factory.utils.timing import Timing
from torch import nn


def grid_stucture_encoder(input_channel, block_config, net_config, timing):
    """
    Create a grid structure encoder network.

    Args:
        input_channel (int): Number of input channels.
        block_config (List[Tuple[int, int]]): List of tuples specifying the number of output channels
            and the number of residual blocks for each layer.
        net_config: Configuration for the network.
        timing: Timing information.

    Returns:
        nn.Sequential: A grid structure encoder network.
    """
    layers = []
    for i, (out_channels, res_blocks) in enumerate(block_config):
        layers.extend([
            nn.Conv2d(input_channel, out_channels, kernel_size=3, stride=1, padding=1),  # padding SAME
        ])
        for j in range(res_blocks):
            layers.append(ResBlock(net_config, out_channels, out_channels, timing))
        input_ch_grid = out_channels
    layers.append(nonlinearity(net_config))
    grid_encoder = nn.Sequential(*layers)
    return grid_encoder


class ResnetEncoderWithTarget(EncoderBase):
    """
    ResNet-based encoder network with target input.

    Args:
        cfg: Configuration for the network.
        obs_space: Observation space.
        timing: Timing information.

    Attributes:
        conv_grid (nn.Sequential): Convolutional layers for grid input.
        conv_target (nn.Sequential): Convolutional layers for target input.
        inventory_compass_emb (nn.Sequential): Embedding layers for inventory and compass data.
        conv_target_out_size (int): Output size of target convolutional layers.
        conv_grid_out_size (int): Output size of grid convolutional layers.
    """
    def __init__(self, cfg, obs_space, timing):
        super().__init__(cfg, timing)
        target_shape = get_obs_shape(obs_space['target_grid'])
        input_ch_targ = target_shape.obs[0]
        target_conf = [[64, 3]]

        grid_shape = get_obs_shape(obs_space['grid'])
        input_ch_grid = grid_shape.obs[0]
        grid_conf = [[64, 3]]
        ### Grid embedding
        self.conv_grid = grid_stucture_encoder(input_ch_grid, grid_conf, cfg, self.timing)
        ### Target embedding
        self.conv_target = grid_stucture_encoder(input_ch_targ, target_conf, cfg, self.timing)

        self.inventory_compass_emb = nn.Sequential(
            nn.Linear(11, cfg.hidden_size),
            nn.ReLU(),
            nn.Linear(cfg.hidden_size, cfg.hidden_size),
            nn.ReLU(),
        )

        self.conv_target_out_size = calc_num_elements(self.conv_target, target_shape.obs)
        self.conv_grid_out_size = calc_num_elements(self.conv_grid, grid_shape.obs)
        self.init_fc_blocks(self.conv_target_out_size + self.conv_grid_out_size + cfg.hidden_size)

    def forward(self, obs_dict):
        # values for normalization
        abs_max_obs = np.array([10, 8, 10, 180, 360])  # x, y, z, yaw, pitch
        true_max_obs = np.array([5, 0, 5, 90, 0])  # x, y, z, yaw, pitch
        max_inventory_val = 20

        abs_max_obs = torch.from_numpy(abs_max_obs).cuda()
        true_max_obs = torch.from_numpy(true_max_obs).cuda()

        inventory_compass = torch.cat(
            [obs_dict['inventory'] / max_inventory_val, (obs_dict['agentPos'] + true_max_obs) / abs_max_obs], -1)
        inv_comp_emb = self.inventory_compass_emb(inventory_compass)

        target = torch.zeros_like((obs_dict['target_grid']))
        target[obs_dict['target_grid'] > 0] = 1  # put 1 if task is build block
        target[obs_dict['target_grid'] < 0] = -1  # put -1 if task is remove block

        tg = self.conv_target(target)
        tg_embed = tg.contiguous().view(-1, self.conv_target_out_size)

        grid = torch.zeros_like((obs_dict['grid']))
        grid[obs_dict['grid'] != 0] = 1  # put 1 on blocks place (make blocks same color)

        grid = self.conv_grid(grid) - 0.5
        grid_embed = grid.contiguous().view(-1, self.conv_grid_out_size)

        head_input = torch.cat([inv_comp_emb, tg_embed, grid_embed], -1)

        x = self.forward_fc_blocks(head_input)
        return x


def main():
    def validate_config(config):
        exp = Experiment(**config)
        flat_config = Namespace(**exp.async_ppo.dict(),
                                **exp.experiment_settings.dict(),
                                **exp.global_settings.dict(),
                                **exp.evaluation.dict(),
                                full_config=exp.dict()
                                )
        return exp, flat_config

    from argparse import Namespace
    from utils.config_validation import Experiment
    from utils.create_env import make_iglu

    exp = Experiment()
    exp, flat_config = validate_config(exp.dict())
    flat_config.hidden_size = 512
    env = make_iglu()
    encoder = ResnetEncoderWithTarget(flat_config, env.observation_space, Timing())

    obs = env.reset()
    counter = defaultdict(set)
    for _ in range(10000):
        for idx, x in enumerate(list(np.round(obs[0]['agentPos'], 0))):
            counter[idx].add(int(x))

        obs, reward, done, info = env.step([env.action_space.sample()])
    obs = obs[0]

    obs['agentPos'] = torch.Tensor(obs['agentPos'])[None]
    obs['inventory'] = torch.Tensor(obs['inventory'])[None]
    obs['target_grid'] = torch.Tensor(obs['target_grid'])[None]
    obs['obs'] = torch.Tensor(obs['obs'])[None]


if __name__ == '__main__':
    main()

def grid_stucture_encoder(input_channel, block_config, net_config, timing):
    layers = []
    for i, (out_channels, res_blocks) in enumerate(block_config):
        layers.extend([
            nn.Conv2d(input_channel, out_channels, kernel_size=3, stride=1, padding=1),  # padding SAME
        ])
        for j in range(res_blocks):
            layers.append(ResBlock(net_config, out_channels, out_channels, timing))
        input_ch_grid = out_channels
    layers.append(nonlinearity(net_config))
    grid_encoder = nn.Sequential(*layers)
    return grid_encoder

!pip install sample-factory

!pip install -U sentence-transformers

from collections import defaultdict

import numpy as np
import torch
from sample_factory.algorithms.appo.model_utils import EncoderBase, \
    ResBlock, nonlinearity, get_obs_shape
from sample_factory.algorithms.utils.pytorch_utils import calc_num_elements
from sample_factory.utils.timing import Timing
from torch import nn
from sentence_transformers import SentenceTransformer

class image_encoder(nn.Module):
    """
    Image encoder module.

    Args:
        obs_space: Observation space.
        cfg: Configuration for the network.
        timing: Timing information.

    Attributes:
        conv_grid (nn.Sequential): Convolutional layers for grid input.
        conv_grid_out_size (int): Output size of grid convolutional layers.
    """
    def __init__(self, obs_space,cfg,timing):
        super(image_encoder,self).__init__()
        self.timing = timing
        grid_shape = get_obs_shape(obs_space['grid'])
        input_ch_grid = grid_shape.obs[0]
        grid_conf = [[64, 3]]
        ### Grid embedding
        self.conv_grid = grid_stucture_encoder(input_ch_grid, grid_conf, cfg, self.timing)
        self.conv_grid_out_size = calc_num_elements(self.conv_grid, grid_shape.obs)

    def forward(self, obs_dict):
        grid = torch.zeros_like((obs_dict['grid']))
        grid[obs_dict['grid'] != 0] = 1  # put 1 on blocks place (make blocks same color)

        grid = self.conv_grid(grid) - 0.5
        grid_embed = grid.contiguous().view(-1, self.conv_grid_out_size)

        return grid_embed

from PIL import Image

from torchvision import datasets, transforms

class cfg:
  nonlinearity = 'relu'
cfg = cfg()

pip install git+https://github.com/iglu-contest/gridworld.git@master

!export IGLU_HEADLESS=0

import gym
import gridworld
from gridworld.data import IGLUDataset

dataset = IGLUDataset(dataset_version='v0.1.0-rc1')

from gridworld.tasks import DUMMY_TASK

dir(dataset.tasks['c73'][1])

#chat,full_grid,last_instruction,starting_grid

obs={'grid' : torch.FloatTensor(dataset.tasks['c73'][1].starting_grid).view(4,4,1),'string':dataset.tasks['c73'][1].last_instruction}

im = image_encoder(obs,cfg,Timing())

k = im(obs)

k.shape

k.transpose(1,0).shape

class language_encoder(nn.Module):
    """
    Language encoder module that uses Sentence Transformers for encoding text.

    Args:
        None

    Attributes:
        model: Sentence Transformers model for text encoding.

    Methods:
        forward(obs_dict):
            Forward pass to encode text observations.

    Returns:
        torch.Tensor: Embeddings of the input text.

    Example:
        lang = LanguageEncoder()
        embeddings = lang({'string': 'This is an example sentence.'})
    """
  def __init__(self):
      super().__init__()

      self.model = SentenceTransformer("johngiorgi/declutr-small")
    
  def forward(self,obs_dict):
      texts = [obs_dict['string']]

      embeddings = self.model.encode(texts)
      return embeddings

lang= language_encoder()
p = lang({'string': 'hey fuck u mother fucker bitch fk'})

p.shape

class other_stuff_encoder(nn.Module):
    """
    Encoder module for processing miscellaneous non-image and non-textual observations.

    Args:
        None

    Attributes:
        inventory_compass_emb (nn.Sequential): Sequential layers for encoding inventory and compass data.

    Methods:
        forward(obs_dict):
            Forward pass to encode miscellaneous observations.

    Returns:
        torch.Tensor: Embeddings of the miscellaneous observations.

    Example:
        other_enc = OtherStuffEncoder()
        embeddings = other_enc({'inventory': torch.randn(11), 'agentPos': torch.randn(5)})
    """
    def __init__(self):
        super(other_stuff_encoder,self).__init__()
        self.inventory_compass_emb = nn.Sequential(
            nn.Linear(11, cfg.hidden_size),
            nn.ReLU(),
            nn.Linear(cfg.hidden_size, cfg.hidden_size),
            nn.ReLU(),
        )

    def forward(self, obs_dict):
        # values for normalization
        abs_max_obs = np.array([10, 8, 10, 180, 360])  # x, y, z, yaw, pitch
        true_max_obs = np.array([5, 0, 5, 90, 0])  # x, y, z, yaw, pitch
        max_inventory_val = 20

        abs_max_obs = torch.from_numpy(abs_max_obs).cuda()
        true_max_obs = torch.from_numpy(true_max_obs).cuda()

        inventory_compass = torch.cat(
            [obs_dict['inventory'] / max_inventory_val, (obs_dict['agentPos'] + true_max_obs) / abs_max_obs], -1)
        inv_comp_emb = self.inventory_compass_emb(inventory_compass)

        return inv_comp_emb

import torch as Tensor

def scaled_dot_product_attention(query: Tensor, key: Tensor, value: Tensor) -> Tensor:
    temp = query.bmm(key.transpose(1, 2))
    scale = query.size(-1) ** 0.5
    softmax = f.softmax(temp / scale, dim=-1)
    return softmax.bmm(value)


class AttentionHead(nn.Module):
    def __init__(self, dim_in: int, dim_q: int, dim_k: int):
        super().__init__()
        self.q = nn.Linear(dim_in, dim_q)
        self.k = nn.Linear(dim_in, dim_k)
        self.v = nn.Linear(dim_in, dim_k)

    def forward(self, query: Tensor, key: Tensor, value: Tensor) -> Tensor:
        return scaled_dot_product_attention(self.q(query), self.k(key), self.v(value))


class MultiHeadAttention(nn.Module):
    def __init__(self, num_heads: int, dim_in: int, dim_q: int, dim_k: int):
        super().__init__()
        self.heads = nn.ModuleList(
            [AttentionHead(dim_in, dim_q, dim_k) for _ in range(num_heads)]
        )
        self.linear = nn.Linear(num_heads * dim_k, dim_in)

    def forward(self, query: Tensor, key: Tensor, value: Tensor) -> Tensor:
        return self.linear(
            torch.cat([h(query, key, value) for h in self.heads], dim=-1)
        )

class Residual(nn.Module):
    def __init__(self, sublayer: nn.Module, dimension: int, dropout: float = 0.1):
        super().__init__()
        self.sublayer = sublayer
        self.norm = nn.LayerNorm(dimension)
        self.dropout = nn.Dropout(dropout)

    def forward(self, *tensors: Tensor) -> Tensor:
        # Assume that the "query" tensor is given first, so we can compute the
        # residual.  This matches the signature of 'MultiHeadAttention'.
        return self.norm(tensors[0] + self.dropout(self.sublayer(*tensors)))

class attention_Layer(nn.Module):
    def __init__(
        self,
        dim_model: int = 256,
        num_heads: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()
        dim_q = dim_k = max(dim_model // num_heads, 1)
        self.attention = Residual(
            MultiHeadAttention(num_heads, dim_model, dim_q, dim_k),
            dimension=dim_model,
            dropout=dropout,
        )

    def forward(self, q: Tensor,k:Tensor,v:Tensor) -> Tensor:
        src = self.attention(q, k, v)
        return src



!pip install htm-pytorch
import torch
from htm_pytorch import HTMBlock

memories = torch.randn(1, 200, 256)

class whole_net(nn.Module):
    """
    Whole network architecture for processing multi-modal inputs.

    Args:
        None

    Attributes:
        image_encoder (image_encoder): Instance of the image encoder.
        language_encoder (language_encoder): Instance of the language encoder.
        lang_q (nn.Linear): Linear layer for language query projection.
        hcam (HTMBlock): Hierarchical Contextual Attention Memory (HCAM) block.
        cross_attention1 (attention_Layer): Cross-attention layer 1.
        cross_attention2 (attention_Layer): Cross-attention layer 2.
        _output (torch.Tensor): Intermediate output tensor.

    Methods:
        forward(inputs, memories):
            Forward pass to process multi-modal inputs and produce an output tensor.

    Returns:
        torch.Tensor: The output tensor of the network.

    Example:
        net = WholeNet()
        output = net({'string': 'sample text'}, torch.randn(1, 200, 256))
    """
  def __init__(self):
    super(whole_net,self).__init__()
    self.image_encoder = image_encoder(obs,cfg,Timing())
    self.language_encoder = language_encoder()
    self.lang_q = nn.Linear(768,256)
    #self.other_stuff_encoder = other_stuff_encoder()
    self.hcam = HTMBlock(
    dim = 256,
    heads = 4, 
    topk_mems = 4,
    mem_chunk_size = 32
    )
    self.cross_attention1 =  attention_Layer()
    self.cross_attention2 = attention_Layer()
    #self.mlp = nn.linear(self.hidden_state,self.output)
    self._output = None

  def forward(self,
              inputs,
              memories):
    self._lang_emb = self.language_encoder(inputs)
    self._imag_emb = self.image_encoder(inputs)
    #self._other_emb = self.other_stuff_encoder(inputs)
    print(self.lang_q( torch.from_numpy(self._lang_emb)).shape)
    print(self._imag_emb.shape)

    self._output = self.cross_attention1(self.lang_q( torch.from_numpy(self._lang_emb)).unsqueeze(0),self._imag_emb.unsqueeze(0),self._imag_emb.unsqueeze(0))
    self._output = self.hcam(self._output,memories)
    print(self._output.shape)
    #self._output = self.cross_attention2(self._output,self._other_emb,self._other_emb)
    #self._output = self.mlp(self._output)
    return self._output

n = whole_net()
f = n(obs,memories)





