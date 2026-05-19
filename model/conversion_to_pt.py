import torch
from safetensors.torch import load_file

input_file = "./model/checkpoints/best/discriminator.safetensors"
output_file = "./model/checkpoints/best/discriminator.pt"

state_dict = load_file(input_file)

torch.save(state_dict, output_file)

print(f"Successfully converted {input_file} to {output_file}")
