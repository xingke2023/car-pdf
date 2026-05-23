#!/usr/bin/env python3
"""
替换 PDF 第2页和第13页中的"洋葱检"品牌信息
方案：白色矩形遮盖 + PIL 渲染新文字贴图
"""
import fitz
from PIL import Image, ImageDraw, ImageFont
import io

PDF   = "template_decrypted.pdf"
FONT_R = "NotoSansSC-Regular.otf"
CO    = "广州万俊机动车鉴定评估有限公司"
CO_S  = "万俊检测"

doc = fitz.open(PDF)

def make_text_patch(text, fontsize_pt, width_pt, height_pt, dpi=150,
                    fg=(0,0,0), bg=(255,255,255)):
    """用 PIL 把文字渲染成 PNG bytes，尺寸按 PDF pt 换算"""
    scale = dpi / 72
    w = max(1, int(width_pt  * scale))
    h = max(1, int(height_pt * scale))
    img = Image.new("RGB", (w, h), bg)
    d   = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_R, int(fontsize_pt * scale))
    d.text((0, 0), text, font=font, fill=fg)
    buf = io.BytesIO()
    img.save(buf, format="PNG", dpi=(dpi, dpi))
    return buf.getvalue()

def cover_write(page, x0, y0, x1, y1, text, fontsize=9.0, pad=1):
    """遮盖区域，用 PIL 渲染的文字图片覆盖"""
    rect = fitz.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad)
    # 白色遮盖
    page.draw_rect(rect, color=(1,1,1), fill=(1,1,1), width=0)
    # 文字贴图（高度给足一行）
    w = x1 - x0
    h = y1 - y0 + 2
    png = make_text_patch(text, fontsize, w, h)
    page.insert_image(fitz.Rect(x0, y0 - 1, x1, y1 + 1),
                      stream=png, overlay=True)

# ═══════════════════════════════════════════════════════
# 第 2 页（index=1）
# ═══════════════════════════════════════════════════════
p2 = doc[1]

cover_write(p2, 95.4, 416.9, 537.8, 425.9,
    f"{CO_S}检测标准等相关检测标准综合评估而成，检测结果仅代表{CO_S}检测评估结果。最终解释权归{CO_S}所有")

cover_write(p2, 57.5, 433.4, 380.0, 442.4,
    f"（{CO}）")

cover_write(p2, 42.5, 550.2, 380.0, 559.2,
    f"检测单位：{CO}")

# 插入透明公章（不遮盖底部文字）
p2.insert_image(fitz.Rect(104, 562, 192, 647), filename="微信图片_20260511113209_84_195.png", overlay=True)

# 删除右下角二维码及扫码查看信息文字
p2.draw_rect(fitz.Rect(478, 550, 565, 658), color=(1,1,1), fill=(1,1,1), width=0)

# ═══════════════════════════════════════════════════════
# 第 13 页（index=12）
# ═══════════════════════════════════════════════════════
p13 = doc[12]

cover_write(p13, 42.5, 151.2, 546.4, 160.2,
    f"温馨提示: 1、本服务由{CO}提供。 2、{CO_S}对指定车辆进行不解体静态检测，即车辆处于")

cover_write(p13, 42.5, 241.2, 550.5, 250.2,
    f"\"受限\"字样，如检测过程中车辆某检测项受外部环境或其他原因影响导致无法检测，报告中此检测项将展示\"受限\"字样；{CO_S}")

cover_write(p13, 42.5, 259.2, 550.3, 268.2,
    f"不对以上检测项产生的任何疑问负责。 7、如对检测标准有异议或需要对检测报告进行解读，请联系{CO_S}客服。 8、本公司检")

cover_write(p13, 42.5, 277.2, 550.3, 286.2,
    f"测标准 GB/T-30323-2013二手车鉴定评估技术规范 + T/CADA18-2021 乘用车鉴定评估技术规范 + {CO_S}检测标准等")

cover_write(p13, 42.5, 295.5, 550.2, 304.5,
    f"相关检测标准综合评估而成，检测结果仅代表{CO_S}检测评估结果。最终解释权归{CO_S}所有（{CO}")

cover_write(p13, 42.5, 313.5, 200.0, 322.5, "）")

doc.saveIncr()
print(f"品牌替换完成，已保存 {PDF}")
