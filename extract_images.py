#!/usr/bin/env python3
"""
Step 1: 从PDF提取需要替换的大图，存入 extracted_images/ 文件夹
用法: python3 extract_images.py [pdf文件]
"""
import fitz
import os
import sys

PDF = sys.argv[1] if len(sys.argv) > 1 else "authfile1852026011497984810(1).pdf"
OUT_DIR = "extracted_images"
os.makedirs(OUT_DIR, exist_ok=True)

doc = fitz.open(PDF)

# 只从第一页提取（其余页共享相同xref）
page = doc[0]
images = page.get_images(full=True)

# 按尺寸过滤：只提取大图（宽或高 > 400px），跳过小图标
large_images = []
for img in images:
    xref, w, h, name = img[0], img[2], img[3], img[7]
    if w > 400 or h > 400:
        large_images.append((xref, w, h, name))

print(f"找到 {len(large_images)} 张大图（可替换）：\n")

for xref, w, h, name in large_images:
    # 提取图片数据
    img_info = doc.extract_image(xref)
    ext = img_info["ext"]
    img_data = img_info["image"]

    out_path = os.path.join(OUT_DIR, f"{name}.{ext}")
    with open(out_path, "wb") as f:
        f.write(img_data)

    orient = "横" if w > h else "竖"
    print(f"  {name:5s}  {w}x{h} ({orient})  →  {out_path}")

print(f"\n完成！图片已导出到 {OUT_DIR}/")
print("\n操作说明：")
print("  1. 用你的新照片替换 extracted_images/ 里对应的文件（保持文件名不变）")
print("  2. 运行 python3 replace_images.py 生成新PDF")
