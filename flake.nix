{
  description = "funscript-copilot";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        system = "${system}";
      };
      dependencies = with pkgs; [
        (python310.withPackages (p: with p; [
          customPythonPackages.pkgs.opencv4
          customPythonPackages.pkgs.coloredlogs
          customPythonPackages.pkgs.cryptography
          customPythonPackages.pkgs.matplotlib
          customPythonPackages.pkgs.pip
          customPythonPackages.pkgs.pyyaml
          customPythonPackages.pkgs.scipy
          customPythonPackages.pkgs.websockets
          customPythonPackages.pkgs.scikit-learn
          customPythonPackages.pkgs.GitPython
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
      packages.${system}.funscript-copilot = pkgs.python39Packages.buildPythonPackage {
        pname = "funscript-copilot";
        version = "0.0.1";
        src = pkgs.fetchFromGitHub {
          owner = "michael-mueller-git";
          repo = "funscript-copilot";
          rev = "3f9a1d19add2b165f54855a22b87251ef7645be";
          # NOTE: change hash to refresh
          sha256 = "sha256-2YdVuC50lmrQtbeJLwui7m6ezOOyPMYeAOT6m+OnAXY";
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
