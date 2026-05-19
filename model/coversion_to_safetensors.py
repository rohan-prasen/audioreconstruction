import torch
from safetensors.torch import save_file

state_dict = torch.load("model.pt", map_location="cpu")

save_file(state_dict, "model.safetensors")
