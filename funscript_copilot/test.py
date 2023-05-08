import cv2.
import numpy as np
from sklearn.decomposition import IncrementalPCA
import json

N_COMPONENTS = 2

cap = cv2.VideoCapture("./example1.mkv")
fps = cap.get(cv2.CAP_PROP_FPS)
with open("./example1.funscript") as f:
    funscript = json.load(f)
    gt_x = []
    gt_y = []
    print("fps", fps)
    frame_time = 1000.0 / fps
    print('frame_time', frame_time)
    for action in funscript["actions"]:
        gt_x.append(action["at"]/frame_time)
        gt_y.append(action["pos"])

ret, first_frame = cap.read()
img = cv2.resize(first_frame,None,fx=0.1,fy=0.1)
height, width = img.shape[:2]
first_frame = img[:, :int(width/2)]
prev_gray = cv2.cv2.Color(first_frame, cv2.COLOR_BGR2GRAY)

# ipca = IncrementalPCA(n_components=N_COMPONENTS, batch_size=BATCH_SITE)

all_X_data = []
all_Y_data = []
i = 0
while(cap.isOpened()):
    i += 1
    ret, frame = cap.read()
    if not ret:
        break
    img = cv2.resize(frame,None,fx=0.1,fy=0.1)
    height, width = img.shape[:2]
    frame = img[:, :int(width/2)]
    gray = cv2.cv2.Color(frame, cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    X_move = np.array(flow[..., 0]).flatten()
    Y_move = np.array(flow[..., 1]).flatten()
    all_X_data.append(X_move)
    all_Y_data.append(Y_move)

    print(i)
    if i > 230:
        break

_, _, pcX = np.linalg.svd(np.transpose(np.array(all_X_data)), full_matrices=False)
_, _, pcY = np.linalg.svd(np.transpose(np.array(all_Y_data)), full_matrices=False)

pcX = np.transpose(np.array(pcX[:N_COMPONENTS,:]))
pcY = np.transpose(np.array(pcY[:N_COMPONENTS,:]))

minimum = min((np.min(pcX), np.min(pcY)))
maximum = max((np.max(pcX), np.max(pcY)))

print(minimum, maximum)

def scale(signal: list, lower: float = 0, upper: float = 99) -> list:
    """ Scale an signal (list of float or int) between given lower and upper value

    Args:
        signal (list): list with float or int signal values to scale
        lower (float): lower scale value
        upper (float): upper scale value

    Returns:
        list: list with scaled signal
    """
    if len(signal) == 0:
        return signal

    if len(signal) == 1:
        return [lower]

    signal_min = min(signal)
    signal_max = max(signal)
    return [(float(upper) - float(lower)) * (x - signal_min) / (signal_max - signal_min) + float(lower) for x in signal]

gt_y = scale(gt_y, minimum, maximum)

endpos_gt = 0
for idx, at in enumerate(gt_x):
    if at > i:
        endpos_gt = idx
        break

gt_x = gt_x[:endpos_gt]
gt_y = gt_y[:endpos_gt]

# plt.plot(np.array(pcX[:,0]) + np.array(pcX[:,1]))
# plt.plot(np.array(pcY[:,0]) + np.array(pcY[:,1]))
# plt.plot(gt_x, gt_y)
# plt.show()

cap.release()
cv2.destroyAllWindows()
