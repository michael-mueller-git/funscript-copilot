#!/usr/bin/env bash

root_dir="$(dirname $0)"
cmd="python3 `dirname $0`/main.py"
# cd $root_dir && nix develop --command $cmd "$@" 2>&1 | tee /tmp/funscript-copilot-nix.log

# TODO: The PCA from nixpkgs looks broken. Workaround use local python env
eval "$cmd $@"
