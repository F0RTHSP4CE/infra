{ lib, pkgs, config, ... }:

{
  services.nginx = {
    # Reload service instead of restart on nixos switch
    enableReload = true;
    # Enable QUIC connection migration
    enableQuicBPF = true;

    # Enable recommended settings
    recommendedGzipSettings = true;
    recommendedTlsSettings = true;
    recommendedProxySettings = true;
    recommendedOptimisation = true;
    recommendedBrotliSettings = true;
  };
}
