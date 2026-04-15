#!/usr/bin/env python3
"""
生成每页的图片槽位预览图，标注每个槽位的编号
方便用户知道"哪个位置对应哪个名字"
"""
import fitz
import os

PDF = "authfile1852026011497984810(1).pdf"
OUT_DIR = "slot_preview"
os.makedirs(OUT_DIR, exist_ok=True)

# 只关注大图（宽或高 > 400px）
MIN_SIZE = 400

doc = fitz.open(PDF)

# 收集所有大图的 xref → name 映射（从第一页）
xref_to_name = {}
page0 = doc[0]
for img in page0.get_images(full=True):
    xref, w, h, name = img[0], img[2], img[3], img[7]
    if w > MIN_SIZE or h > MIN_SIZE:
        xref_to_name[xref] = name

print(f"共 {len(xref_to_name)} 个大图槽位\n")

for page_num, page in enumerate(doc):
    # 渲染页面为图片（缩放 0.4 倍，足够看清布局）
    mat = fitz.Matrix(0.4, 0.4)
    pix = page.get_pixmap(matrix=mat)

    # 转为可编辑的 fitz.Pixmap（RGB）
    if pix.alpha:
        pix = fitz.Pixmap(fitz.csRGB, pix)

    # 获取每个大图在页面上的位置
    img_dict = page.get_image_rects(full=True)  # 不可用，改用下面方法

    # 用 get_images + get_image_bbox 获取位置
    page_images = page.get_images(full=True)
    scale = 0.4

    labeled = []
    for img in page_images:
        xref = img[0]
        if xref not in xref_to_name:
            continue
        name = xref_to_name[xref]

        # 获取该图在页面上的所有显示位置
        rects = page.get_image_rects(xref)
        for rect in rects:
            x0, y0, x1, y1 = rect
            labeled.append((name, x0*scale, y0*scale, x1*scale, y1*scale))

    # 在图上画框和标签
    for name, x0, y0, x1, y1 in labeled:
        # 画红色边框
        shape_rect = fitz.Rect(x0, y0, x1, y1)
        pix.draw_rect(shape_rect, color=(1, 0, 0), width=2)

        # 写标签（居中）
        cx = int((x0 + x1) / 2)
        cy = int((y0 + y1) / 2)
        # fitz.Pixmap 不直接支持文字，改为在矩形左上角写
        # 用简单方式：在边框左上角留标签区域
        label_x = max(0, int(x0) + 2)
        label_y = max(0, int(y0) + 2)
        pix.draw_rect(fitz.Rect(label_x, label_y, label_x+40, label_y+14),
                      color=(1,0,0), fill=(1,0,0))

    out_path = os.path.join(OUT_DIR, f"page_{page_num+1:02d}.png")
    pix.save(out_path)
    print(f"第 {page_num+1} 页 → {out_path}  (槽位: {[l[0] for l in labeled]})")

print(f"\n预览图已保存到 {OUT_DIR}/")
