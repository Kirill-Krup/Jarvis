import asyncio
import os
import tempfile
import pygame
import edge_tts

from config.profile_manager import ProfileManager


class Speaker:

    def __init__(self):
        pygame.mixer.init()
        self.profile = ProfileManager()
        print("Speaker готов ✓")

    def speak(self, text: str):
        asyncio.run(self._speak_async(text))

    async def _speak_async(self, text: str):
        try:
            print(f"Джарвис: {text}")

            communicate = edge_tts.Communicate(
                text=text,
                voice=self.profile.current["voice"],
                rate=self.profile.current["speed"],
                pitch=self.profile.current["pitch"],
            )

            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".mp3"
            ) as tmp:
                tmp_path = tmp.name

            await communicate.save(tmp_path)

            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            os.unlink(tmp_path)

        except Exception as e:
            print(f"Ошибка Speaker: {e}")