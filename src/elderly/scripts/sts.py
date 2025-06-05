import subprocess
import threading
import time
import os
import hashlib
import pygame
from pathlib import Path

import rospy
from std_msgs.msg import String

# For gTTS functionality
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# For offline audio playback
try:
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class EnhancedTTSManager:
    """Enhanced Text-to-Speech Manager for STS Robot with Thai support"""
    
    def __init__(self, cache_dir="/tmp/robot_tts_cache", default_lang="en"):
        self.speaking = False
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.default_lang = default_lang
        
        # Audio output settings
        self.audio_device = None  # Will be set based on available devices
        
        # Check available TTS methods
        self.gtts_available = GTTS_AVAILABLE
        self.pygame_available = PYGAME_AVAILABLE
        self.espeak_available = self._check_espeak()
        
        # Initialize audio system
        if self.pygame_available:
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                rospy.loginfo("TTS initialized with pygame for audio playback")
            except Exception as e:
                rospy.logwarn(f"Pygame init failed: {e}")
                self.pygame_available = False
        
        # Log available TTS methods
        methods = []
        if self.gtts_available:
            methods.append("gTTS (online/cached)")
        if self.espeak_available:
            methods.append("espeak")
        if self.pygame_available:
            methods.append("pygame audio")
        
        rospy.loginfo(f"TTS methods available: {', '.join(methods) if methods else 'None'}")
        
        # Pre-generate common robot phrases
        self.pre_generate_common_phrases()
    
    def _check_espeak(self):
        """Check if espeak is available"""
        try:
            subprocess.run(['espeak', '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _detect_language(self, text):
        """Detect if text contains Thai characters"""
        if any('\u0e00' <= char <= '\u0e7f' for char in text):
            return 'th'
        return 'en'
    
    def _get_cache_filename(self, text, lang):
        """Generate cache filename based on text and language"""
        text_hash = hashlib.md5(f"{text}_{lang}".encode()).hexdigest()
        return self.cache_dir / f"{text_hash}.mp3"
    
    def _generate_gtts_audio(self, text, lang):
        """Generate audio using gTTS and save to cache"""
        if not self.gtts_available:
            return None
        
        cache_file = self._get_cache_filename(text, lang)
        
        # Return cached file if exists
        if cache_file.exists():
            return str(cache_file)
        
        try:
            # Generate TTS audio
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(str(cache_file))
            rospy.logdebug(f"Generated TTS audio: {cache_file}")
            return str(cache_file)
        except Exception as e:
            rospy.logwarn(f"gTTS generation failed: {e}")
            return None
    
    def _play_audio_file(self, audio_file):
        """Play audio file using pygame or system player"""
        try:
            if self.pygame_available:
                # Use pygame for better control
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                
                # Wait for playback to finish
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            else:
                # Fallback to system player
                subprocess.run(['aplay', audio_file], capture_output=True, check=False)
        except Exception as e:
            rospy.logwarn(f"Audio playback failed: {e}")
    
    def _speak_with_espeak(self, text, lang):
        """Fallback to espeak for TTS"""
        if not self.espeak_available:
            return False
        
        try:
            voice = 'th' if lang == 'th' else 'en+m3'
            speed = '140' if lang == 'th' else '160'
            
            subprocess.run([
                'espeak', 
                '-s', speed,
                '-a', '200',        
                '-p', '50',         
                '-g', '5' if lang == 'th' else '3',
                '-v', voice,
                text
            ], capture_output=True, check=False)
            return True
        except Exception as e:
            rospy.logwarn(f"espeak failed: {e}")
            return False
    
    def pre_generate_common_phrases(self):
        """Pre-generate audio for common robot phrases"""
        common_phrases = {
            'en': [
                "STS Robot starting up. Please wait.",
                "All motor controllers connected successfully.",
                "STS Robot ready for operation. Use buttons to control the system.",
                "Ready position. Press both buttons to start assistance sequence.",
                "Preparing to assist. Please position yourself.",
                "Assisting you to stand. Hold on tight.",
                "Assisting you to sit down. Take your time.",
                "Standing mode activated.",
                "Sitting mode activated.",
                "Assistance sequence activated. Please hold on.",
                "System stopped. Ready for next command.",
                "Warning: motor controllers not found."
            ],
            'th': [
                "หุ่นยนต์ช่วยเหลือกำลังเริ่มทำงาน กรุณารอสักครู่",
                "เชื่อมต่อมอเตอร์ครบทุกตัวแล้ว",
                "หุ่นยนต์พร้อมใช้งาน กดปุ่มเพื่อควบคุมระบบ",
                "ท่าพร้อม กดปุ่มทั้งสองเพื่อเริ่มช่วยเหลือ",
                "กำลังเตรียมช่วยเหลือ กรุณาจัดท่า",
                "กำลังช่วยคุณลุกขึ้นยืน จับให้แน่น",
                "กำลังช่วยคุณนั่งลง ใช้เวลาตามสบาย",
                "เปิดโหมดยืนแล้ว",
                "เปิดโหมดนั่งแล้ว",
                "เริ่มลำดับการช่วยเหลือ กรุณาจับให้แน่น",
                "หยุดระบบแล้ว พร้อมรับคำสั่งถัดไป"
            ]
        }
        
        if not self.gtts_available:
            rospy.loginfo("gTTS not available, skipping phrase pre-generation")
            return
        
        rospy.loginfo("Pre-generating common phrases...")
        
        for lang, phrases in common_phrases.items():
            for phrase in phrases:
                try:
                    self._generate_gtts_audio(phrase, lang)
                except Exception as e:
                    rospy.logwarn(f"Failed to pre-generate '{phrase}': {e}")
        
        rospy.loginfo("Phrase pre-generation completed")
    
    def speak_async(self, text, lang=None):
        """Speak text asynchronously without blocking"""
        if not text:
            return
        
        # Don't interrupt if already speaking
        if self.speaking:
            rospy.logdebug(f"TTS busy, skipping: {text}")
            return
        
        if lang is None:
            lang = self._detect_language(text)
        
        thread = threading.Thread(target=self._speak_thread, args=(text, lang))
        thread.daemon = True
        thread.start()
    
    def speak_sync(self, text, lang=None):
        """Speak text synchronously (blocks until finished)"""
        if not text:
            return
        
        if lang is None:
            lang = self._detect_language(text)
        
        self._speak_thread(text, lang)
    
    def _speak_thread(self, text, lang):
        """Internal method to handle TTS in separate thread"""
        self.speaking = True
        
        try:
            # Try gTTS first (better quality, especially for Thai)
            audio_file = self._generate_gtts_audio(text, lang)
            if audio_file:
                self._play_audio_file(audio_file)
                rospy.logdebug(f"TTS spoke (gTTS): {text}")
            else:
                # Fallback to espeak
                if self._speak_with_espeak(text, lang):
                    rospy.logdebug(f"TTS spoke (espeak): {text}")
                else:
                    rospy.logwarn(f"All TTS methods failed for: {text}")
        
        except Exception as e:
            rospy.logwarn(f"TTS error: {e}")
        finally:
            self.speaking = False
    
    def speak_urgent(self, text, lang=None):
        """Speak urgent messages immediately (interrupts current speech)"""
        if not text:
            return
        
        # Stop current audio
        if self.pygame_available:
            pygame.mixer.music.stop()
        
        # Kill espeak processes
        try:
            subprocess.run(['pkill', 'espeak'], capture_output=True, check=False)
        except:
            pass
        
        if lang is None:
            lang = self._detect_language(text)
        
        # Speak immediately
        self._speak_thread(text, lang)
    
    def is_speaking(self):
        """Check if TTS is currently speaking"""
        return self.speaking
    
    def set_audio_output_device(self, device_name=None):
        """Set audio output device (for external speakers)"""
        # This would require additional implementation based on your audio setup
        # For Bluetooth: you'd need to pair and connect the BT speaker first
        # For USB: the device should be automatically detected
        pass
    
    def cleanup(self):
        """Cleanup pygame resources"""
        if self.pygame_available:
            pygame.mixer.quit()


# Example usage in your STSRobot class:
class STSRobotWithEnhancedTTS:
    def __init__(self):
        # ... your existing initialization ...
        
        # Initialize enhanced TTS with Thai support
        self.tts = EnhancedTTSManager(default_lang="th")  # Set Thai as default
        
        # ... rest of your initialization ...
    
    def handle_stage_tts(self):
        """Handle TTS announcements for stage changes with Thai support"""
        if self.stage != self.last_stage:
            # English messages
            stage_messages_en = {
                0: "Ready position. Press both buttons to start assistance sequence.",
                1: "Preparing to assist. Please position yourself.",
                2: "Assisting you to stand. Hold on tight.",
                3: "Assisting you to sit down. Take your time."
            }
            
            # Thai messages
            stage_messages_th = {
                0: "ท่าพร้อม กดปุ่มทั้งสองเพื่อเริ่มช่วยเหลือ",
                1: "กำลังเตรียมช่วยเหลือ กรุณาจัดท่า",
                2: "กำลังช่วยคุณลุกขึ้นยืน จับให้แน่น",
                3: "กำลังช่วยคุณนั่งลง ใช้เวลาตามสบาย"
            }
            
            # Use Thai by default, fallback to English
            message = stage_messages_th.get(self.stage) or stage_messages_en.get(self.stage, f"Stage {self.stage}")
            self.tts.speak_async(message)
            self.last_stage = self.stage
