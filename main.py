import cv2
import mediapipe as mp
import numpy as np
import time
import json
import os
import pygame
import threading
import random

CONFIG_FILE = "config.json"

def load_config():
    default_config = {
        "GAMES": {
            "piano_game": False,
            "coins_game": False
        },
        "gpu_mode": False,
        "window_width": 960,
        "window_height": 720
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                if "GAMES" not in user_config:
                    if "piano_game" in user_config or "coins_game" in user_config:
                        user_config["GAMES"] = {
                            "piano_game": user_config.pop("piano_game", False),
                            "coins_game": user_config.pop("coins_game", False)
                        }
                default_config.update(user_config)
                if "GAMES" in user_config:
                    default_config["GAMES"].update(user_config["GAMES"])
                print(f"[OK] Configuration loaded from {CONFIG_FILE}")
        except Exception as e:
            print(f"[WARNING] Error loading configuration: {e}")
            print("[INFO] Using default configuration")
    else:
        print(f"[INFO] {CONFIG_FILE} not found, using default configuration")
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        print(f"[OK] Configuration file created: {CONFIG_FILE}")
    
    return default_config

config = load_config()
WINDOW_WIDTH = config["window_width"]
WINDOW_HEIGHT = config["window_height"]

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

def initialize_hands():
    try:
        hands = mp_hands.Hands(
            static_image_mode=False
        )
        mode = "GPU" if config["gpu_mode"] else "CPU"
        print(f"[INFO] MediaPipe Hands initialized (mode {mode})")
        return hands
    except Exception as e:
        print(f"[WARNING] Error initializing MediaPipe: {e}")
        hands = mp_hands.Hands(
            static_image_mode=False
        )
        return hands

hands = initialize_hands()

def init_piano():
    if config["GAMES"]["piano_game"]:
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        return True
    return False

def generate_tone(frequency, duration=0.2, sample_rate=22050):
    frames = int(duration * sample_rate)
    arr = np.zeros((frames, 2), dtype=np.int16)
    max_sample = 2**(16 - 1) - 1
    
    for i in range(frames):
        t = float(i) / sample_rate
        wave = 4096 * np.sin(2 * np.pi * frequency * t)
        envelope = 1.0
        if i < frames * 0.1:
            envelope = i / (frames * 0.1)
        elif i > frames * 0.7:
            envelope = 1.0 - ((i - frames * 0.7) / (frames * 0.3))
        wave *= envelope
        arr[i][0] = int(np.clip(wave, -max_sample, max_sample))
        arr[i][1] = int(np.clip(wave, -max_sample, max_sample))
    return arr

def play_note(frequency, duration=0.2):
    if not config["GAMES"]["piano_game"]:
        return
    try:
        tone = generate_tone(frequency, duration)
        sound = pygame.sndarray.make_sound(tone)
        sound.play()
    except:
        pass

piano_notes = {
    "right": {
        0: 261.63,
        1: 293.66,
        2: 329.63,
        3: 349.23,
        4: 392.00
    },
    "left": {
        0: 440.00,
        1: 493.88,
        2: 523.25,
        3: 587.33,
        4: 659.25
    }
}

previous_finger_states = {}

def init_coins_game():
    return {
        "score": 0,
        "coins": [],
        "ball": {"x": WINDOW_WIDTH // 2, "y": 25, "vx": random.choice([-3, 3]), "vy": 3, "radius": 20},
        "game_over": False,
        "restart_time": None,
        "last_coin_spawn": time.time()
    }

def spawn_coin():
    return {
        "x": random.randint(30, WINDOW_WIDTH - 30),
        "y": random.randint(30, WINDOW_HEIGHT - 30),
        "radius": 25,
        "collected": False
    }

def check_collision(point_x, point_y, obj_x, obj_y, obj_radius):
    distance = np.sqrt((point_x - obj_x)**2 + (point_y - obj_y)**2)
    return distance < obj_radius

def update_ball(game_state):
    if game_state["game_over"]:
        return
    
    ball = game_state["ball"]
    ball["x"] += ball["vx"]
    ball["y"] += ball["vy"]
    
    if ball["x"] - ball["radius"] <= 0 or ball["x"] + ball["radius"] >= WINDOW_WIDTH:
        ball["vx"] = -ball["vx"]
        ball["x"] = max(ball["radius"], min(WINDOW_WIDTH - ball["radius"], ball["x"]))
    
    if ball["y"] - ball["radius"] <= 0 or ball["y"] + ball["radius"] >= WINDOW_HEIGHT:
        ball["vy"] = -ball["vy"]
        ball["y"] = max(ball["radius"], min(WINDOW_HEIGHT - ball["radius"], ball["y"]))

coins_game_state = None

def get_finger_states(landmarks, is_right_hand=True):
    finger_tips = [4, 8, 12, 16, 20]
    finger_pips = [3, 6, 10, 14, 18]
    finger_mcps = [2, 5, 9, 13, 17]
    wrist = 0
    
    finger_states = [False] * 5
    
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]
    thumb_mcp = landmarks[2]
    
    if is_right_hand:
        finger_states[0] = thumb_tip.x > thumb_ip.x
    else:
        finger_states[0] = thumb_tip.x < thumb_ip.x
    
    if not finger_states[0]:
        finger_states[0] = thumb_tip.y < thumb_ip.y and thumb_tip.y < thumb_mcp.y
    
    for i in range(1, 5):
        finger_states[i] = landmarks[finger_tips[i]].y < landmarks[finger_pips[i]].y
    
    return finger_states

def count_fingers(landmarks, is_right_hand=True):
    finger_states = get_finger_states(landmarks, is_right_hand)
    return sum(finger_states)

def detect_all_cameras():
    available_cameras = []
    backends = [
        (cv2.CAP_DSHOW, "DirectShow"),
        (cv2.CAP_MSMF, "Media Foundation"),
        (cv2.CAP_V4L2, "V4L2"),
        (cv2.CAP_ANY, "Any")
    ]
    
    print("[INFO] Scanning for all available cameras...")
    for camera_index in range(10):
        for backend_id, backend_name in backends:
            try:
                test_cap = cv2.VideoCapture(camera_index, backend_id)
                if test_cap.isOpened():
                    ret, test_frame = test_cap.read()
                    if ret and test_frame is not None:
                        available_cameras.append({
                            "index": camera_index,
                            "backend_id": backend_id,
                            "backend_name": backend_name
                        })
                        print(f"[OK] Camera {camera_index} found using {backend_name}")
                        test_cap.release()
                        break
                else:
                    test_cap.release()
            except:
                pass
    
    return available_cameras

def switch_camera(camera_list, current_index, cap):
    if not camera_list or current_index >= len(camera_list):
        return None, current_index
    
    if cap is not None:
        cap.release()
        time.sleep(0.2)
    
    camera_info = camera_list[current_index]
    new_cap = cv2.VideoCapture(camera_info["index"], camera_info["backend_id"])
    
    if new_cap.isOpened():
        new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, WINDOW_WIDTH)
        new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, WINDOW_HEIGHT)
        new_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        time.sleep(0.3)
        print(f"[OK] Switched to camera {camera_info['index']} ({camera_info['backend_name']})")
        return new_cap, current_index
    else:
        print(f"[WARNING] Could not switch to camera {camera_info['index']}")
        return None, current_index

def main():
    print("=" * 60)
    print("Hand Detection - Finger Counter")
    print("=" * 60)
    
    available_cameras = detect_all_cameras()
    
    if not available_cameras:
        print("\n[ERROR] No cameras found.")
        print("Please check:")
        print("  - Webcam is connected and working")
        print("  - No other application is using the webcam")
        print("  - Webcam permissions are enabled")
        return
    
    print(f"\n[INFO] Found {len(available_cameras)} camera(s) available")
    
    current_camera_idx = 0
    cap = None
    cap, current_camera_idx = switch_camera(available_cameras, current_camera_idx, cap)
    
    if cap is None or not cap.isOpened():
        print("\n[ERROR] Could not open webcam.")
        return
    
    ret, test_frame = cap.read()
    if not ret or test_frame is None:
        print("\n[WARNING] Camera opened but cannot read frames.")
        print("Trying to reinitialize...")
        cap.release()
        time.sleep(1)
        cap, current_camera_idx = switch_camera(available_cameras, current_camera_idx, None)
        if cap is None:
            print("[ERROR] Could not reinitialize camera.")
            return
        time.sleep(0.5)
    
    print("[OK] Webcam initialized successfully!")
    
    piano_initialized = init_piano()
    if config["GAMES"]["piano_game"] and piano_initialized:
        print("[OK] Piano mode initialized")
    
    cv2.namedWindow('Hand Detection', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Hand Detection', WINDOW_WIDTH, WINDOW_HEIGHT)
    
    print("\n" + "=" * 60)
    print("[OK] Application started successfully!")
    print("=" * 60)
    print(f"\n[CONFIG] Piano Game: {'Enabled' if config['GAMES']['piano_game'] else 'Disabled'}")
    print(f"[CONFIG] Coins Game: {'Enabled' if config['GAMES']['coins_game'] else 'Disabled'}")
    print(f"[CONFIG] GPU: {'Enabled' if config['gpu_mode'] else 'Disabled (CPU)'}")
    print("=" * 60)
    
    global coins_game_state
    if config["GAMES"]["coins_game"]:
        coins_game_state = init_coins_game()
        print("[OK] Coins game initialized")
    print("\n[INFO] Show your hand to the camera")
    print("[CONTROLS]")
    print("  - Press 'q' to quit")
    if len(available_cameras) > 1:
        print("  - Press 'd' or RIGHT arrow to switch to next camera")
        print("  - Press 'a' or LEFT arrow to switch to previous camera")
        print("  - Press number keys (0-9) to select camera directly")
    print("")
    
    consecutive_failures = 0
    max_failures = 10
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                print("\n[ERROR] Could not read frame from webcam after multiple attempts.")
                print("Closing application...")
                break
            
            time.sleep(0.1)
            continue
        
        consecutive_failures = 0
        
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (WINDOW_WIDTH, WINDOW_HEIGHT))
        
        if config["GAMES"]["coins_game"] and coins_game_state:
            if coins_game_state["game_over"]:
                if coins_game_state["restart_time"] is None:
                    coins_game_state["restart_time"] = time.time()
                elif time.time() - coins_game_state["restart_time"] >= 5.0:
                    coins_game_state = init_coins_game()
                    print("[INFO] Game restarted")
                else:
                    remaining = int(5 - (time.time() - coins_game_state["restart_time"]))
                    text = f"GAME OVER - Restarting in {remaining}s"
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 1.5
                    thickness = 3
                    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
                    text_x = (WINDOW_WIDTH - text_width) // 2
                    text_y = WINDOW_HEIGHT // 2
                    cv2.putText(frame, text, (text_x, text_y), font, font_scale, (0, 0, 255), thickness)
            else:
                update_ball(coins_game_state)
                
                if time.time() - coins_game_state["last_coin_spawn"] > 2.0:
                    coins_game_state["coins"].append(spawn_coin())
                    coins_game_state["last_coin_spawn"] = time.time()
                
                coins_game_state["coins"] = [coin for coin in coins_game_state["coins"] if not coin["collected"]]
                for coin in coins_game_state["coins"]:
                    cv2.circle(frame, (coin["x"], coin["y"]), coin["radius"], (0, 255, 255), -1)
                    cv2.circle(frame, (coin["x"], coin["y"]), coin["radius"], (255, 215, 0), 3)
                
                ball = coins_game_state["ball"]
                cv2.circle(frame, (int(ball["x"]), int(ball["y"])), ball["radius"], (0, 0, 0), -1)
                cv2.circle(frame, (int(ball["x"]), int(ball["y"])), ball["radius"], (255, 255, 255), 2)
                
                score_text = f"Score: {coins_game_state['score']}"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 1.5
                thickness = 3
                (text_width, text_height), baseline = cv2.getTextSize(score_text, font, font_scale, thickness)
                score_x = WINDOW_WIDTH - text_width - 20
                score_y = 50
                cv2.rectangle(frame, (score_x - 10, score_y - text_height - 10), 
                            (score_x + text_width + 10, score_y + 10), (0, 0, 0), -1)
                cv2.putText(frame, score_text, (score_x, score_y),
                          font, font_scale, (255, 255, 255), thickness)
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = hands.process(rgb_frame)
        
        total_fingers = 0
        hand_count = 0
        
        if results.multi_hand_landmarks:
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                hand_label = results.multi_handedness[idx].classification[0].label
                inverted_label = "Left" if hand_label == "Right" else "Right"
                is_right = inverted_label == "Right"
                hand_key = "right" if is_right else "left"
                
                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp_drawing.DrawingSpec(color=(0, 0, 255), thickness=2)
                )
                
                finger_states = get_finger_states(hand_landmarks.landmark, is_right)
                fingers = sum(finger_states)
                total_fingers += fingers
                hand_count += 1
                
                h, w, c = frame.shape
                cx = int(hand_landmarks.landmark[0].x * w)
                cy = int(hand_landmarks.landmark[0].y * h)
                
                hand_id = f"{hand_key}_{idx}"
                
                if config["GAMES"]["piano_game"]:
                    if hand_id not in previous_finger_states:
                        previous_finger_states[hand_id] = finger_states.copy()
                    else:
                        for finger_idx in range(5):
                            if previous_finger_states[hand_id][finger_idx] and not finger_states[finger_idx]:
                                note_freq = piano_notes[hand_key][finger_idx]
                                threading.Thread(target=play_note, args=(note_freq,), daemon=True).start()
                        previous_finger_states[hand_id] = finger_states.copy()
                    
                    label_text = inverted_label.upper()
                    cv2.putText(frame, label_text, (cx - 40, cy - 60),
                              cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 3)
                
                cv2.putText(frame, f"{fingers} fingers", (cx - 50, cy - 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                if config["GAMES"]["coins_game"] and coins_game_state and not coins_game_state["game_over"]:
                    for landmark in hand_landmarks.landmark:
                        px = int(landmark.x * w)
                        py = int(landmark.y * h)
                        
                        for coin in coins_game_state["coins"][:]:
                            if not coin.get("collected", False) and check_collision(px, py, coin["x"], coin["y"], coin["radius"]):
                                coin["collected"] = True
                                coins_game_state["score"] += 1
                                coins_game_state["coins"].remove(coin)
                                break
                        
                        if coins_game_state["game_over"]:
                            break
                        
                        ball = coins_game_state["ball"]
                        if check_collision(px, py, int(ball["x"]), int(ball["y"]), ball["radius"]):
                            coins_game_state["game_over"] = True
                            coins_game_state["restart_time"] = None
                            print("[GAME] Game Over! Score:", coins_game_state["score"])
                            break
        
        if config["GAMES"]["piano_game"]:
            if results.multi_hand_landmarks:
                active_hand_ids = set()
                for idx in range(len(results.multi_hand_landmarks)):
                    hand_label = results.multi_handedness[idx].classification[0].label
                    inverted_label = "Left" if hand_label == "Right" else "Right"
                    hand_key = "right" if inverted_label == "Right" else "left"
                    active_hand_ids.add(f"{hand_key}_{idx}")
                
                for hand_id in list(previous_finger_states.keys()):
                    if hand_id not in active_hand_ids:
                        del previous_finger_states[hand_id]
            else:
                previous_finger_states.clear()
        
        if not config["GAMES"]["coins_game"]:
            cv2.rectangle(frame, (10, 10), (400, 100), (0, 0, 0), -1)
            cv2.putText(frame, f"Total fingers: {total_fingers}", (20, 50),
                      cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 255), 3)
            cv2.putText(frame, f"Hands: {hand_count}", (20, 85),
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
        
        camera_info_text = f"Camera: {current_camera_idx + 1}/{len(available_cameras)}"
        if len(available_cameras) > 1:
            camera_info_text += " (d/a or arrows to switch)"
        cv2.rectangle(frame, (10, WINDOW_HEIGHT - 80), (400, WINDOW_HEIGHT - 10), (0, 0, 0), -1)
        cv2.putText(frame, camera_info_text, (15, WINDOW_HEIGHT - 50),
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        if not results.multi_hand_landmarks:
            cv2.putText(frame, "No hands detected", (10, WINDOW_HEIGHT - 20),
                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        cv2.imshow('Hand Detection', frame)
        
        full_key = cv2.waitKey(1)
        key = full_key & 0xFF
        
        if key == ord('q') or key == 27:
            print("\n[QUIT] Quitting application...")
            break
        elif len(available_cameras) > 1:
            if key == ord('d') or (full_key == 2555904):
                current_camera_idx = (current_camera_idx + 1) % len(available_cameras)
                cap, current_camera_idx = switch_camera(available_cameras, current_camera_idx, cap)
            elif key == ord('a') or (full_key == 2424832):
                current_camera_idx = (current_camera_idx - 1) % len(available_cameras)
                cap, current_camera_idx = switch_camera(available_cameras, current_camera_idx, cap)
            elif ord('0') <= key <= ord('9'):
                camera_num = key - ord('0')
                if camera_num < len(available_cameras):
                    current_camera_idx = camera_num
                    cap, current_camera_idx = switch_camera(available_cameras, current_camera_idx, cap)
    
    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    
    print("[OK] Application closed successfully.")
    print("Thanks for using Hand Detection - Finger Counter!\n")

if __name__ == "__main__":
    main()

