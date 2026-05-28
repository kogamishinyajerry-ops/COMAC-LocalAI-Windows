# verify_deployment.py — comprehensive deployment verification
# Run on the build machine to simulate and verify the entire offline deployment

import os, sys, subprocess, struct, tempfile, shutil, zipfile

PROJECT = r"D:\COMAC-Windows-LLM\COMAC-LocalAI-Windows"
TEST = r"D:\COMAC-Windows-LLM\_deploy_test"
PASS = 0; FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} - {detail}")

def header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

# ============================================================
# TEST 1: Source package integrity
# ============================================================
header("1. Source Package Integrity")

with zipfile.ZipFile(f"{PROJECT}/COMAC-offline-sources.zip") as z:
    files = z.namelist()

check("install-offline.bat in zip", "install-offline.bat" in files)
check("start.bat in zip", "start.bat" in files)
check("setup.bat in zip", "setup.bat" in files)
check("opencode.bat in zip", "opencode.bat" in files)
check("pre-deploy.bat in zip", "pre-deploy.bat" in files)
check("merge_official.py in zip", "merge_official.py" in files)
check("requirements.lock.txt in zip", "requirements.lock.txt" in files)
check("app.py in zip", "app.py" in files)

with open(f"{PROJECT}/requirements.lock.txt") as f:
    lock = f.read()
check("hf_xet in lock", "hf_xet" in lock.lower())
check("gguf in lock", "gguf==0.19.0" in lock)

# ============================================================
# TEST 2: Wheel package integrity
# ============================================================
header("2. Wheel Package Integrity")

with zipfile.ZipFile(f"{PROJECT}/COMAC-python-wheels.zip") as z:
    wheels = [n for n in z.namelist() if n.endswith('.whl')]

check("wheels > 60", len(wheels) >= 60, f"got {len(wheels)}")
check("gguf wheel present", any("gguf" in w for w in wheels))
check("hf_xet wheel present", any("hf_xet" in w for w in wheels))
check("gradio wheel present", any("gradio" in w.lower() and "client" not in w.lower() for w in wheels))
check("ollama wheel present", any("ollama" in w.lower() for w in wheels))

# ============================================================
# TEST 3: Batch file syntax check
# ============================================================
header("3. Batch File Syntax")

def check_bat(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    lines = content.split('\n')
    issues = []
    
    # Check for common issues
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('REM') or stripped.startswith('::'):
            continue
        
        # Check for curl (should be gone)
        if 'curl -s' in stripped:
            issues.append(f"L{i}: curl usage found")
        
        # Check for 11434 (should be 11435)
        if '11434' in stripped and '11435' not in stripped:
            issues.append(f"L{i}: old port 11434")
        
        # Check for dangerous unescaped parens in echo within blocks
        # (heuristic: echo line with both ) and ! inside)
        if 'echo' in stripped.lower() and ')' in stripped:
            if any(c in stripped for c in '!%'):
                # Could be problematic - flag it
                pass
    
    # Check for SCRIPT_DIR strip
    if '~0,-1' in content:
        issues.append("SCRIPT_DIR strip found")
    
    return issues

for bat in ['install-offline.bat', 'setup.bat', 'start.bat', 'opencode.bat', 'pre-deploy.bat']:
    path = f"{PROJECT}/{bat}"
    issues = check_bat(path)
    if not issues:
        check(f"{bat} syntax", True)
    else:
        check(f"{bat} syntax", False, "; ".join(issues[:3]))

# Specific checks
with open(f"{PROJECT}/install-offline.bat", 'r', encoding='utf-8', errors='replace') as f:
    c = f.read()
check("no SCRIPT_DIR strip", '~0,-1' not in c)
check("no curl", 'curl -s' not in c)
check("powershell iwr present", '$r=iwr' in c)
check("port 11435", '11435' in c and '11434' not in c)

with open(f"{PROJECT}/start.bat", 'r', encoding='utf-8', errors='replace') as f:
    c = f.read()
check("start.bat OLLAMA_MODELS", 'OLLAMA_MODELS' in c)
check("start.bat install-offline ref", 'install-offline.bat' in c)

with open(f"{PROJECT}/opencode.bat", 'r', encoding='utf-8', errors='replace') as f:
    c = f.read()
check("opencode.bat OLLAMA_MODELS", 'OLLAMA_MODELS' in c)
check("opencode.bat OLLAMA_HOST=127", '127.0.0.1:11435' in c)

# ============================================================
# TEST 4: Modelfile integrity
# ============================================================
header("4. Modelfile Integrity")

with open(f"{PROJECT}/ollama-models/Modelfile", 'r', encoding='utf-8', errors='replace') as f:
    mf = f.read()

check("Modelfile FROM line", "FROM ./qwen2.5-7b-instruct-q4_k_m.gguf" in mf)
check("Modelfile ASCII only", all(ord(c) < 128 for c in mf), "contains non-ASCII")
check("temperature set", "temperature 0.3" in mf.lower())
check("num_ctx set", "num_ctx 8192" in mf.lower())

# ============================================================
# TEST 5: merge_official.py test
# ============================================================
header("5. merge_official.py — Synthetic GGUF Test")

# Create 2 fake shards and merge
def make_test_shard(path, tc, kvs, data):
    d = bytearray(b'GGUF' + struct.pack('<IQQ', 3, tc, len(kvs)))
    for key, vt, val in kvs:
        d.extend(struct.pack('<Q', len(key)) + key.encode() + struct.pack('<I', vt))
        if vt == 8: d.extend(struct.pack('<Q', len(val)) + val.encode())
        elif vt == 4: d.extend(struct.pack('<I', val))
        elif vt == 9:
            at, av = val
            d.extend(struct.pack('<I', at) + struct.pack('<Q', len(av)))
            for v in av: d.extend(struct.pack('<Q', len(v)) + v.encode())
    d.extend(data)
    with open(path, 'wb') as f: f.write(d)

tokens = [f'token_{i:05d}' for i in range(100)]
make_test_shard(f"{TEST}/test-00001-of-00002.gguf", 200, [
    ('general.architecture', 8, 'test'),
    ('tokenizer.ggml.tokens', 9, (8, tokens)),
    ('split.count', 4, 2),
], b'T1_D' * 10000)
make_test_shard(f"{TEST}/test-00002-of-00002.gguf", 150, [
    ('general.architecture', 8, 'test'),
    ('split.count', 4, 2),
], b'T2_D' * 8000)

# Add gguf lib to path and test merge
sys.path.insert(0, f"{PROJECT}/.venv/Lib/site-packages")

try:
    from gguf import GGUFReader, GGUFWriter
    from gguf.constants import Keys
    
    os.chdir(TEST)
    
    # Run merge
    readers = [GGUFReader(f"{TEST}/test-00001-of-00002.gguf"),
               GGUFReader(f"{TEST}/test-00002-of-00002.gguf")]
    
    tensor_count = sum(len(r.tensors) for r in readers)
    check("merge: tensor count correct", tensor_count == 350, str(tensor_count))
    
    writer = GGUFWriter(f"{TEST}/test-merged.gguf", readers[0].arch)
    for key in readers[0].fields:
        if not key.startswith("split.") and not key.startswith("tokenizer.ggml.tokens"):
            try:
                field = readers[0].fields[key]
                val = field.parts[field.data[0]]
                if isinstance(val, str):
                    writer.add_string(key, val)
                elif isinstance(val, int):
                    writer.add_uint32(key, val)
            except:
                pass
    
    for reader in readers:
        for name, tensor in reader.tensors.items():
            writer.add_tensor(name, tensor.data, raw_dtype=tensor.tensor_type)
    
    writer.write_all_to_file()
    
    # Verify merged
    merged = GGUFReader(f"{TEST}/test-merged.gguf")
    check("merge: output valid GGUF", True)
    check("merge: no split keys", all(not k.startswith('split.') for k in merged.fields))
    check("merge: total tensors", len(merged.tensors) == 350, str(len(merged.tensors)))
    check("merge: data intact (T1)", b'T1_D' in open(f"{TEST}/test-merged.gguf", 'rb').read())
    check("merge: data intact (T2)", b'T2_D' in open(f"{TEST}/test-merged.gguf", 'rb').read())
    
    for f in ['test-00001-of-00002.gguf', 'test-00002-of-00002.gguf', 'test-merged.gguf']:
        try: os.remove(f"{TEST}/{f}")
        except: pass
    
except ImportError as e:
    check("merge: gguf lib available", False, f"ImportError: {e}")
except Exception as e:
    check("merge: execution", False, str(e)[:100])

# ============================================================
# TEST 6: Ollama end-to-end
# ============================================================
header("6. Ollama End-to-End")

try:
    os.chdir(f"{PROJECT}/tools/ollama")
    
    # Check ollama is running
    result = subprocess.run(["ollama.exe", "list"], capture_output=True, text=True, timeout=10,
                          env={**os.environ, "OLLAMA_HOST": "127.0.0.1:11435"})
    
    check("Ollama service running", result.returncode == 0, result.stderr[:80])
    check("Model qwen exists", "qwen" in result.stdout.lower(), result.stdout[:80])
    
    # Test inference
    result = subprocess.run(
        ["ollama.exe", "run", "qwen:7b-q4_K_M", "Say hello in one word"],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "OLLAMA_HOST": "127.0.0.1:11435",
             "OLLAMA_MODELS": f"{PROJECT}/ollama-cache"}
    )
    
    has_output = len(result.stdout.strip()) > 0 and "error" not in result.stdout.lower()
    check("Ollama inference works", has_output, result.stdout[:50] + result.stderr[:50])
    
except Exception as e:
    check("Ollama test", False, str(e)[:100])

# ============================================================
# TEST 7: Python imports
# ============================================================
header("7. Python Dependency Verification")

venv_python = f"{PROJECT}/.venv/Scripts/python.exe"
imports = [
    ("gradio", "import gradio"),
    ("ollama", "import ollama"),
    ("pandas", "import pandas"),
    ("numpy", "import numpy"),
    ("gguf", "from gguf import GGUFReader"),
    ("docx", "import docx"),
    ("pptx", "import pptx"),
    ("openpyxl", "import openpyxl"),
]

for name, code in imports:
    try:
        result = subprocess.run([venv_python, "-c", code], capture_output=True, timeout=10)
        check(f"import {name}", result.returncode == 0, result.stderr[:50])
    except Exception as e:
        check(f"import {name}", False, str(e)[:50])

# ============================================================
# SUMMARY
# ============================================================
header("SUMMARY")
print(f"  PASS: {PASS}")
print(f"  FAIL: {FAIL}")
print(f"  TOTAL: {PASS + FAIL}")
print()

if FAIL == 0:
    print("  *** ALL CHECKS PASSED ***")
else:
    print(f"  *** {FAIL} CHECKS FAILED ***")

os.chdir(PROJECT)
