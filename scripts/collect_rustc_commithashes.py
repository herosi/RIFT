"""
Helper script to initialize JSON file mapping commit hashes to corresponding rust version.
Python is too slow to process this IMO, we need to implement this in either golang or rust.
"""

import argparse
import re
import requests
import json

RE_TOML_FILE_PATTERN = r"(.{1,50}\s.{1,50})\s(\d+)\s(channel-rust.{1,20}.toml$)"
r_toml_file = re.compile(RE_TOML_FILE_PATTERN)

RE_COMMIT_HASH = r"git_commit_hash = \"(.*)\".*"
r_commit_hash = re.compile(RE_COMMIT_HASH)

RE_RUST_VERSION = r"channel-rust-(.{1,30})\.toml"
r_rust_version = re.compile(RE_RUST_VERSION)

AWS_URL = "https://static.rust-lang.org/dist/"

def main(args):
    """Main."""
    print(f"[debug] Starting build_chash_info.py, storing results in {args.o}")
    lines = []
    json_output = {"exact_hash_to_version": []}
    with open(args.i, "r") as f:
        lines = f.readlines()
    
    print(f"[debug] Total lines = {len(lines)}")
    for line in lines:

        m = r_toml_file.match(line)
        rust_version = ""
        if m:
            
            timestamp = m.group(1)
            name = m.group(3)
            m = r_rust_version.match(name)
            if m:
                rust_version = m.group(1)
            url = f"{AWS_URL}{name}"

            print(f"[debug] Downloading TOML file from {url}")
            response = requests.get(url)
            if response.status_code != 200:
                continue
                
            # For now, determine only since which version the git commit hash is included in the toml
            # This is appararently since version 1.50.0
            content = response.content[0:1000]
            if not b"git_commit_hash" in content:
                continue
            for line in content.decode("ascii").split("\n"):
                m = r_commit_hash.match(line)
                if m:
                    commit_hash = m.group(1)
                    json_output["exact_hash_to_version"].append({"timestamp": timestamp.rstrip(), 
                                                                 "name": name.rstrip(), 
                                                                 "url": url, 
                                                                 "commit_hash": commit_hash, 
                                                                 "rust_version": rust_version})
                    break
    
    with open(args.o, "w+") as f:
        json.dump(json_output, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", help="Input file, result of 'aws --no-sign-request s3 ls s3://static-rust-lang-org/dist/ >> out.txt'")
    parser.add_argument("-o", help="Output file name", default="data/rustc_tags.json")
    main(parser.parse_args())