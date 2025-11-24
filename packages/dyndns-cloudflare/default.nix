{ writers, python3Packages, ... }:

writers.writePython3Bin "dyndns-cloudflare" {
  libraries = with python3Packages; [ requests cloudflare ];
  flakeIgnore = [ "E" "W" ];
} (builtins.readFile ./main.py)
