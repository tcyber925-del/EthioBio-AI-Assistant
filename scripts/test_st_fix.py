import torch

# Patch register_fake to handle missing ops
original_register_fake = torch.library.register_fake
def patched_register_fake(name, *args, **kwargs):
    def wrapper(fn):
        try:
            result = original_register_fake(name, *args, **kwargs)
            def inner(*a, **kw):
                try:
                    return fn(*a, **kw)
                except RuntimeError as e:
                    if 'does not exist' in str(e):
                        return None
                    raise
            try:
                result(inner)
            except RuntimeError as e:
                if 'does not exist' in str(e):
                    print(f'Skipped torchvision::nms registration', flush=True)
                else:
                    raise
            return fn
        except RuntimeError as e:
            if 'does not exist' in str(e):
                print(f'Skipped torchvision::nms registration', flush=True)
                return fn
            raise
    return wrapper

torch.library.register_fake = patched_register_fake

import torchvision
print('torchvision imported OK', flush=True)

from sentence_transformers import SentenceTransformer
print('sentence_transformers imported OK', flush=True)

m = SentenceTransformer('all-MiniLM-L6-v2')
print('Model loaded', flush=True)
e = m.encode('test').tolist()
print(f'Embedding dims: {len(e)}', flush=True)
