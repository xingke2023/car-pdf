#!/usr/bin/env python3
"""
生成新封面并替换 template_decrypted.pdf 第一页
风格：简约浅色，深蓝主色，留白 + 细线装饰
"""
from PIL import Image, ImageDraw, ImageFont
import fitz
import os

PDF_IN  = "template_decrypted.pdf"
FONT_R  = "NotoSansSC-Regular.otf"
FONT_B  = "NotoSansSC-Bold.otf"

COMPANY = "广州国际检机动车鉴定评估有限公司"
TITLE_1 = "检测认证"
TITLE_2 = "评估报告"
SUBTITLE = "VEHICLE INSPECTION & CERTIFICATION REPORT"

# A4 @ 150dpi: 595.28pt * 150/72 = 1240px, 841.89pt * 150/72 = 1754px
DPI   = 150
W, H  = 1240, 1754

# 颜色（RGB）- 浅色调
C_BG     = (250, 251, 253)
C_WHITE  = (255, 255, 255)
C_NAVY   = (110, 140, 180)
C_LIGHT  = (170, 185, 210)
C_LINE   = (220, 228, 240)
C_BRAND  = (90,  125, 170)

def px(pt):
    """PDF pt → 图片 px"""
    return int(pt * DPI / 72)

img = Image.new("RGB", (W, H), C_BG)
d   = ImageDraw.Draw(img)

# ── 字体 ─────────────────────────────────────────
fR  = lambda sz: ImageFont.truetype(FONT_R, px(sz))
fB  = lambda sz: ImageFont.truetype(FONT_B, px(sz))

# ── 顶部细线 ─────────────────────────────────────
d.rectangle([(0, 0), (W, px(4))], fill=C_NAVY)

# ── 底部细线 ─────────────────────────────────────
d.rectangle([(0, H - px(4)), (W, H)], fill=C_NAVY)

# ── 顶部大字 "国际检" 居中 ───────────────────────
brand_text = "国际检"
brand_font = fB(72)
bb_brand = brand_font.getbbox(brand_text)
brand_w = bb_brand[2] - bb_brand[0]
brand_h = bb_brand[3] - bb_brand[1]
brand_x = (W - brand_w) // 2
brand_y = px(70)
d.text((brand_x, brand_y), brand_text, font=brand_font, fill=C_BRAND)

# ── 中央白色卡片 ─────────────────────────────────
cx1, cy1 = px(56), px(260)
cx2, cy2 = W - px(56), px(650)
d.rectangle([(cx1, cy1), (cx2, cy2)], fill=C_WHITE, outline=C_LINE, width=1)

# 卡片左侧深蓝竖线
d.rectangle([(cx1, cy1), (cx1 + px(5), cy2)], fill=C_NAVY)

# ── 主标题 ───────────────────────────────────────
d.text((cx1 + px(28), cy1 + px(40)), TITLE_1, font=fB(54), fill=C_NAVY)
d.text((cx1 + px(28), cy1 + px(108)), TITLE_2, font=fB(54), fill=C_NAVY)

# 卡片内分隔线
sep_y = cy1 + px(185)
d.line([(cx1 + px(20), sep_y), (cx2 - px(20), sep_y)], fill=C_LINE, width=1)

# 英文副标题
d.text((cx1 + px(28), sep_y + px(10)), SUBTITLE, font=fR(8), fill=C_LIGHT)

# 说明文字
d.text((cx1 + px(28), sep_y + px(55)), "本报告依据国家相关标准，对委托车辆进行综合检测评估。", font=fR(8.5), fill=C_LIGHT)
d.text((cx1 + px(28), sep_y + px(76)), "检测结果仅对受检车辆当次状态负责。", font=fR(8.5), fill=C_LIGHT)

# ── 公司区域 ─────────────────────────────────────
sep2_y = px(720)
d.line([(px(56), sep2_y), (W - px(56), sep2_y)], fill=C_LINE, width=1)

d.text((px(56), sep2_y + px(22)), COMPANY, font=fB(15), fill=C_NAVY)
d.text((px(56), sep2_y + px(46)), "检测评估单位", font=fR(8), fill=C_LIGHT)

# 日期
d.text((W - px(185), sep2_y + px(22)), "检测日期：________________", font=fR(8.5), fill=C_LIGHT)

# ── 报告编号（右上角）────────────────────────────
d.text((W - px(180), px(20)), "报告编号：________________", font=fR(7.5), fill=C_LIGHT)

# ── 页码 ─────────────────────────────────────────
pg_text = "1 / 13"
bb = fR(7.5).getbbox(pg_text)
pg_w = bb[2] - bb[0]
d.text(((W - pg_w) // 2, H - px(20)), pg_text, font=fR(7.5), fill=C_LIGHT)

# ── 保存封面图片 ──────────────────────────────────
cover_img = "cover_page.png"
img.save(cover_img, dpi=(DPI, DPI))
print(f"封面图片已生成: {cover_img}")

# ── 替换 PDF 第一页 ───────────────────────────────
doc  = fitz.open(PDF_IN)
page = doc[0]
W_pt = page.rect.width
H_pt = page.rect.height

# 用白色矩形覆盖原有内容
shape = page.new_shape()
shape.draw_rect(page.rect)
shape.finish(fill=(1, 1, 1), color=(1, 1, 1), width=0)
shape.commit()

# 插入新封面图片（铺满全页）
rect = fitz.Rect(0, 0, W_pt, H_pt)
page.insert_image(rect, filename=cover_img)

doc.saveIncr()
print(f"已更新 {PDF_IN} 第一页封面")
