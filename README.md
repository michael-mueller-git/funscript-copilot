# funscript-copilot

Collection of funscript copilot scripts.

- `dense-optical-flow`: This method use OpticalFlow + PCA to determine the movement inside a video and stream the predicted top and bottom turnpoints of the movement via websocket to OFS where the user can futher optimize the delta for the movement.
- `auto-tracker`: Use custom yolov10 model to track the dick length and predict funscript actions.

## Setup

Currently this project only support Linux via [Nix package manager](https://nixos.org/download.html). In Addition you need to install [my Fork of OFS](https://github.com/michael-mueller-git/OFS) which supports add actions via websocket functions. The extension is available in the OFS lua extension menu when you install [my Fork of OFS](https://github.com/michael-mueller-git/OFS) via nix.
