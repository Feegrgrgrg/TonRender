from captcha.image import ImageCaptcha
from PIL import Image
import random
import string

def generate_random_text(length=6):
    """Генерация случайного текста для капчи."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_captcha():
    """Генерация и отображение изображения капчи с случайным текстом."""
    captcha_text = generate_random_text()
    image = ImageCaptcha(width=280, height=90)
    captcha_image = image.generate_image(captcha_text)
    

