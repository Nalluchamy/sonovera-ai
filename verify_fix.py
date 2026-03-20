import transformers.pytorch_utils
def isin_mps_friendly(elements, tensor):
    import torch
    return torch.isin(elements, tensor)
transformers.pytorch_utils.isin_mps_friendly = isin_mps_friendly
from TTS.api import TTS
print('Import successful')
