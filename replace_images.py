#!/usr/bin/env python3
"""
Step 2: 用 extracted_images/ 里的图片替换PDF中对应的大图
用法: python3 replace_images.py [pdf文件] [输出文件]
"""
import fitz
import os
import sys

PDF = sys.argv[1] if len(sys.argv) > 1 else "authfile1852026011497984810(1).pdf"
OUT_PDF = sys.argv[2] if len(sys.argv) > 2 else PDF.replace(".pdf", "_new.pdf")
IMG_DIR = "extracted_images"

doc = fitz.open(PDF)
page = doc[0]
images = page.get_images(full=True)

replaced = 0
skipped = 0

print(f"开始替换图片...\n")

for img in images:
    xref, w, h, name = img[0], img[2], img[3], img[7]
    if w <= 400 and h <= 400:
        continue  # 跳过小图标

    # 查找替换文件（支持 jpg/jpeg/png/webp 等格式）
    replacement = None
    for ext in ["jpg", "jpeg", "png", "webp", "JPG", "JPEG", "PNG"]:
        candidate = os.path.join(IMG_DIR, f"{name}.{ext}")
        if os.path.exists(candidate):
            replacement = candidate
            break

    if replacement is None:
        print(f"  跳过 {name}（未找到替换文件）")
        skipped += 1
        continue

    # 替换图片（保持原始xref，所有页面自动更新）
    try:
        doc.replace_image(xref, filename=replacement)
        print(f"  ✓ {name}  ←  {replacement}")
        replaced += 1
    except Exception as e:
        print(f"  ✗ {name} 替换失败: {e}")
        skipped += 1

doc.save(OUT_PDF, deflate=True)
print(f"\n完成！替换了 {replaced} 张，跳过 {skipped} 张")
print(f"输出文件: {OUT_PDF}")
