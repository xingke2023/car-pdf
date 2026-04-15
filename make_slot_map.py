#!/usr/bin/env python3
"""
生成带编号标注的槽位地图图片
输出: slot_map/page_04.png ~ page_07.png
方便用户知道"第几张照片放哪个位置"
"""
import fitz
import os

PDF = "authfile1852026011497984810(1).pdf"
OUT_DIR = "slot_map"
os.makedirs(OUT_DIR, exist_ok=True)

# 车辆照片槽位：xref → 顺序编号（1-25）
PHOTO_XREFS_ORDER = [
    78, 80, 82, 84, 86, 88,    # 第4页 I16-I21 (01-06)
    90, 92, 94, 96, 98, 100, 102, 104,  # 第5页 I22-I29 (07-14)
    106, 108, 110, 112, 114, 116, 118, 120,  # 第6页 I30-I37 (15-22)
    122, 124, 126,              # 第7页 I38-I40 (23-25)
]
xref_to_num = {xref: i+1 for i, xref in enumerate(PHOTO_XREFS_ORDER)}

doc = fitz.open(PDF)
SCALE = 0.6

# 只处理有车辆照片的页
target_pages = [3, 4, 5, 6]  # 0-indexed: 第4-7页

for page_num in target_pages:
    page = doc[page_num]
    mat = fitz.Matrix(SCALE, SCALE)
    pix = page.get_pixmap(matrix=mat)
    if pix.alpha:
        pix = fitz.Pixmap(fitz.csRGB, pix)

    # 获取该页所有大图位置
    infos = page.get_image_info(xrefs=True)
    photo_infos = [(info['xref'], info['bbox']) for info in infos
                   if info['xref'] in xref_to_num]

    # 在图上绘制标注（用 fitz.open 叠加绘图）
    # 转成临时PDF再绘图
    tmp_doc = fitz.open()
    tmp_page = tmp_doc.new_page(width=pix.width, height=pix.height)
    tmp_page.insert_image(fitz.Rect(0, 0, pix.width, pix.height), pixmap=pix)

    for xref, bbox in photo_infos:
        num = xref_to_num[xref]
        x0, y0, x1, y1 = [v * SCALE for v in bbox]

        # 红色边框
        rect = fitz.Rect(x0, y0, x1, y1)
        tmp_page.draw_rect(rect, color=(0.9, 0.1, 0.1), width=3)

        # 红色半透明背景标签
        label = f"#{num:02d}"
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        fs = min(28, (x1-x0)*0.25)  # 字体大小自适应
        tw = fs * len(label) * 0.55
        th = fs * 1.3
        lx0, ly0 = cx - tw/2 - 4, cy - th/2 - 2
        lx1, ly1 = cx + tw/2 + 4, cy + th/2 + 2

        tmp_page.draw_rect(fitz.Rect(lx0, ly0, lx1, ly1),
                           color=(0.9, 0.1, 0.1), fill=(0.9, 0.1, 0.1),
                           fill_opacity=0.85)
        tmp_page.insert_text(
            fitz.Point(lx0 + 4, ly1 - 4),
            label,
            fontsize=fs,
            color=(1, 1, 1),
            fontname="helv"
        )

    out_path = os.path.join(OUT_DIR, f"page_{page_num+1:02d}.png")
    final_pix = tmp_page.get_pixmap(matrix=fitz.Matrix(1, 1))
    final_pix.save(out_path)
    print(f"第{page_num+1}页 → {out_path}  (编号: {[xref_to_num[x] for x,_ in photo_infos]})")

print(f"\n地图已保存到 {OUT_DIR}/，用 'open {OUT_DIR}' 查看")
