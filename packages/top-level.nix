pkgs:

{
  upgrade-system = pkgs.callPackage ./upgrade-system.nix { };
  dyndns-cloudflare = pkgs.callPackage ./dyndns-cloudflare { };
  autodns = pkgs.callPackage ./autodns { };
  element-f0rth-space = pkgs.callPackage ./element.nix { };
}
