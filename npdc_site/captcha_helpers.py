import random
from captcha.conf import settings as captcha_settings


def mixed_char_challenge():
    """Generate a mixed-case CAPTCHA string using configured characters."""
    chars = getattr(
        captcha_settings,
        "CAPTCHA_CHARS",
        "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789",
    )
    length = getattr(captcha_settings, "CAPTCHA_LENGTH", 6)
    challenge = "".join(random.choice(chars) for _ in range(length))
    return challenge, challenge
