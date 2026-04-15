#!/usr/bin/env python3
"""
把一套照片批量套入PDF模板
照片命名: 01.jpg, 02.jpg, ..., 25.jpg（或 png/webp）
放在 photos/ 文件夹中

用法:
  python3 apply_photos.py                    # 使用 photos/ 文件夹
  python3 apply_photos.py my_photos/        # 指定照片文件夹
  python3 apply_photos.py photos/ out.pdf   # 指定输出文件名
"""
import fitz
import os
import sys

PDF = "authfile1852026011497984810(1).pdf"
PHOTOS_DIR = sys.argv[1] if len(sys.argv) > 1 else "photos"
OUT_PDF = sys.argv[2] if len(sys.argv) > 2 else "output.pdf"

# 照片编号 → xref 映射（按页面顺序，共25张）
PHOTO_MAP = {
     1: 78,   2: 80,   3: 82,   4: 84,   5: 86,   6: 88,   # 第4页
     7: 90,   8: 92,   9: 94,  10: 96,  11: 98,  12: 100,
    13: 102, 14: 104,                                         # 第5页
    15: 106, 16: 108, 17: 110, 18: 112, 19: 114, 20: 116,
    21: 118, 22: 120,                                         # 第6页
    23: 122, 24: 124, 25: 126,                               # 第7页
}

if not os.path.isdir(PHOTOS_DIR):
    print(f"错误：找不到照片文件夹 '{PHOTOS_DIR}'")
    print(f"请创建 {PHOTOS_DIR}/ 文件夹，放入命名为 01.jpg~25.jpg 的照片")
    sys.exit(1)

def find_photo(num: int) -> str | None:
    """查找编号对应的照片文件，支持 jpg/jpeg/png/webp/heic"""
    for ext in ["jpg", "jpeg", "png", "webp", "heic", "JPG", "JPEG", "PNG", "HEIC"]:
        p = os.path.join(PHOTOS_DIR, f"{num:02d}.{ext}")
        if os.path.exists(p):
            return p
    return None

doc = fitz.open(PDF)
replaced, skipped, missing = 0, 0, []

print(f"照片来源: {PHOTOS_DIR}/")
print(f"PDF模板:  {PDF}")
print(f"输出文件: {OUT_PDF}\n")

for num, xref in sorted(PHOTO_MAP.items()):
    photo = find_photo(num)
    if photo is None:
        print(f"  [ ] #{num:02d}  ← 未找到照片（跳过）")
        missing.append(num)
        skipped += 1
        continue
    try:
        doc.replace_image(xref, filename=photo)
        print(f"  [✓] #{num:02d}  ← {os.path.basename(photo)}")
        replaced += 1
    except Exception as e:
        print(f"  [✗] #{num:02d}  替换失败: {e}")
        skipped += 1

doc.save(OUT_PDF, deflate=True)

print(f"\n完成！替换 {replaced} 张，跳过 {skipped} 张")
if missing:
    print(f"缺少照片编号: {missing}")
print(f"输出: {OUT_PDF}")
