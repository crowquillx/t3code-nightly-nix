{
  description = "Automatically updated Nix package for T3 Code nightly";

  nixConfig = {
    extra-substituters = [ "https://crowquillx-t3code-nightly.cachix.org" ];
    extra-trusted-public-keys = [
      "crowquillx-t3code-nightly.cachix.org-1:R+Cr24SRF6a4pGwdEhU5RiBzkIEMKlGdLWRQ7aPgef8="
    ];
  };

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      t3code-nightly = pkgs.callPackage ./pkgs/t3code-nightly { };
    in
    {
      formatter.${system} = pkgs.nixfmt;

      packages.${system} = {
        default = t3code-nightly;
        inherit t3code-nightly;
      };

      checks.${system} = {
        package = t3code-nightly;
        updater =
          pkgs.runCommandLocal "t3code-nightly-updater-tests"
            {
              nativeBuildInputs = [ pkgs.python3 ];
              UPDATE_SCRIPT = ./scripts/update.py;
            }
            ''
              python ${./tests/test_update.py}
              touch "$out"
            '';
      };
    };
}
