{ writers, python3Packages, ... }:

writers.writePython3Bin "autodns" {
  libraries = with python3Packages; [ librouteros cloudflare ];
  flakeIgnore = [ "E" "W" ];
} (builtins.readFile ./main.py)
