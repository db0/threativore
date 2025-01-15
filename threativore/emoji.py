import threading
import time
from loguru import logger
from threativore.lemmy import base_lemmy

class LemmyEmoji:

    emoji_cache: dict = {}

    def __init__(self, _base_lemmy):
        self.lemmy = _base_lemmy.lemmy
        self.emoji_cache_thread = threading.Thread(target=self.fetch_custom_emoji, args=(), daemon=True)
        self.emoji_cache_thread.start()
    
    def fetch_custom_emoji(self):
        while True:
            try:
                ce = self.lemmy.emoji.get()
                for emoji in ce:
                    self.emoji_cache[emoji["custom_emoji"]["shortcode"]] = emoji["custom_emoji"]["image_url"]
                logger.debug(f"Updated emoji cache with {len(self.emoji_cache)} emojis")
            except Exception as e:
                logger.error(f"Failed to update emoji cache: {e}")
            finally:
                logger.debug("Sleeping for 5 minutes")
                time.sleep(300)
                
lemmy_emoji = LemmyEmoji(base_lemmy)
