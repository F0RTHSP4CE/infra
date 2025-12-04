{
  description = "f0rthsp4ce server configs";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";

    flake-utils.url = "github:numtide/flake-utils";

    agenix = {
      url = "github:ryantm/agenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    home-manager = {
      url = "github:nix-community/home-manager/release-25.11";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    deploy-rs.url = "github:serokell/deploy-rs";

    botka-v0.url =
      "github:f0rthsp4ce/botka/4ada593690610da9a7105913c9564b9f673c267e";
    botka-v1.url = "github:f0rthsp4ce/botka";
  };

  outputs = { self, nixpkgs, flake-utils, agenix, deploy-rs, ... }@attrs:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        config = { permittedInsecurePackages = [ "olm-3.2.16" ]; };
      };
      deployPkgs = import nixpkgs {
        inherit system;
        overlays = [
          deploy-rs.overlays.default
          (self: super: {
            deploy-rs = {
              inherit (pkgs) deploy-rs;
              lib = super.deploy-rs.lib;
            };
          })
        ];
      };
      meta = builtins.mapAttrs
        (key: value: pkgs.lib.importJSON ./machines/${key}/meta.json)
        (builtins.readDir ./machines);
    in {
      nixosConfigurations = builtins.mapAttrs (key: value:
        (nixpkgs.lib.nixosSystem {
          system = meta.${key}.system;
          specialArgs = attrs;
          modules = [ ./machines/${key} ];
        })) (builtins.readDir ./machines);

      deploy.nodes = builtins.mapAttrs (key: value: {
        hostname = meta.${key}.deploy_ip;
        profiles.system = {
          user = "root";
          path = deployPkgs.deploy-rs.lib.activate.nixos value;
        };
      }) self.nixosConfigurations;

      overlays.default = final: prev: (import ./overlay.nix final attrs);

      checks = builtins.mapAttrs
        (system: deployLib: deployLib.deployChecks self.deploy) deploy-rs.lib;
    } // flake-utils.lib.eachSystem
    (with flake-utils.lib.system; [ x86_64-linux i686-linux aarch64-linux ])
    (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
      in {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            agenix.packages.${system}.default
            pkgs.nixfmt-classic
            pkgs.deploy-rs
          ];
        };

        packages = {
          ci-cache = pkgs.stdenv.mkDerivation {
            name = "ci-cache";
            version = "0.1.0";
            buildInputs =
              ([ ] ++ builtins.attrValues (import ./overlay.nix pkgs attrs));
            phases = [ "installPhase" ];
            installPhase = "echo 'ci-cache' > $out";
          };
        } // (import ./overlay.nix pkgs attrs);
      });
}
