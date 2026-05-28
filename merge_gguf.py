# merge_gguf.py — correctly merge sharded GGUF files
# Usage: python merge_gguf.py
# Place this file next to the two shard files in ollama-models/

import struct, os, glob

def find_shards():
    pattern = "ollama-models/qwen2.5-7b-instruct-q4_k_m-*-of-*.gguf"
    files = sorted(glob.glob(pattern))
    if len(files) < 2:
        pattern2 = "qwen2.5-7b-instruct-q4_k_m-*-of-*.gguf"
        files = sorted(glob.glob(pattern2))
    if len(files) < 2:
        print("ERROR: Could not find sharded GGUF files")
        print("Expected: qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf and -00002-of-00002.gguf")
        exit(1)
    return files

def merge(shard1, shard2, output):
    print(f"Reading {shard1}...")
    with open(shard1, 'rb') as f:
        data1 = f.read()
    print(f"Reading {shard2}...")
    with open(shard2, 'rb') as f:
        data2 = f.read()
    
    # GGUF format: magic(4 bytes 'GGUF') + version(4) + tensor_count(8) + metadata_kv_count(8)
    if data1[:4] != b'GGUF' or data2[:4] != b'GGUF':
        print("ERROR: Not valid GGUF files")
        exit(1)
    
    # Read metadata size from header
    metadata_size1 = struct.unpack_from('<Q', data1, 8)[0]
    header_size1 = 8 + 8 + metadata_size1  # 8(tensor_count + kv_count) + metadata
    
    metadata_size2 = struct.unpack_from('<Q', data2, 8)[0]
    header_size2 = 8 + 8 + metadata_size2
    
    # Merge: keep header from shard1, append tensor data from shard2 (skip its header)
    merged = data1 + data2[header_size2:]
    
    print(f"Writing {output}...")
    with open(output, 'wb') as f:
        f.write(merged)
    
    size_mb = os.path.getsize(output) / (1024*1024)
    print(f"Done: {output} ({size_mb:.0f} MB)")

def main():
    shards = find_shards()
    output = shards[0].replace("-00001-of-00002", "")
    merge(shards[0], shards[1], output)
    print("\nNow update Modelfile FROM line to:")
    print(f"  FROM ./{os.path.basename(output)}")

if __name__ == "__main__":
    main()
