# merge_gguf_v4.py — robust GGUF merger with defensive header parsing
# python merge_gguf_v4.py

import struct, os, glob

def find_header_end(data):
    """Find where GGUF header ends and tensor data begins.
    Returns offset, or raises if parsing fails."""
    assert data[:4] == b'GGUF', "Not GGUF"
    
    version = struct.unpack_from('<I', data, 4)[0]
    tensor_count = struct.unpack_from('<Q', data, 8)[0]
    kv_count = struct.unpack_from('<Q', data, 16)[0]
    
    pos = 24
    end = len(data)
    val_sizes = {0:1, 1:1, 2:2, 3:2, 4:4, 5:4, 6:4, 7:1, 10:8, 11:8, 12:8, 13:1}
    
    for i in range(kv_count):
        if pos + 8 > end:
            raise ValueError(f"KV {i}: key_len read at {pos} exceeds file size {end}")
        
        key_len = struct.unpack_from('<Q', data, pos)[0]
        pos += 8
        
        if pos + key_len > end:
            raise ValueError(f"KV {i}: key data exceeds file size")
        
        key = data[pos:pos + key_len].decode('utf-8', errors='replace')
        pos += key_len
        
        if pos + 4 > end:
            raise ValueError(f"KV {i}: val_type exceeds file size")
        
        val_type = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        
        if val_type == 8:  # string
            if pos + 8 > end:
                raise ValueError(f"KV {i} ({key}): string_len exceeds file size")
            s_len = struct.unpack_from('<Q', data, pos)[0]
            pos += 8 + s_len
            
        elif val_type == 9:  # array
            if pos + 8 > end:
                raise ValueError(f"KV {i} ({key}): array header exceeds file size")
            arr_type = struct.unpack_from('<I', data, pos)[0]
            arr_count = struct.unpack_from('<Q', data, pos + 4)[0]
            pos += 12
            
            if arr_type == 8:  # array of strings
                for j in range(arr_count):
                    if pos + 8 > end:
                        raise ValueError(f"KV {i} ({key}): string[{j}] len exceeds file")
                    s_len = struct.unpack_from('<Q', data, pos)[0]
                    pos += 8 + s_len
            else:
                item_sz = val_sizes.get(arr_type, 4)
                pos += arr_count * item_sz
                
        else:
            sz = val_sizes.get(val_type, 4)
            pos += sz
        
        if pos > end:
            raise ValueError(f"KV {i} ({key}): overflow at pos {pos} > {end}")
    
    return pos, tensor_count, kv_count

def main():
    patterns = [
        "ollama-models/qwen3-4b-instruct-q4_k_m-*-of-*.gguf",
        "qwen3-4b-instruct-q4_k_m-*-of-*.gguf",
    ]
    shards = []
    for p in patterns:
        shards = sorted(glob.glob(p))
        if shards:
            break
    
    if len(shards) < 2:
        print("ERROR: need 2+ shards")
        exit(1)
    
    datas = []
    offsets = []
    tcs = []
    
    for i, s in enumerate(shards):
        size_gb = os.path.getsize(s) / (1024**3)
        print(f"Shard {i+1}: {s} ({size_gb:.2f} GB)")
        with open(s, 'rb') as f:
            d = f.read()
        datas.append(d)
        
        try:
            off, tc, kc = find_header_end(d)
            offsets.append(off)
            tcs.append(tc)
            print(f"  {kc} KV pairs, {tc} tensors, header={off} bytes, data={len(d)-off} bytes")
        except ValueError as e:
            print(f"  PARSE ERROR in shard {i+1}: {e}")
            print(f"  This shard may be corrupted. Try re-downloading.")
            exit(1)
    
    # Build merged file
    output = shards[0].replace("-00001-of-00002", "")
    if os.path.exists(output):
        os.remove(output)
    
    # Copy shard0 header
    merged = bytearray(datas[0][:offsets[0]])
    
    # Patch tensor count
    total_tc = sum(tcs)
    struct.pack_into('<Q', merged, 8, total_tc)
    
    # Zero out split metadata in header
    pos = 24
    kc = struct.unpack_from('<Q', datas[0], 16)[0]
    vs = {0:1, 1:1, 2:2, 3:2, 4:4, 5:4, 6:4, 7:1, 10:8, 11:8, 12:8, 13:1}
    
    for _ in range(kc):
        kl = struct.unpack_from('<Q', merged, pos)[0]
        key = bytes(merged[pos+8:pos+8+kl]).decode('utf-8', errors='replace')
        vp = pos + 8 + kl
        vt = struct.unpack_from('<I', merged, vp)[0]
        
        if vt == 8:  # string
            sl = struct.unpack_from('<Q', merged, vp+4)[0]
            nxt = vp + 4 + 8 + sl
        elif vt == 9:  # array
            at = struct.unpack_from('<I', merged, vp+4)[0]
            ac = struct.unpack_from('<Q', merged, vp+8)[0]
            nxt = vp + 4 + 12
            if at == 8:
                for _ in range(ac):
                    sl = struct.unpack_from('<Q', merged, nxt)[0]
                    nxt += 8 + sl
            else:
                nxt += ac * vs.get(at, 4)
        else:
            nxt = vp + 4 + vs.get(vt, 4)
        
        if key.startswith('split.'):
            print(f"  Stripping {key}")
            if vt == 4:
                struct.pack_into('<I', merged, vp+4, 0)
            elif vt == 8:
                struct.pack_into('<Q', merged, vp+4, 0)
        
        pos = nxt
    
    # Append tensor data
    # Append tensor data with 32-byte alignment between shards
    ALIGN = 32
    merged.extend(datas[0][offsets[0]:])
    
    for i in range(1, len(datas)):
        # Pad to 32-byte alignment before appending next shard's tensors
        pos = len(merged)
        pad = (ALIGN - (pos % ALIGN)) % ALIGN
        if pad:
            merged.extend(b'\x00' * pad)
        merged.extend(datas[i][offsets[i]:])
    
    print(f"  Writing {output} ({len(merged) / (1024**3):.2f} GB)...")
    with open(output, 'wb') as f:
        f.write(merged)
    
    assert bytes(merged[:4]) == b'GGUF'
    print(f"  Done! Tensors: {total_tc}, Size: {len(merged)} bytes")
    print(f"  Modelfile: FROM ./{os.path.basename(output)}")

if __name__ == "__main__":
    main()
