import apriltag
import cv2
import numpy as np
from _helper import get_config

CONFIG = get_config()

MTX = np.load(CONFIG["calc_intrinsics"]["filenames"]["mtx"])
DIST = np.load(CONFIG["calc_intrinsics"]["filenames"]["dist"])

TAG_SIZE = CONFIG["apriltag"]["tag_size"]

def detect_apriltags(input_frame: cv2.Mat, draw_tags=True, draw_tag_dists=True):
    frame = input_frame.copy()

    # convert the frame to grayscale
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # get the dectector with the family of tags we want to detect
    options = apriltag.DetectorOptions(families=CONFIG["apriltag"]["tag_family"])
    detector = apriltag.Detector(options)

    # detect the apriltags in the image
    results = detector.detect(gray_frame)

    # create a list of the things we want to return
    return_list = []

    # loop over the detected AprilTags
    for r in results:
        if not 1 <= r.tag_id <= 8:
            # not a tag used in FRC2023, may be a false detection
            continue
        # extract the bounding box (x, y)-coordinates for the AprilTag & center and undistort them
        # using the camera matrix and distortion coefficients
        corners = np.array(cv2.undistortImagePoints(r.corners, MTX, DIST)).squeeze()
        r = r._replace(corners=corners)
        center = np.array(cv2.undistortImagePoints(r.center, MTX, DIST)).squeeze()
        r = r._replace(center=center)

        # unpack the corners
        (ptA, ptB, ptC, ptD) = corners
        ptB = (int(ptB[0]), int(ptB[1]))
        ptC = (int(ptC[0]), int(ptC[1]))
        ptD = (int(ptD[0]), int(ptD[1]))
        ptA = (int(ptA[0]), int(ptA[1]))

        if draw_tags:
            # draw the bounding box of the AprilTag detection on the original, distorted and colored frame
            cv2.line(frame, ptA, ptB, (255, 0, 0), 2)
            cv2.line(frame, ptB, ptC, (255, 0, 0), 2)
            cv2.line(frame, ptC, ptD, (255, 0, 0), 2)
            cv2.line(frame, ptD, ptA, (255, 0, 0), 2)

            # draw the center (x, y)-coordinates of the AprilTag
            (cX, cY) = (int(center[0]), int(center[1]))
            cv2.circle(frame, (cX, cY), 5, (0, 0, 255), -1)

            # draw the id number on the frame
            tagId = f"ID {r.tag_id}"
            cv2.putText(frame, tagId, (ptA[0], ptA[1] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # detect the pose of the apriltag
        pose, e0, e1 = detector.detection_pose(r, (MTX[0,0], MTX[1,1], MTX[0,2], MTX[1,2]), TAG_SIZE)

        # create the 4x4 pose matrix that stores the pixel coordinates of the corners
        ncorners = np.array([[-TAG_SIZE/2, TAG_SIZE/2, 0, 1],
                        [TAG_SIZE/2, TAG_SIZE/2, 0, 1],
                        [TAG_SIZE/2, -TAG_SIZE/2, 0, 1],
                        [-TAG_SIZE/2, -TAG_SIZE/2, 0, 1],
                        [0, 0, 0, 1]])

        # transform the pixel coordinate corners to the real-world coordinate system based on the pose (linear algebra)
        corners_trans = np.matmul(pose, np.transpose(ncorners))

        if draw_tag_dists:
            # draw the real-world distance from the camera to the tag
            for i in range(3):
                cv2.putText(frame, f"{chr(ord('x')+i)}: {round(corners_trans[i][4], 5)}", (cX+15, cY+(15*i)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # get the yaw, pitch and roll of the center of the tag in degrees
        yaw = -round(np.arctan2(-pose[2][0], np.sqrt(pose[2][1]**2 + pose[2][2]**2)) * 180 / np.pi, 5)
        pitch = -round(np.arctan2(pose[2][1], pose[2][2]) * 180 / np.pi, 5)
        roll = -round(np.arctan2(pose[1][0], pose[0][0]) * 180 / np.pi, 5)

        return_list.append({
            "id": r.tag_id,
            "dist": (corners_trans[0][4], corners_trans[1][4], corners_trans[2][4]), # x, y, z distances
            "rot": (yaw, pitch, roll), # yaw, pitch, roll
        })

    return frame, return_list

if __name__ == "__main__":
    cap = cv2.VideoCapture(CONFIG["camera"]["port"])
    print(f"[INFO] start VideoCapture on USB {CONFIG['camera']['port']}")

    while True:
        ret, frame = cap.read()
        frame = cv2.resize(frame, (CONFIG["camera"]["size"]["width"], CONFIG["camera"]["size"]["height"]))
        drawn_frame, tags = detect_apriltags(frame)
        cv2.imshow("drawn_frame", drawn_frame)
        cv2.imshow("frame", frame)
        print(tags)
        key = cv2.waitKey(1)
        if key == ord('q'):
            break

    cap.release()
    print("[INFO] stop VideoCapture")