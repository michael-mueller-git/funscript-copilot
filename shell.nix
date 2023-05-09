{ pkgs ? import <nixpkgs> {} }:
let python =
    let
    packageOverrides = self:
    super: {
      opencv4 = super.opencv4.overrideAttrs (old: rec {
        buildInputs = old.buildInputs ++ [pkgs.qt6.full];
        cmakeFlags = old.cmakeFlags ++ ["-DWITH_QT=6"];
      });
    };
    in
      pkgs.python310.override {inherit packageOverrides; self = python;};
in
  pkgs.mkShell {
    nativeBuildInputs = with pkgs; [
      python.pkgs.opencv4
      (python310.withPackages (p: with p; [
        cryptography
        matplotlib
        pip
        pyyaml
        scikit-learn
        scipy
        websockets
      ]))
    ];

 shellHook = ''
    export QT_QPA_PLATFORM="xcb"
  '';
}
