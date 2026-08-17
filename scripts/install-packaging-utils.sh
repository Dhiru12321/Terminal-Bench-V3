#!/usr/bin/env bash
# zip/unzip — required for TB3 packaging / gates (see AGENT SETUP MANIFEST.txt).
set -euo pipefail
sudo apt-get update -qq
sudo apt-get install -y zip unzip
command -v zip unzip
zip -v | head -1
unzip -v | head -1
