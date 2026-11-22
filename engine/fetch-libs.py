#!/usr/bin/env python3
"""User-space shared-library bundle for headless Chrome on Debian (no root).

Downloads the .deb packages that provide the sonames `ldd` reports as missing,
extracts them with dpkg-deb into ./libs, and repeats until ldd is clean.
Mapping soname -> package comes from the Debian Contents index.
"""
import gzip, io, os, re, subprocess, sys, urllib.request

MIRROR = "https://deb.debian.org/debian"
DIST = "trixie"
HERE = os.path.dirname(os.path.abspath(__file__))
LIBS = os.environ.get("RF_LIBS_DIR") or os.path.join(HERE, "libs")
DEBS = os.path.join(os.path.dirname(os.path.abspath(LIBS)), "debs")
LIBDIRS = [os.path.join(LIBS, "usr/lib/x86_64-linux-gnu"), os.path.join(LIBS, "lib/x86_64-linux-gnu")]
os.makedirs(LIBS, exist_ok=True); os.makedirs(DEBS, exist_ok=True)

binaries = sys.argv[1:]
if not binaries:
    sys.exit("usage: [RF_LIBS_DIR=<dir>] fetch-libs.py <binary> [...]")

def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()

print("loading Contents index ...", flush=True)
contents = {}
raw = fetch(f"{MIRROR}/dists/{DIST}/main/Contents-amd64.gz")
with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8", errors="replace") as f:
    for line in f:
        if not line.startswith("usr/lib/x86_64-linux-gnu/"):
            continue
        path, pkgs = line.rsplit(None, 1)
        name = path.rsplit("/", 1)[-1]
        if ".so" in name and name not in contents:
            contents[name] = pkgs.split(",")[0].split("/")[-1]
print(f"  {len(contents)} sonames indexed", flush=True)

print("loading Packages index ...", flush=True)
packages = {}
raw = fetch(f"{MIRROR}/dists/{DIST}/main/binary-amd64/Packages.gz")
with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8", errors="replace") as f:
    cur = {}
    for line in f:
        line = line.rstrip("\n")
        if not line:
            if "Package" in cur:
                packages[cur["Package"]] = cur
            cur = {}
        elif ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            cur[k] = v.strip()
print(f"  {len(packages)} packages indexed", flush=True)

def ldd_missing(paths):
    env = dict(os.environ, LD_LIBRARY_PATH=":".join(LIBDIRS))
    missing = set()
    for p in paths:
        out = subprocess.run(["ldd", p], capture_output=True, text=True, env=env).stdout
        for m in re.finditer(r"^\s*(\S+) => not found", out, re.M):
            missing.add(m.group(1))
    return missing

def all_sos():
    res = []
    for d in LIBDIRS:
        if os.path.isdir(d):
            for root, _, files in os.walk(d):
                res += [os.path.join(root, f) for f in files if ".so" in f]
    return res

installed = set()
for rnd in range(8):
    missing = ldd_missing(binaries + all_sos())
    if not missing:
        print("ldd clean", flush=True); break
    want = set()
    for so in sorted(missing):
        pkg = contents.get(so)
        if not pkg:
            print(f"  !! no package provides {so}", flush=True); continue
        want.add(pkg)
    want -= installed
    if not want:
        print("no further packages to install but still missing:", sorted(missing)); break
    print(f"round {rnd}: {len(missing)} missing sonames -> {sorted(want)}", flush=True)
    for pkg in sorted(want):
        meta = packages.get(pkg)
        if not meta:
            print(f"  !! {pkg} not in Packages"); continue
        deb = os.path.join(DEBS, os.path.basename(meta["Filename"]))
        if not os.path.exists(deb):
            open(deb, "wb").write(fetch(f"{MIRROR}/{meta['Filename']}"))
        subprocess.run(["dpkg-deb", "-x", deb, LIBS], check=True)
        installed.add(pkg)
        print(f"  + {pkg} {meta.get('Version','')} ({int(meta.get('Size','0'))//1024} KB)", flush=True)

print("installed packages:", sorted(installed))
print("LD_LIBRARY_PATH=" + ":".join(LIBDIRS))
