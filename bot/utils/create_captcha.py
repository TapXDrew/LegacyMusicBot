
from captcha.image import ImageCaptcha
from captcha.audio import AudioCaptcha
import base64
import random
import json
import socket    
 

number_list = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

alphabet_lowercase = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']

alphabet_uppercase = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']


def create_random_captcha_text(captcha_string_size=6):

    captcha_string_list = []

    base_char = alphabet_lowercase + alphabet_uppercase + number_list

    for i in range(captcha_string_size):
        char = random.choice(base_char)
        captcha_string_list.append(char)

    captcha_string = ''  
    for item in captcha_string_list:
        captcha_string += str(item)

    return captcha_string


def create_random_digital_text(captcha_string_size=10):

    captcha_string_list = []
    for i in range(captcha_string_size):
        char = random.choice(number_list)
        captcha_string_list.append(char)
        
    captcha_string = ''  
    for item in captcha_string_list:
        captcha_string += str(item)

    return captcha_string


def create_image_captcha(captcha_text):
    image_captcha = ImageCaptcha()
    image = image_captcha.generate_image(captcha_text)
    image_captcha.create_noise_curve(image, image.getcolors())
    image_captcha.create_noise_dots(image, image.getcolors())
    image_file = "./captcha.png"
    image_captcha.write(captcha_text, image_file)


def create_audio_captcha():
    audio_captcha = AudioCaptcha()
    captcha_text = create_random_digital_text()
    audio_data = audio_captcha.generate(captcha_text)
    audio_file = "./captcha_audio.wav"
    audio_captcha.write(captcha_text, audio_file)


if __name__ == '__main__':
    captcha_text = create_random_captcha_text()
    print(captcha_text)
    create_image_captcha(captcha_text)