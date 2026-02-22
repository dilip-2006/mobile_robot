#!/usr/bin/env python3
"""
Gesture Controlled Mobile Robot – Professional HUD
Author : Dilip Kumar
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import cv2
import mediapipe as mp
import numpy as np
import time
from datetime import datetime

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = ( 18,  18,  24)
ACCENT  = (  0, 195, 160)
BLUE    = (  0, 140, 255)
TEXT_HI = (225, 225, 235)
TEXT_LO = (105, 105, 120)
LINE    = ( 42,  42,  54)
GREEN   = (  0, 210, 115)
RED_    = ( 65,  65, 220)

FONT    = cv2.FONT_HERSHEY_SIMPLEX
DUPLEX  = cv2.FONT_HERSHEY_DUPLEX


def _t(p, txt, x, y, col=TEXT_HI, sc=0.38, th=1):
    cv2.putText(p, txt, (x, y), FONT, sc, col, th, cv2.LINE_AA)


def _div(p, y, pw, px=14):
    cv2.line(p, (px, y), (pw - px, y), LINE, 1)


def _bar(p, label, val, maxv, x, y, bw, bh, col, pw):
    _t(p, label, x, y, TEXT_LO, 0.28)
    cv2.rectangle(p, (x, y + 3), (x + bw, y + 3 + bh), (42, 42, 56), -1)
    fill = int(min(abs(val) / maxv, 1.0) * bw)
    if fill > 0:
        cv2.rectangle(p, (x, y + 3), (x + fill, y + 3 + bh), col, -1)
    cv2.rectangle(p, (x, y + 3), (x + bw, y + 3 + bh), LINE, 1)
    _t(p, f"{val:+.2f}", x + bw + 5, y + 3 + bh, TEXT_HI, 0.28)


class GestureControlNode(Node):
    def __init__(self):
        super().__init__('gesture_control')
        self.pub   = self.create_publisher(Twist, 'cmd_vel', 10)
        self.timer = self.create_timer(0.05, self.cb)

        mh             = mp.solutions.hands
        self.hands     = mh.Hands(max_num_hands=1, min_detection_confidence=0.7)
        self.draw      = mp.solutions.drawing_utils
        self.styles    = mp.solutions.drawing_styles
        self.CONN      = mh.HAND_CONNECTIONS

        self.cap   = cv2.VideoCapture(0)
        self.t0    = time.time()
        self._ft   = time.time()
        self._fn   = 0
        self._fps  = 0.0
        self._sl   = 0.0   # smoothed linear
        self._sa   = 0.0   # smoothed angular

        self.get_logger().info("Gesture Control Node active.")

    def _dpad(self, p, cx, cy, gesture):
        """Four arrow triangles around a centre dot."""
        arrows = {
            "FORWARD":    np.array([(cx,cy-20),(cx-10,cy-6),(cx+10,cy-6)]),
            "BACKWARD":   np.array([(cx,cy+20),(cx-10,cy+6),(cx+10,cy+6)]),
            "TURN LEFT":  np.array([(cx-20,cy),(cx-6,cy-10),(cx-6,cy+10)]),
            "TURN RIGHT": np.array([(cx+20,cy),(cx+6,cy-10),(cx+6,cy+10)]),
        }
        for key, pts in arrows.items():
            cv2.fillPoly(p, [pts], ACCENT if key == gesture else (48, 48, 62))
        cv2.circle(p, (cx, cy), 4,
                   ACCENT if gesture != "STOP" else (70, 70, 88), -1)

    def cb(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame  = cv2.flip(frame, 1)
        result = self.hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        msg          = Twist()
        gesture      = "STOP"
        finger_count = 0

        if result.multi_hand_landmarks:
            for hl in result.multi_hand_landmarks:
                self.draw.draw_landmarks(
                    frame, hl, self.CONN,
                    self.styles.get_default_hand_landmarks_style(),
                    self.styles.get_default_hand_connections_style())

                fh, fw = frame.shape[:2]
                pts = [[int(l.x * fw), int(l.y * fh)] for l in hl.landmark]
                tips = [8, 12, 16, 20]
                finger_count = sum(1 for t in tips if pts[t][1] < pts[t-2][1])

                if   finger_count == 1: msg.linear.x  =  0.5; gesture = "FORWARD"
                elif finger_count == 2: msg.linear.x  = -0.5; gesture = "BACKWARD"
                elif finger_count == 3: msg.angular.z =  1.0; gesture = "TURN LEFT"
                elif finger_count == 4: msg.angular.z = -1.0; gesture = "TURN RIGHT"

                if msg.linear.x or msg.angular.z:
                    self.get_logger().info(
                        f'{gesture} | Lin={msg.linear.x:+.2f} Ang={msg.angular.z:+.2f}')

        self.pub.publish(msg)

        # Smooth velocity
        a = 0.3
        self._sl = a * msg.linear.x  + (1-a) * self._sl
        self._sa = a * msg.angular.z + (1-a) * self._sa

        # FPS
        self._fn += 1
        now = time.time()
        if now - self._ft >= 1.0:
            self._fps = self._fn / (now - self._ft)
            self._fn  = 0
            self._ft  = now

        # ── Sidebar ──────────────────────────────────────────────────────────
        H, W = frame.shape[:2]
        PW   = 240
        px   = 14
        p    = np.full((H, PW, 3), BG, dtype=np.uint8)

        # Left accent stripe (always full height)
        cv2.rectangle(p, (0, 0), (3, H), ACCENT, -1)

        # We draw each block sequentially using a y-cursor.
        # Each block has a fixed pixel height. Heights sum ≤ H.
        # Heights chosen for a 480px frame; they also work at 720px.

        # ── [1] HEADER (44px) ────────────────────────────────────────────────
        y = 0
        SH = 44
        cv2.rectangle(p, (0, y), (PW, y + SH), (28, 28, 40), -1)
        cv2.putText(p, "GESTURE ROBOT", (px, y + 20),
                    DUPLEX, 0.52, ACCENT, 1, cv2.LINE_AA)
        _t(p, "Mobile Control  v2.0", px, y + 36, TEXT_LO, 0.28)
        y += SH
        _div(p, y, PW, 0)

        # ── [2] SYSTEM INFO (36px) ────────────────────────────────────────────
        SH = 36
        up = int(now - self.t0);  mm, ss = divmod(up, 60)
        ts = datetime.now().strftime("%H:%M:%S")
        _t(p, f"FPS {self._fps:4.1f}", px, y + 14, TEXT_LO, 0.32)
        _t(p, ts,                       PW - 72, y + 14, TEXT_LO, 0.32)
        _t(p, f"UP  {mm:02d}:{ss:02d}", px, y + 28, TEXT_LO, 0.32)
        y += SH
        _div(p, y, PW, px)

        # ── [3] COMMAND (54px) ────────────────────────────────────────────────
        SH      = 54
        cmd_col = RED_ if gesture == "STOP" else GREEN
        _t(p, "COMMAND", px, y + 13, TEXT_LO, 0.30)
        # badge
        BY, BH = y + 18, 28
        cv2.rectangle(p, (px - 2, BY), (PW - px + 2, BY + BH), (35, 35, 50), -1)
        cv2.rectangle(p, (px - 2, BY), (PW - px + 2, BY + BH), LINE, 1)
        cv2.putText(p, gesture, (px + 4, BY + BH - 6),
                    DUPLEX, 0.60, cmd_col, 2, cv2.LINE_AA)
        y += SH
        _div(p, y, PW, px)

        # ── [4] D-PAD (74px) ─────────────────────────────────────────────────
        SH = 74
        _t(p, "DIRECTION", px, y + 13, TEXT_LO, 0.30)
        self._dpad(p, PW // 2, y + 46, gesture)
        y += SH
        _div(p, y, PW, px)

        # ── [5] FINGER DOTS (48px) ────────────────────────────────────────────
        SH      = 48
        dot_r   = 9
        spacing = (PW - 2 * px) // 5
        _t(p, "FINGERS DETECTED", px, y + 13, TEXT_LO, 0.30)
        for i in range(5):
            col  = ACCENT if i < finger_count else (50, 50, 64)
            cx_  = px + spacing // 2 + i * spacing
            cy_  = y + 33
            cv2.circle(p, (cx_, cy_), dot_r, col, -1)
            _t(p, str(i+1), cx_ - 3, cy_ + 4,
               BG if i < finger_count else (80, 80, 96), 0.24)
        y += SH
        _div(p, y, PW, px)

        # ── [6] TELEMETRY (52px) ──────────────────────────────────────────────
        SH  = 52
        bw  = int(PW * 0.57)
        bh_ = 9
        _bar(p, "LINEAR  X", self._sl, 1.0, px, y + 18, bw, bh_, GREEN, PW)
        _bar(p, "ANGULAR Z", self._sa, 1.5, px, y +40, bw, bh_, BLUE,  PW)
        y += SH
        _div(p, y, PW, px)

        # ── [7] HAND STATUS (32px) ────────────────────────────────────────────
        SH      = 32
        hand_on = bool(result.multi_hand_landmarks)
        h_col   = GREEN if hand_on else RED_
        h_txt   = "HAND  DETECTED" if hand_on else "SEARCHING..."
        _t(p, "SENSOR", px, y + 12, TEXT_LO, 0.30)
        cv2.circle(p, (px + 5, y + 24), 5, h_col, -1)
        _t(p, h_txt, px + 16, y + 27, h_col, 0.33)
        y += SH
        _div(p, y, PW, px)

        # ── [8] GUIDE – fills remaining space ─────────────────────────────────
        guide   = [("1","Forward"), ("2","Backward"),
                   ("3","Turn Left"), ("4","Turn Right"), ("0","Stop")]
        # Reserve 20px for credit at bottom, divide the rest for 5 guide items
        remaining = H - y - 20
        step      = max(remaining // (len(guide) + 1), 14)
        _t(p, "GUIDE", px, y + step - 2, TEXT_LO, 0.30)
        for i, (k, v) in enumerate(guide):
            gy = y + step + (i + 1) * step - 2
            if gy < H - 22:          # safety guard
                _t(p, f"  {k}  ->  {v}", px, gy, TEXT_HI, 0.30)

        # ── [9] CREDIT (last 20px) ────────────────────────────────────────────
        _div(p, H - 20, PW, px)
        _t(p, "By  Dilip Kumar", px, H - 7, (72, 72, 88), 0.29)

        # ── Compose ──────────────────────────────────────────────────────────
        combined = np.hstack([frame, p])
        cv2.imshow("Gesture Robot Control  |  Dilip Kumar", combined)
        cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = GestureControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
