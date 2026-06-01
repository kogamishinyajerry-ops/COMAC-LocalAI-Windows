# merge_official.py — use gguf library for correct GGUF merging
# pip install gguf
# python merge_official.py shard1.gguf shard2.gguf output.gguf

import sys, os, struct
from gguf import GGUFReader, GGUFWriter
from gguf.constants import Keys, GGMLQuantizationType

def merge_shards(shard_files, output_path):
    """Merge multiple GGUF shards into one file using gguf library."""
    
    readers = []
    all_tensors = []
    total_tensor_count = 0
    
    # Read all shards
    for i, path in enumerate(shard_files):
        print(f"Reading shard {i+1}: {path} ({os.path.getsize(path) / (1024**3):.1f} GB)")
        reader = GGUFReader(path)
        readers.append(reader)
        
        tensor_count = len(reader.tensors)
        total_tensor_count += tensor_count
        print(f"  {tensor_count} tensors")
        
        # Collect tensor names and data
        for name, tensor in reader.tensors.items():
            all_tensors.append((name, tensor))
            print(f"    {name}: shape={tensor.shape}, type={tensor.tensor_type.name}")
    
    if not readers:
        print("ERROR: no shards to merge")
        return False
    
    # Use first shard's metadata as base
    base = readers[0]
    
    # Create writer
    writer = GGUFWriter(output_path, base.arch)
    
    # Copy all KV metadata from first shard (except split keys)
    for key in base.fields:
        if key.startswith("split."):
            continue
        
        field = base.fields[key]
        val = field.parts[field.data[0]]
        
        # Skip tensor-specific metadata (will be auto-generated)
        if key.startswith("tokenizer.ggml.") or key.startswith("general."):
            try:
                # Try to add the field
                if isinstance(val, list):
                    if len(val) == 0:
                        continue
                    if isinstance(val[0], str):
                        writer.add_string_list(key, val)
                    elif isinstance(val[0], float):
                        writer.add_float32_list(key, val)
                elif isinstance(val, str):
                    writer.add_string(key, val)
                elif isinstance(val, int):
                    writer.add_uint32(key, val)
                elif isinstance(val, float):
                    writer.add_float32(key, val)
                elif isinstance(val, bool):
                    writer.add_bool(key, val)
            except Exception as e:
                print(f"  Skipping key {key}: {e}")
    
    # Write all tensors
    print(f"\nWriting {total_tensor_count} tensors...")
    for name, tensor in all_tensors:
        data = tensor.data
        # Handle numpy array
        if hasattr(data, 'nbytes'):
            writer.add_tensor(name, data, raw_dtype=tensor.tensor_type)
        else:
            writer.add_tensor(name, data, raw_dtype=tensor.tensor_type)
    
    print(f"Writing {output_path}...")
    writer.write_all_to_file()
    
    print(f"Done! {os.path.getsize(output_path) / (1024**3):.2f} GB")
    return True

if __name__ == "__main__":
    # Find shard files
    import glob as g
    patterns = [
        "ollama-models/qwen3-4b-instruct-q4_k_m-*-of-*.gguf",
        "qwen3-4b-instruct-q4_k_m-*-of-*.gguf",
    ]
    shards = []
    for p in patterns:
        shards = sorted(g.glob(p))
        if len(shards) >= 2:
            break
    
    if len(shards) < 2:
        print("ERROR: Need 2+ shard files")
        print("Usage: python merge_official.py shard1.gguf shard2.gguf output.gguf")
        exit(1)
    
    output = shards[0].replace("-00001-of-00002", "")
    merge_shards(shards, output)
    print(f"\nModelfile FROM: FROM ./{os.path.basename(output)}")
