#!/usr/bin/env python3
"""Render 王新峰 as a transparent PNG using Liu Jian Mao Cao font."""
import os
from PIL import Image, ImageDraw, ImageFont

WORK = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(WORK, 'LiuJianMaoCao.ttf')
OUT  = os.path.join(WORK, 'signature_wxf.png')
TEXT = '王新峰'
SIZE = 256
COLOR = (10, 61, 124, 255)

font = ImageFont.truetype(FONT, SIZE)
tmp = Image.new('RGBA', (10, 10))
bbox = ImageDraw.Draw(tmp).textbbox((0, 0), TEXT, font=font)
w = bbox[2] - bbox[0]
h = bbox[3] - bbox[1]
pad = 16
img = Image.new('RGBA', (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
ImageDraw.Draw(img).text((pad - bbox[0], pad - bbox[1]), TEXT, font=font, fill=COLOR)
img.save(OUT)
print(f'wrote {OUT}  {img.size}')
