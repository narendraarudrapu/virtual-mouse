import cv2
import mediapipe as mp
import time
import math
import numpy as np
import os

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions
from mediapipe.tasks.python.vision.core import image as mp_image


class handDetector():
    def __init__(self, model_path=None, mode=False, maxHands=3, detectionCon=0.5, trackCon=0.5):
        self.mode = mode
        self.maxHands = maxHands
        self.detectionCon = detectionCon
        self.trackCon = trackCon
        self.tipIds = [4, 8, 12, 16, 20]
        # default model in project models/ folder
        if model_path is None:
            base = os.path.dirname(__file__)
            model_path = os.path.join(base, 'models', 'hand_landmarker.task')

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"hand_landmarker model not found at {model_path}. Please download and place it there.")

        # create a HandLandmarker instance from model file (image mode)
        try:
            self.landmarker = HandLandmarker.create_from_model_path(model_path)
        except Exception as e:
            raise RuntimeError(f"Failed to create HandLandmarker: {e}")

        self.results = None
        self.lmList = []

    def findHands(self, img, draw=True):
        # img is BGR (cv2) -> convert to RGB
        h, w, _ = img.shape
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mpimg = mp_image.Image(mp_image.ImageFormat.SRGB, img_rgb)

        result = self.landmarker.detect(mpimg)
        self.results = result

        # draw simple landmarks
        if draw and result and result.hand_landmarks:
            for hand_landmarks in result.hand_landmarks:
                for lm in hand_landmarks:
                    cx, cy = int(lm.x * w), int(lm.y * h)
                    cv2.circle(img, (cx, cy), 3, (255, 0, 255), cv2.FILLED)
        return img

    def findPosition(self, img, handNo=0, draw=True):
        xList = []
        yList = []
        bbox = []
        self.lmList = []
        if not self.results or not self.results.hand_landmarks:
            return self.lmList, bbox

        if handNo >= len(self.results.hand_landmarks):
            return self.lmList, bbox

        hand = self.results.hand_landmarks[handNo]
        h, w, _ = img.shape
        for id, lm in enumerate(hand):
            cx, cy = int(lm.x * w), int(lm.y * h)
            xList.append(cx)
            yList.append(cy)
            self.lmList.append([id, cx, cy])
            if draw:
                cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)

        if xList and yList:
            xmin, xmax = min(xList), max(xList)
            ymin, ymax = min(yList), max(yList)
            bbox = (xmin, ymin, xmax, ymax)
            if draw:
                cv2.rectangle(img, (xmin - 20, ymin - 20), (xmax + 20, ymax + 20), (0, 255, 0), 2)

        return self.lmList, bbox

    def fingersUp(self):
        fingers = []
        if not self.lmList:
            return [0,0,0,0,0]
        # Thumb: compare x of tip and prior landmark
        try:
            if self.lmList[self.tipIds[0]][1] > self.lmList[self.tipIds[0] - 1][1]:
                fingers.append(1)
            else:
                fingers.append(0)
        except Exception:
            fingers.append(0)

        # Other fingers: tip y < pip y means finger up
        for id in range(1,5):
            try:
                if self.lmList[self.tipIds[id]][2] < self.lmList[self.tipIds[id] - 2][2]:
                    fingers.append(1)
                else:
                    fingers.append(0)
            except Exception:
                fingers.append(0)

        return fingers

    def findDistance(self, p1, p2, img, draw=True, r=15, t=3):
        if not self.lmList:
            return 0, img, [0,0,0,0,0,0]
        x1, y1 = self.lmList[p1][1:]
        x2, y2 = self.lmList[p2][1:]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if draw:
            cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), t)
            cv2.circle(img, (x1, y1), r, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (x2, y2), r, (255, 0, 255), cv2.FILLED)
            cv2.circle(img, (cx, cy), r, (0, 0, 255), cv2.FILLED)

        length = math.hypot(x2 - x1, y2 - y1)
        return length, img, [x1, y1, x2, y2, cx, cy]


def main():
    pTime = 0
    cTime = 0
    cap = cv2.VideoCapture(0)
    detector = handDetector()
    while True:
        success, img = cap.read()
        img = detector.findHands(img)
        lmList, bbox = detector.findPosition(img)
        if len(lmList) != 0:
            print(lmList[4])

        cTime = time.time()
        fps = 1 / (cTime - pTime) if (cTime - pTime) != 0 else 0
        pTime = cTime

        cv2.putText(img, str(int(fps)), (10, 70), cv2.FONT_HERSHEY_PLAIN, 3, (255, 0, 255), 3)

        cv2.imshow("Image", img)
        if cv2.waitKey(1) & 0xFF == 27:
            break


if __name__ == "__main__":
    main()