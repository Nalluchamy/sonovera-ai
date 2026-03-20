import sys
import types
import importlib

def patch_transformers():
    """
    Monkey patches for compatibility:
    1. Force is_torchcodec_available to False
    2. Patch torchaudio.load/save to use soundfile directly (bypass torchcodec DLL error)
    3. transformers.pytorch_utils.isin_mps_friendly
    """
    import transformers.pytorch_utils
    import torch
    import torchaudio
    import soundfile
    import numpy as np

    # Patch 1: Force False for torchcodec
    try:
        import transformers.utils.import_utils as tu
        if hasattr(tu, "is_torchcodec_available"):
            tu.is_torchcodec_available = lambda: False
            print("Forced is_torchcodec_available to False")
    except Exception:
        pass

    # Patch 2: torchaudio load/save redirection
    def patched_load(uri, frame_offset=0, num_frames=-1, normalize=True, channels_first=True, **kwargs):
        # Fallback to soundfile to avoid torchcodec DLL issues on Windows
        try:
            # soundfile.read handles bytes, paths, etc.
            data, samplerate = soundfile.read(uri, start=frame_offset, stop=None if num_frames == -1 else frame_offset + num_frames)
            
            # Convert to torch tensor
            tensor = torch.from_numpy(data).float()
            
            # Normalize if needed (soundfile already returns float in [-1, 1] range usually)
            # but if it was int, we'd need to normalize. soundfile.read(..., dtype='float32') is better.
            
            # Handle shape [time, channel] -> [channel, time]
            if channels_first:
                if tensor.ndim == 1:
                    tensor = tensor.unsqueeze(0)
                else:
                    tensor = tensor.transpose(0, 1)
            
            return tensor, samplerate
        except Exception as e:
            # Fallback to original if soundfile fails
            print(f"[Patch] soundfile load failed, trying original: {e}")
            return original_load(uri, frame_offset=frame_offset, num_frames=num_frames, normalize=normalize, channels_first=channels_first, **kwargs)

    def patched_save(uri, src, sample_rate, channels_first=True, **kwargs):
        try:
            # src is [channel, time] if channels_first else [time, channel]
            data = src.detach().cpu().numpy()
            if channels_first and data.ndim == 2:
                data = data.transpose(1, 0) # -> [time, channel]
            
            soundfile.write(uri, data, sample_rate)
            return
        except Exception as e:
            print(f"[Patch] soundfile save failed: {e}")
            return original_save(uri, src, sample_rate, channels_first=channels_first, **kwargs)

    if not hasattr(torchaudio, "_patched_by_antigravity"):
        original_load = torchaudio.load
        original_save = torchaudio.save
        torchaudio.load = patched_load
        torchaudio.save = patched_save
        torchaudio._patched_by_antigravity = True
        print("Successfully patched torchaudio.load/save with soundfile fallback")

    # Patch 3: isin_mps_friendly
    if not hasattr(transformers.pytorch_utils, "isin_mps_friendly"):
        def isin_mps_friendly(elements, tensor):
            return torch.isin(elements, tensor)
        transformers.pytorch_utils.isin_mps_friendly = isin_mps_friendly
        print("Successfully applied isin_mps_friendly monkey patch to transformers.pytorch_utils")

if __name__ == "__main__":
    patch_transformers()
