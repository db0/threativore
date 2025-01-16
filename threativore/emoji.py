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
                    self.emoji_cache[emoji["custom_emoji"]["shortcode"]] = emoji["custom_emoji"]
                logger.debug(f"Updated emoji cache with {len(self.emoji_cache)} emojis")
            except Exception as e:
                logger.error(f"Failed to update emoji cache: {e}")
            finally:
                logger.debug("Sleeping for 5 minutes")
                time.sleep(300)

    # TODO: Move to pythorhead?
    def get_emoji_url(self, emoji_shortcode):
        return self.emoji_cache.get(emoji_shortcode, {}).get("image_url")
                
    # TODO: Move to pythorhead?
    def get_emoji_markdown(self, emoji_shortcode):
        if emoji_shortcode not in self.emoji_cache:
            return ""
        emoji_dict = self.emoji_cache[emoji_shortcode]
        return f'![{emoji_dict["alt_text"]}]({emoji_dict["image_url"]} "{emoji_dict["shortcode"]}") '
                
lemmy_emoji = LemmyEmoji(base_lemmy)
