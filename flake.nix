{
  description = "funscript-copilot";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
  };

  outputs = { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        system = "${system}";
      };
      dependencies = [
        (pkgs.python310.withPackages (p: with p; [
          customPythonPackages.pkgs.scikit-learn
          customPythonPackages.pkgs.opencv4
          customPythonPackages.pkgs.coloredlogs
          customPythonPackages.pkgs.cryptography
          customPythonPackages.pkgs.matplotlib
          customPythonPackages.pkgs.pip
          customPythonPackages.pkgs.pyyaml
          customPythonPackages.pkgs.scipy
          customPythonPackages.pkgs.websockets
          customPythonPackages.pkgs.GitPython
          customPythonPackages.pkgs.onnxruntime
          customPythonPackages.pkgs.filterpy
          customPythonPackages.pkgs.pandas
          customPythonPackages.pkgs.pynput
        ]))
      ];
      libPath = pkgs.lib.makeLibraryPath dependencies;
      binPath = pkgs.lib.makeBinPath dependencies;

      customPythonPackages =
        let
          packageOverrides = self:
            super: {
              opencv4 = super.opencv4.overrideAttrs (old: rec {
                buildInputs = old.buildInputs ++ [ pkgs.qt6.full ];
                cmakeFlags = old.cmakeFlags ++ [ "-DWITH_QT=ON" ];
              });
            };
        in
        pkgs.python310.override { inherit packageOverrides; self = customPythonPackages; };
    in
    {
      packages.${system}.funscript-copilot = pkgs.python310Packages.buildPythonPackage {
        pname = "funscript-copilot";
        version = "0.0.2";
        src = pkgs.fetchFromGitHub {
          owner = "michael-mueller-git";
          repo = "funscript-copilot";
          rev = "ebedf5f105e0a8df49c45bf75fd34dd9c91b7ba1";
          # NOTE: change hash to refresh
          sha256 = "sha256-Y0uMPuGjiYDeteEAS08qqPVzJupd1XYUWRNdBlvUK/w=";
          fetchSubmodules = true;
        };
        propagatedBuildInputs = dependencies;
        nativeBuildInputs = with pkgs; [
          makeWrapper
        ];
        postInstall = ''
          wrapProgram "$out/bin/funscript-copilot" --prefix LD_LIBRARY_PATH : "${libPath}" --prefix PATH : "${binPath}"
        '';
      };
      defaultPackage.${system} = self.packages.x86_64-linux.funscript-copilot;
      formatter.${system} = pkgs.nixpkgs-fmt;
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = dependencies;
      };
    };
}
