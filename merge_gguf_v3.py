# merge_gguf_v3.py — GGUF shard merger (patch-in-place approach)
# python merge_gguf_v3.py

import struct, os, glob

def main():
    patterns = [
        "ollama-models/qwen2.5-7b-instruct-q4_k_m-*-of-*.gguf",
        "qwen2.5-7b-instruct-q4_k_m-*-of-*.gguf",
    ]
    shards = []
    for p in patterns:
        shards = sorted(glob.glob(p))
        if shards:
            break
    
    if len(shards) < 2:
        print("ERROR: need at least 2 GGUF shards")
        exit(1)
    
    print(f"Found {len(shards)} shards")
    
    # Read all shards
    datas = []
    offsets = []
    t_counts = []
    
    for i, s in enumerate(shards):
        print(f"  Shard {i+1}: {s} ({os.path.getsize(s) / (1024**3):.1f} GB)")
        with open(s, 'rb') as f:
            d = f.read()
        datas.append(d)
        
        assert d[:4] == b'GGUF', f"Not GGUF: {s}"
        tc = struct.unpack_from('<Q', d, 8)[0]
        kc = struct.unpack_from('<Q', d, 16)[0]
        t_counts.append(tc)
        
        # Find tensor data start (skip KV metadata)
        offset = 24
        val_sizes = {0:1, 1:1, 2:2, 3:2, 4:4, 5:4, 6:4, 7:1, 8:0, 9:0, 10:8, 11:8, 12:8}
        for _ in range(kc):
            k_len = struct.unpack_from('<Q', d, offset)[0]
            offset += 8 + k_len
            v_type = struct.unpack_from('<I', d, offset)[0]
            offset += 4
            if v_type == 8:  # string
                s_len = struct.unpack_from('<Q', d, offset)[0]
                offset += 8 + s_len
            elif v_type == 9:  # array
                a_type = struct.unpack_from('<I', d, offset)[0]
                a_len = struct.unpack_from('<I', d, offset + 4)[0]
                offset += 8
                if a_type == 8:
                    for _ in range(a_len):
                        s_len = struct.unpack_from('<Q', d, offset)[0]
                        offset += 8 + s_len
                else:
                    sz = val_sizes.get(a_type, 4)
                    offset += a_len * sz
            else:
                sz = val_sizes.get(v_type, 4)
                offset += sz
        
        offsets.append(offset)
        print(f"    {tc} tensors, {kc} kv, data at {offset}")
    
    # Build merged: shard0 header + all tensor data
    total_tc = sum(t_counts)
    merged = bytearray(datas[0][:offsets[0]])  # shard0 header
    
    # Patch tensor_count in header
    struct.pack_into('<Q', merged, 8, total_tc)
    
    # Find and zero-out split.* KV entries in the header
    # The header is in merged[0:offsets[0]], we need to find split keys
    pos = 24
    kv_count = struct.unpack_from('<Q', datas[0], 16)[0]
    for _ in range(kv_count):
        k_len = struct.unpack_from('<Q', merged, pos)[0]
        key = bytes(merged[pos+8:pos+8+k_len]).decode('utf-8', errors='replace')
        val_start = pos + 8 + k_len
        v_type = struct.unpack_from('<I', merged, val_start)[0]
        val_data_start = val_start + 4
        
        # Move past this KV
        if v_type == 8:
            s_len = struct.unpack_from('<Q', merged, val_data_start)[0]
            pos = val_data_start + 8 + s_len
        elif v_type == 9:
            a_type = struct.unpack_from('<I', merged, val_data_start)[0]
            a_len = struct.unpack_from('<I', merged, val_data_start + 4)[0]
            end = val_data_start + 8
            if a_type == 8:
                for _ in range(a_len):
                    s_len = struct.unpack_from('<Q', merged, end)[0]
                    end += 8 + s_len
            else:
                end += a_len * val_sizes.get(a_type, 4)
            pos = end
        else:
            pos = val_data_start + val_sizes.get(v_type, 4)
        
        # Zero out split keys (set value to a minimal valid value)
        if key.startswith('split.'):
            print(f"    Removing split metadata: {key}")
            if v_type == 8:  # string - set to empty
                s_offset = val_data_start + 8
                s_len = struct.unpack_from('<Q', merged, val_data_start)[0]
                struct.pack_into('<Q', merged, val_data_start, 0)
                for j in range(s_len):
                    merged[s_offset + j] = 0
            elif v_type == 4:  # uint32 - set to 0
                struct.pack_into('<I', merged, val_data_start, 0)
            elif v_type == 10:  # uint64 - set to 0
                struct.pack_into('<Q', merged, val_data_start, 0)
    
    # Append all tensor data
    merged.extend(datas[0][offsets[0]:])  # shard0 tensors
    for i in range(1, len(datas)):
        merged.extend(datas[i][offsets[i]:])
    
    output = shards[0].replace("-00001-of-00002", "")
    if os.path.exists(output):
        os.remove(output)
    
    print(f"  Writing {output} ({len(merged) / (1024**3):.1f} GB)...")
    with open(output, 'wb') as f:
        f.write(merged)
    
    # Verify
    assert merged[:4] == b'GGUF'
    final_tc = struct.unpack_from('<Q', merged, 8)[0]
    print(f"  Done! {final_tc} tensors total")
    print(f"\n  Modelfile FROM = FROM ./{os.path.basename(output)}")

if __name__ == "__main__":
    main()
