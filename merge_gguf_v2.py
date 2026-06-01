# merge_gguf_v2.py — proper GGUF shard merger
# python merge_gguf_v2.py

import struct, os, glob

def parse_gguf_header(data):
    """Parse GGUF header, return (data_start_offset, tensor_count, kv_count)"""
    if data[:4] != b'GGUF':
        raise ValueError("Not a GGUF file")
    
    version = struct.unpack_from('<I', data, 4)[0]
    tensor_count = struct.unpack_from('<Q', data, 8)[0]
    kv_count = struct.unpack_from('<Q', data, 16)[0]
    
    # Metadata starts at offset 24 (4+4+8+8)
    offset = 24
    for _ in range(kv_count):
        # Read key (string: uint64 length + bytes)
        key_len = struct.unpack_from('<Q', data, offset)[0]
        offset += 8 + key_len
        # Read value type (uint32)
        val_type = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        # Skip value based on type
        if val_type in (0, 1, 4, 5, 6, 7, 8, 9, 10, 11, 12):  # uint8/16/32/64/int8/16/32/64/float32/64/bool/string
            if val_type == 8:  # string
                s_len = struct.unpack_from('<Q', data, offset)[0]
                offset += 8 + s_len
            elif val_type == 12:  # array
                arr_type = struct.unpack_from('<I', data, offset)[0]
                arr_len = struct.unpack_from('<I', data, offset + 4)[0]
                offset += 8
                for _ in range(arr_len):
                    if arr_type == 8:  # string array
                        s_len = struct.unpack_from('<Q', data, offset)[0]
                        offset += 8 + s_len
                    else:
                        offset += {0:1, 1:2, 4:4, 5:2, 6:4, 7:8, 9:2, 10:4, 11:8, 13:1}.get(arr_type, 4)
            else:
                offset += {0:1, 1:2, 4:4, 5:2, 6:4, 7:8, 9:2, 10:4, 11:8, 13:1}.get(val_type, 4)
    
    return offset, tensor_count, kv_count

def find_shards():
    patterns = [
        "ollama-models/qwen3-4b-instruct-q4_k_m-*-of-*.gguf",
        "qwen3-4b-instruct-q4_k_m-*-of-*.gguf",
    ]
    for p in patterns:
        files = sorted(glob.glob(p))
        if len(files) >= 2:
            return files
    print("ERROR: sharded GGUF files not found")
    exit(1)

def main():
    shards = find_shards()
    print(f"Found {len(shards)} shards:")
    for s in shards:
        print(f"  {s} ({os.path.getsize(s) / (1024**3):.1f} GB)")
    
    # Read all shards
    datas = []
    headers = []
    total_tensors = 0
    
    for s in shards:
        print(f"Reading {s}...")
        with open(s, 'rb') as f:
            d = f.read()
        datas.append(d)
        offset, tc, kc = parse_gguf_header(d)
        headers.append(offset)
        total_tensors += tc
        print(f"  -> {tc} tensors, header at offset {offset}")
    
    # Build merged file
    # Use shard 0's header but with updated tensor_count
    output = shards[0].replace("-00001-of-00002", "")
    
    merged = bytearray(datas[0])
    # Update tensor_count in header (offset 8, uint64)
    struct.pack_into('<Q', merged, 8, total_tensors)
    
    # Append tensor data from remaining shards
    for i in range(1, len(datas)):
        merged.extend(datas[i][headers[i]:])
    
    print(f"Writing {output} ({len(merged) / (1024**3):.1f} GB)...")
    with open(output, 'wb') as f:
        f.write(merged)
    
    print(f"Done! Total tensors: {total_tensors}")
    print(f"Modelfile FROM should be: FROM ./{os.path.basename(output)}")

if __name__ == "__main__":
    main()
