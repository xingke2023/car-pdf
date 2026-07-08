#!/usr/bin/env python3
"""
车辆PDF模板工具 - Web界面
运行: python3 app.py
浏览器打开: http://localhost:5000
"""
import os, io, json, tempfile, shutil, zipfile, base64, copy
from datetime import timedelta
from flask import Flask, request, jsonify, send_file, render_template_string, render_template, session, redirect, url_for

WORK_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(WORK_DIR, 'templates'))
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=2)
app.secret_key = os.environ.get('CAR_PDF_SECRET') or 'gjj-car-pdf-secret-2026-please-change-in-prod'
LOGIN_PASSWORD = 'gjj2026'
DEFAULT_TEMPLATE = os.path.join(WORK_DIR, 'template_decrypted.pdf')
MIN_IMG_SIZE = 400  # 大图阈值（px）

# 运行时状态（本地单用户工具）
STATE = {
    'pdf_path': DEFAULT_TEMPLATE,
    'pdf_bytes': None,
    'slots': [],          # [{xref, page, w, h, name, bbox, orient}]
    'photo_map': {},      # int(photo_num) -> int(xref)
}


# ─── CORS ──────────────────────────────────────────────────────

@app.after_request
def add_cors(r):
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    r.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return r


# ─── 报告常量 ───────────────────────────────────────────────────

COMPANY       = "广州国际检机动车鉴定评估有限公司"
COMPANY_SHORT = "国际检"

PHOTO_PAGES = [
    {'page': 4, 'title': '车辆图片',
     'subtitle': '【外观件检测标准】：是否存在钣金、喷漆、更换、改装、损伤、钣件缝隙是否均匀等，非法改装外观车辆不做承保。',
     'rows': [
         {'slots': [1, 2], 'labels': ['左前', '右后']},
         {'slots': [3, 4], 'labels': ['仪表盘', '铭牌']},
         {'slots': [5, 6], 'labels': ['车架号', '行驶证']},
     ]},
    {'page': 5, 'title': '车辆图片（续）', 'subtitle': '',
     'rows': [
         {'slots': [7,  8],  'labels': ['前防撞梁', '左前纵梁']},
         {'slots': [9,  10], 'labels': ['右前纵梁', '防火墙(前围板)']},
         {'slots': [11, 12], 'labels': ['发动机舱盖', '发动机舱盖']},
         {'slots': [13, 14], 'labels': ['副驾座椅轨道及骨架', '右前安全带及插座']},
     ]},
    {'page': 6, 'title': '车辆图片（续）', 'subtitle': '',
     'rows': [
         {'slots': [15, 16], 'labels': ['备胎槽(行李箱底板)', '后围板']},
         {'slots': [17, 18], 'labels': ['右后纵梁', '左后纵梁']},
         {'slots': [19, 20], 'labels': ['后防撞梁', '后保险杠']},
         {'slots': [21, 22], 'labels': ['仪表台骨架', '左前地毯(含周边饰条/饰板)']},
     ]},
    {'page': 7, 'title': '车辆图片（续）', 'subtitle': '',
     'rows': [
         {'slots': [23, 24], 'labels': ['OBD插接件', '车身底板']},
         {'slots': [25],     'labels': ['车身底板']},
     ]},
]

CHECK_SECTIONS_DATA = [
  {'id':'ac','name':'事故检测','count':63,'desc':'【判断标准】事故车指车辆结构经过撞击等外力作用，即使修复但仍存在安全隐患的车辆总称','items':[
    {'name':'左前大灯框架','pageIdx':7},{'name':'前防撞梁','pageIdx':7},
    {'name':'左前吸能盒','pageIdx':7},{'name':'右前吸能盒','pageIdx':7},
    {'name':'水箱框架可拆卸','pageIdx':7},{'name':'水箱框架不可拆卸','pageIdx':7},
    {'name':'防火墙(前围板)','pageIdx':7},{'name':'左前纵梁','pageIdx':7},
    {'name':'右前纵梁','pageIdx':7},{'name':'右前减震器座','pageIdx':7},
    {'name':'右前翼子板骨架','pageIdx':7},{'name':'右A柱外侧','pageIdx':7},
    {'name':'右A柱内侧','pageIdx':7},{'name':'右侧上边梁','pageIdx':7},
    {'name':'右前安全带','pageIdx':7},{'name':'右B柱外侧','pageIdx':7},
    {'name':'右B柱内侧','pageIdx':7},{'name':'右C柱外侧','pageIdx':7},
    {'name':'右C柱内侧','pageIdx':7},{'name':'右侧下边梁','pageIdx':7},
    {'name':'右后安全带','pageIdx':7},{'name':'右D柱外侧','pageIdx':7},
    {'name':'右D柱内侧','pageIdx':7},{'name':'右后翼子板','pageIdx':7},
    {'name':'右后翼子板导水槽','pageIdx':7},{'name':'右后翼子板内侧(骨架)','pageIdx':7},
    {'name':'右后尾灯框架','pageIdx':7},{'name':'右后减震器座','pageIdx':7},
    {'name':'右后轮旋','pageIdx':7},{'name':'行李箱后遮物板(铁质)','pageIdx':7},
    {'name':'备胎槽(行李箱底板)','pageIdx':7},{'name':'后围板','pageIdx':7},
    {'name':'右后纵梁','pageIdx':8},{'name':'左后纵梁','pageIdx':8},
    {'name':'底板纵梁','pageIdx':8},{'name':'底板横梁','pageIdx':8},
    {'name':'后防撞梁','pageIdx':8},{'name':'车身底板','pageIdx':8},
    {'name':'左后轮旋','pageIdx':8},{'name':'左后尾灯框架','pageIdx':8},
    {'name':'左后翼子板导水槽','pageIdx':8},{'name':'左后减震器座','pageIdx':8},
    {'name':'左后翼子板内侧(骨架)','pageIdx':8},{'name':'左后翼子板','pageIdx':8},
    {'name':'左D柱外侧','pageIdx':8},{'name':'左D柱内侧','pageIdx':8},
    {'name':'左后安全带','pageIdx':8},{'name':'左C柱外侧','pageIdx':8},
    {'name':'左C柱内侧','pageIdx':8},{'name':'左B柱外侧','pageIdx':8},
    {'name':'左B柱内侧','pageIdx':8},{'name':'左侧上边梁','pageIdx':8},
    {'name':'左侧下边梁','pageIdx':8},{'name':'仪表台骨架','pageIdx':8},
    {'name':'仪表台','pageIdx':8},{'name':'安全气囊','pageIdx':8},
    {'name':'左前安全带','pageIdx':8},{'name':'左A柱外侧','pageIdx':8},
    {'name':'左A柱内侧','pageIdx':8},{'name':'左前翼子板骨架','pageIdx':8},
    {'name':'左前减震器座','pageIdx':8},{'name':'右前大灯框架','pageIdx':8},
    {'name':'车身大顶','pageIdx':8},
  ]},
  {'id':'wt','name':'泡水检测','count':29,'desc':'【判断标准】泡水车指车辆被水浸泡过，导致车辆电气系统、机械系统等受损的车辆','items':[
    {'name':'机舱保险盒','pageIdx':9},{'name':'左前地毯(含周边饰条/饰板)','pageIdx':9},
    {'name':'仪表台空调出风口','pageIdx':9},{'name':'仪表台骨架','pageIdx':9},
    {'name':'转向管柱','pageIdx':9},{'name':'机舱电器插接件','pageIdx':9},
    {'name':'OBD插接件','pageIdx':9},{'name':'点烟器座','pageIdx':9},
    {'name':'左侧门槛内部空腔','pageIdx':9},{'name':'主驾座椅轨道及骨架','pageIdx':9},
    {'name':'左侧门槛线束','pageIdx':9},{'name':'左前底板隔音胶及封边胶','pageIdx':9},
    {'name':'左后地毯(含周边饰条/饰板)','pageIdx':9},{'name':'左后安全带及插座','pageIdx':9},
    {'name':'左侧脚部出风口','pageIdx':9},{'name':'后排座椅骨架及海绵','pageIdx':9},
    {'name':'车内顶棚','pageIdx':9},{'name':'备胎槽(行李箱底板)','pageIdx':9},
    {'name':'行李箱底板线束及保险盒','pageIdx':9},{'name':'右后地毯(含周边饰条/饰板)','pageIdx':9},
    {'name':'右侧门槛线束','pageIdx':9},{'name':'右侧脚部出风口','pageIdx':9},
    {'name':'右后安全带及插座','pageIdx':9},{'name':'右侧门槛内部空腔','pageIdx':9},
    {'name':'右前底板隔音胶及封边胶','pageIdx':9},{'name':'右前地毯(含周边饰条/饰板)','pageIdx':9},
    {'name':'副驾座椅轨道及骨架','pageIdx':9},{'name':'右前安全带及插座','pageIdx':9},
    {'name':'左前安全带及插座','pageIdx':9},
  ]},
  {'id':'fr','name':'火烧检测','count':23,'desc':'【判断标准】火烧车指车辆曾经发生过火灾，导致车辆部件受损的车辆','items':[
    {'name':'燃油箱及管路','pageIdx':9},{'name':'发动机舱内管路','pageIdx':9},
    {'name':'蓄电池及附件','pageIdx':10},{'name':'发动机舱隔音棉','pageIdx':10},
    {'name':'机舱线束及标签','pageIdx':10},{'name':'发动机舱塑料件','pageIdx':10},
    {'name':'机舱保险盒','pageIdx':10},{'name':'防火墙隔热棉','pageIdx':10},
    {'name':'左前减震器座周边胶体','pageIdx':10},{'name':'右前减震器座周边胶体','pageIdx':10},
    {'name':'主驾驶座椅无火烧痕迹','pageIdx':10},{'name':'仪表台及附件','pageIdx':10},
    {'name':'驾驶舱内饰板','pageIdx':10},{'name':'驾驶舱内线束及插接件','pageIdx':10},
    {'name':'后排座椅','pageIdx':10},{'name':'左后轮旋','pageIdx':10},
    {'name':'行李箱','pageIdx':10},{'name':'行李箱内饰板','pageIdx':10},
    {'name':'行李箱底板线束及保险盒','pageIdx':10},{'name':'右后轮旋','pageIdx':10},
    {'name':'车身底板','pageIdx':10},{'name':'车身覆盖件','pageIdx':10},
    {'name':'副驾驶座椅','pageIdx':10},
  ]},
  {'id':'ex','name':'车身外观检测','count':52,'desc':'【判断标准】检测车辆外观覆盖件是否存在钣金、喷漆、更换等痕迹','items':[
    {'name':'前中网','pageIdx':10},{'name':'前保险杠','pageIdx':10},
    {'name':'发动机舱盖','pageIdx':10},{'name':'前风挡玻璃','pageIdx':10},
    {'name':'天窗玻璃','pageIdx':10},{'name':'车身大顶','pageIdx':10},
    {'name':'左前大灯','pageIdx':10},{'name':'左前雾灯','pageIdx':10},
    {'name':'右前雾灯','pageIdx':10},{'name':'右前大灯','pageIdx':10},
    {'name':'右前翼子板','pageIdx':10},{'name':'右A柱外侧','pageIdx':10},
    {'name':'右A柱三角玻璃','pageIdx':10},{'name':'右侧外后视镜','pageIdx':10},
    {'name':'右前门','pageIdx':10},{'name':'右前门玻璃','pageIdx':10},
    {'name':'右侧下边梁','pageIdx':11},{'name':'右下边梁外饰板','pageIdx':11},
    {'name':'右B柱外侧','pageIdx':11},{'name':'右侧上边梁','pageIdx':11},
    {'name':'右后门','pageIdx':11},{'name':'右后门玻璃','pageIdx':11},
    {'name':'右C柱外侧','pageIdx':11},{'name':'右侧C柱三角玻璃','pageIdx':11},
    {'name':'右D柱外侧','pageIdx':11},{'name':'右侧D柱三角玻璃','pageIdx':11},
    {'name':'右后翼子板','pageIdx':11},{'name':'后风挡玻璃','pageIdx':11},
    {'name':'行李箱盖','pageIdx':11},{'name':'右后尾灯','pageIdx':11},
    {'name':'右后行李箱盖尾灯','pageIdx':11},{'name':'后保险杠','pageIdx':11},
    {'name':'后雾灯','pageIdx':11},{'name':'左后行李箱盖尾灯','pageIdx':11},
    {'name':'左后尾灯','pageIdx':11},{'name':'左后翼子板','pageIdx':11},
    {'name':'左D柱外侧','pageIdx':11},{'name':'左侧D柱三角玻璃','pageIdx':11},
    {'name':'左侧C柱三角玻璃','pageIdx':11},{'name':'左C柱外侧','pageIdx':11},
    {'name':'左后门','pageIdx':11},{'name':'左后门玻璃','pageIdx':11},
    {'name':'左B柱外侧','pageIdx':11},{'name':'左侧上边梁','pageIdx':11},
    {'name':'左侧下边梁','pageIdx':11},{'name':'左下边梁外饰板','pageIdx':11},
    {'name':'左前门','pageIdx':11},{'name':'左前门玻璃','pageIdx':11},
    {'name':'左A柱三角玻璃','pageIdx':11},{'name':'左A柱外侧','pageIdx':11},
    {'name':'左侧外后视镜','pageIdx':11},{'name':'左前翼子板','pageIdx':11},
  ]},
  {'id':'rc','name':'记录模块','count':7,'desc':'【记录模块】车辆各类电子记录检测结果','items':[
    {'name':'出险记录','pageIdx':11},{'name':'维保记录','pageIdx':11},
    {'name':'云端记录','pageIdx':11},{'name':'故障码记录','pageIdx':11},
    {'name':'obd读取记录','pageIdx':12},{'name':'电池包检测记录','pageIdx':12},
    {'name':'电车电池记录','pageIdx':12},
  ]},
]


def build_check_sections(status_overrides):
    secs = copy.deepcopy(CHECK_SECTIONS_DATA)
    for key, val in status_overrides.items():
        parts = key.split(':')
        if len(parts) != 2:
            continue
        sec_id, idx_str = parts
        for sec in secs:
            if sec['id'] == sec_id:
                idx = int(idx_str)
                if 0 <= idx < len(sec['items']):
                    sec['items'][idx]['status'] = val
    return secs


def group_items_by_page(sections):
    """Returns dict: pageIdx -> list of {item, section_id, section_name, is_first}"""
    from collections import defaultdict, OrderedDict
    pages = defaultdict(list)
    for sec in sections:
        first_page = None
        for item in sec['items']:
            item.setdefault('status', '正常')
            pg = item['pageIdx']
            is_first = (pg != first_page) and (first_page is None or pg != first_page)
            if first_page is None:
                first_page = pg
            pages[pg].append({
                'name': item['name'],
                'status': item.get('status', '正常'),
                'section_id': sec['id'],
                'section_name': sec['name'],
                'section_desc': sec['desc'],
                'section_count': sec['count'],
            })
    return dict(pages)


@app.template_filter('status_class')
def status_class_filter(s):
    return {'正常': 'ok', '受限': 'limited', '异常': 'abnormal'}.get(s or '正常', 'ok')


# ─── PDF 工具函数 ──────────────────────────────────────────────

def open_doc():
    import fitz
    if STATE['pdf_bytes']:
        return fitz.open(stream=STATE['pdf_bytes'], filetype='pdf')
    return fitz.open(STATE['pdf_path'])


def do_scan():
    import fitz
    doc = open_doc()

    # 用 get_image_info(xrefs=True) 扫描每页，获取实际渲染位置
    slots = []
    seen = set()
    for page_num, page in enumerate(doc):
        for info in page.get_image_info(xrefs=True):
            xref = info.get('xref', 0)
            w, h = info.get('width', 0), info.get('height', 0)
            if xref <= 0 or xref in seen:
                continue
            if w <= MIN_IMG_SIZE and h <= MIN_IMG_SIZE:
                continue
            # 过滤极端宽高比（细线/文字框，不是照片槽位）
            if min(w, h) < 80:
                continue
            seen.add(xref)
            bbox = list(info.get('bbox', [0, 0, 200, 150]))
            # name 从 xref 对应的图像对象获取
            try:
                name = doc.xref_get_key(xref, 'Name')[1] or f'I{xref}'
            except Exception:
                name = f'I{xref}'
            slots.append({
                'xref': xref,
                'page': page_num + 1,
                'w': w,
                'h': h,
                'name': name,
                'bbox': bbox,
                'orient': '横拍' if w >= h else '竖拍',
            })

    doc.close()
    slots.sort(key=lambda s: (s['page'], s['bbox'][1], s['bbox'][0]))
    STATE['slots'] = slots
    return slots


def render_preview(page_num_0idx, scale=0.45):
    """渲染带标注的页面预览，返回 PNG bytes"""
    import fitz
    doc = open_doc()
    page = doc[page_num_0idx]
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    if pix.alpha:
        pix = fitz.Pixmap(fitz.csRGB, pix)

    tmp = fitz.open()
    tp = tmp.new_page(width=pix.width, height=pix.height)
    tp.insert_image(fitz.Rect(0, 0, pix.width, pix.height), pixmap=pix)

    # 反转 photo_map: xref -> photo_num
    xref_to_photo = {v: k for k, v in STATE['photo_map'].items()}

    page_slots = [s for s in STATE['slots'] if s['page'] == page_num_0idx + 1]
    for s in page_slots:
        x0, y0, x1, y1 = [v * scale for v in s['bbox']]
        tp.draw_rect(fitz.Rect(x0, y0, x1, y1), color=(0.9, 0.1, 0.1), width=2)

        pn = xref_to_photo.get(s['xref'])
        label = f"#{pn:02d}" if pn is not None else f"xref{s['xref']}"
        fs = max(8, min(22, (x1 - x0) * 0.18))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        tw = fs * len(label) * 0.6
        th = fs * 1.4
        lx0, ly0 = cx - tw / 2 - 3, cy - th / 2 - 2
        lx1, ly1 = cx + tw / 2 + 3, cy + th / 2 + 2
        tp.draw_rect(fitz.Rect(lx0, ly0, lx1, ly1),
                     color=(0.9, 0.1, 0.1), fill=(0.9, 0.1, 0.1), fill_opacity=0.85)
        tp.insert_text(fitz.Point(lx0 + 3, ly1 - 4), label,
                       fontsize=fs, color=(1, 1, 1), fontname='helv')

    out_pix = tp.get_pixmap()
    png = out_pix.tobytes('png')
    doc.close()
    tmp.close()
    return png


# ─── API 路由 ──────────────────────────────────────────────────

def _render_login_page(err_msg='', next_url='/'):
    from markupsafe import escape
    err_cls = 'class="err"' if err_msg else ''
    nxt = escape(next_url)
    msg = escape(err_msg)
    return ('<!doctype html><html lang="zh"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">'
        '<title>检测认证评估报告 · 登录</title>'
        '<style>'
        '*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}'
        'body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;'
        'background:#000;color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}'
        '.box{width:100%;max-width:360px;text-align:center}'
        'h1{font-size:24px;font-weight:600;margin:0 0 8px;letter-spacing:2px}'
        '.sub{color:#888;font-size:13px;margin-bottom:48px;letter-spacing:1px}'
        'input[type=password]{width:100%;background:#1a1a1a;border:1px solid #333;color:#fff;'
        'border-radius:12px;padding:14px 16px;font-size:16px;outline:none;margin-bottom:14px}'
        'input[type=password]:focus{border-color:#ff3b30}'
        'input[type=password].err{border-color:#ff3b30;background:#2a1010}'
        'button{width:100%;background:#ff3b30;color:#fff;border:none;border-radius:12px;'
        'padding:14px;font-size:16px;font-weight:700;letter-spacing:2px}'
        'button:active{opacity:.8}'
        '.err-msg{color:#ff3b30;font-size:13px;height:18px;margin-top:8px}'
        '</style></head><body>'
        '<form class="box" method="post" action="/login" autocomplete="off">'
        '<h1>检测认证评估报告</h1>'
        '<div class="sub">请输入访问密码</div>'
        f'<input type="password" name="password" placeholder="密码" autofocus {err_cls}>'
        '<button type="submit">登录</button>'
        f'<div class="err-msg">{msg}</div>'
        f'<input type="hidden" name="next" value="{nxt}">'
        '</form></body></html>')


def _is_logged_in():
    return session.get('auth') is True


def _safe_next(url):
    if not url or not url.startswith('/') or url.startswith('//'):
        return '/'
    return url


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pw = (request.form.get('password') or '').strip()
        nxt = _safe_next(request.form.get('next') or '/')
        if pw == LOGIN_PASSWORD:
            session.permanent = True
            session['auth'] = True
            return redirect(nxt)
        return _render_login_page('密码错误，请重试', nxt), 401, {'Content-Type': 'text/html; charset=utf-8'}

    nxt = _safe_next(request.args.get('next') or '/')
    return _render_login_page('', nxt), 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/logout')
def logout():
    session.pop('auth', None)
    return redirect(url_for('login'))


@app.route('/')
def index():
    if not _is_logged_in():
        return redirect(url_for('login', next=request.path))
    guide_path = os.path.join(WORK_DIR, 'photo_guide_v2.html')
    with open(guide_path, 'rb') as f:
        content = f.read()
    return content, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/guide')
def guide():
    return index()


@app.route('/tool')
def tool():
    return render_template_string(HTML)


@app.route('/slot-preview/<path:filename>')
def slot_preview(filename):
    """服務槽位預覽圖（從 slot_previews/ 目錄）"""
    previews_dir = os.path.join(WORK_DIR, 'slot_previews')
    return send_file(os.path.join(previews_dir, filename), mimetype='image/jpeg')


@app.route('/api/scan', methods=['POST'])
def api_scan():
    f = request.files.get('pdf')
    path = request.form.get('path', '').strip()

    if f and f.filename:
        STATE['pdf_bytes'] = f.read()
        STATE['pdf_path'] = None
    elif path:
        if not os.path.isfile(path):
            return jsonify({'error': f'文件不存在: {path}'}), 400
        STATE['pdf_path'] = path
        STATE['pdf_bytes'] = None
    else:
        # 使用默认模板
        STATE['pdf_path'] = DEFAULT_TEMPLATE
        STATE['pdf_bytes'] = None
        if not os.path.isfile(DEFAULT_TEMPLATE):
            return jsonify({'error': f'默认模板不存在: {DEFAULT_TEMPLATE}'}), 400

    try:
        slots = do_scan()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # 默认按页面顺序自动编号
    STATE['photo_map'] = {i + 1: s['xref'] for i, s in enumerate(slots)}

    pages = sorted(set(s['page'] for s in slots))
    return jsonify({
        'slots': slots,
        'photo_map': STATE['photo_map'],
        'pages': pages,
        'total': len(slots),
    })


@app.route('/api/preview/<int:page_num>')
def api_preview(page_num):
    """返回第 page_num 页（1-indexed）的带标注预览图"""
    if not STATE['slots']:
        return 'No template loaded', 400
    try:
        png = render_preview(page_num - 1)
        return send_file(io.BytesIO(png), mimetype='image/png')
    except Exception as e:
        return str(e), 500


@app.route('/api/update-map', methods=['POST'])
def api_update_map():
    data = request.json or {}
    pm = data.get('photo_map', {})
    STATE['photo_map'] = {int(k): int(v) for k, v in pm.items()}
    return jsonify({'ok': True})


@app.route('/api/apply', methods=['POST'])
def api_apply():
    tmp_dir = None
    try:
        # 解析参数
        if request.content_type and 'application/json' in request.content_type:
            data = request.json or {}
            pm = data.get('photo_map', STATE['photo_map'])
            photos_dir = data.get('photos_dir', '').strip()
            zip_bytes = None
        else:
            pm_str = request.form.get('photo_map')
            pm = json.loads(pm_str) if pm_str else STATE['photo_map']
            photos_dir = request.form.get('photos_dir', '').strip()
            zf = request.files.get('photos_zip')
            zip_bytes = zf.read() if zf else None

        photo_map = {int(k): int(v) for k, v in pm.items()}
        if not photo_map:
            return jsonify({'error': '没有槽位映射，请先扫描模板'}), 400

        # 准备照片目录
        if zip_bytes:
            tmp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                z.extractall(tmp_dir)
            photos_dir = tmp_dir
        elif not photos_dir:
            photos_dir = os.path.join(WORK_DIR, 'photos')

        if not os.path.isdir(photos_dir):
            return jsonify({'error': f'照片文件夹不存在: {photos_dir}'}), 400

        import fitz
        doc = open_doc()
        replaced, missing = 0, []

        for photo_num, xref in sorted(photo_map.items()):
            photo_path = None
            for ext in ['jpg', 'jpeg', 'png', 'webp', 'heic',
                        'JPG', 'JPEG', 'PNG', 'WEBP', 'HEIC']:
                p = os.path.join(photos_dir, f'{photo_num:02d}.{ext}')
                if os.path.exists(p):
                    photo_path = p
                    break

            if photo_path is None:
                missing.append(photo_num)
                continue

            try:
                doc.replace_image(xref, filename=photo_path)
                replaced += 1
            except Exception:
                missing.append(photo_num)

        out_buf = io.BytesIO()
        doc.save(out_buf, deflate=True)
        doc.close()
        out_buf.seek(0)

        resp = send_file(out_buf, mimetype='application/pdf',
                         as_attachment=True, download_name='output.pdf')
        resp.headers['X-Replaced'] = str(replaced)
        resp.headers['X-Missing'] = ','.join(map(str, missing))
        resp.headers['Access-Control-Expose-Headers'] = 'X-Replaced, X-Missing'
        return resp

    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


@app.route('/api/export-config')
def api_export_config():
    config = {'photo_map': STATE['photo_map'], 'slots': STATE['slots']}
    buf = io.BytesIO(json.dumps(config, ensure_ascii=False, indent=2).encode('utf-8'))
    return send_file(buf, mimetype='application/json',
                     as_attachment=True, download_name='slot_config.json')


@app.route('/api/import-config', methods=['POST'])
def api_import_config():
    data = request.json or {}
    if 'photo_map' in data:
        STATE['photo_map'] = {int(k): int(v) for k, v in data['photo_map'].items()}
    if 'slots' in data:
        STATE['slots'] = data['slots']
    return jsonify({'ok': True, 'total': len(STATE['photo_map'])})


import uuid, threading, time, re

# 临时 PDF 缓存：token -> bytes，60 秒后自动清除
_PDF_CACHE = {}
_PDF_CACHE_LOCK = threading.Lock()

# 已分享报告：磁盘持久化 6 个月
SHARED_REPORTS_DIR = os.path.join(WORK_DIR, 'shared_reports')
os.makedirs(SHARED_REPORTS_DIR, exist_ok=True)
HTML_SHARE_TTL = 180 * 24 * 3600  # 6 个月

_HEX32_RE = re.compile(r'^[0-9a-f]{32}$')
# 新格式 token：YYYYMMDD-VIN（17位字母数字）或 YYYYMMDD-NNN（3+位数字流水）
_TOKEN_RE = re.compile(r'^\d{8}-[A-Za-z0-9]{1,32}$')
_VIN_RE = re.compile(r'^[A-Za-z0-9]{1,32}$')

def _expire_pdf(token):
    time.sleep(300)
    with _PDF_CACHE_LOCK:
        _PDF_CACHE.pop(token, None)

def _shared_html_path(token):
    t = token or ''
    if not (_HEX32_RE.match(t) or _TOKEN_RE.match(t)):
        return None
    return os.path.join(SHARED_REPORTS_DIR, f'{t}.html')

def _shared_pdf_path(token):
    t = token or ''
    if not (_HEX32_RE.match(t) or _TOKEN_RE.match(t)):
        return None
    return os.path.join(SHARED_REPORTS_DIR, f'{t}.pdf')

def _normalize_date(s):
    """从 'YYYY-MM-DD' / 'YYYY/MM/DD' / 'YYYY-MM-DD HH:MM:SS' 抽出 YYYYMMDD；失败返回今天。"""
    from datetime import date
    if s:
        digits = ''.join(ch for ch in str(s) if ch.isdigit())
        if len(digits) >= 8:
            return digits[:8]
    return date.today().strftime('%Y%m%d')

def _next_seq_token(date_str):
    """扫描 shared_reports/ 找当天最大流水号 +1，返回 'YYYYMMDD-NNN'。"""
    max_n = 0
    prefix = date_str + '-'
    try:
        for name in os.listdir(SHARED_REPORTS_DIR):
            if not (name.startswith(prefix) and name.endswith('.html')):
                continue
            suffix = name[len(prefix):-5]
            if suffix.isdigit():
                max_n = max(max_n, int(suffix))
    except OSError:
        pass
    return f'{date_str}-{max_n + 1:03d}'

def _build_report_token(info):
    """根据报告信息生成 token：有 VIN 用 日期-VIN，否则当天流水。"""
    date_str = _normalize_date(info.get('checkDate') if isinstance(info, dict) else None)
    vin = ''
    if isinstance(info, dict):
        vin = (info.get('vin') or '').strip()
    if vin and _VIN_RE.match(vin):
        return f'{date_str}-{vin.upper()}'
    return _next_seq_token(date_str)

def _cleanup_shared_html():
    """删除超过 6 个月的已分享报告（HTML 与 PDF）。"""
    try:
        now = time.time()
        for name in os.listdir(SHARED_REPORTS_DIR):
            if not (name.endswith('.html') or name.endswith('.pdf')):
                continue
            path = os.path.join(SHARED_REPORTS_DIR, name)
            try:
                if now - os.path.getmtime(path) > HTML_SHARE_TTL:
                    os.remove(path)
            except OSError:
                pass
    except OSError:
        pass

# 启动时清理一次，后台每天清理一次
_cleanup_shared_html()
def _shared_html_janitor():
    while True:
        time.sleep(24 * 3600)
        _cleanup_shared_html()
threading.Thread(target=_shared_html_janitor, daemon=True).start()


@app.route('/report/pdf', methods=['POST', 'OPTIONS'])
def generate_report_pdf():
    """生成 PDF，持久化到磁盘 6 个月，返回下载 token"""
    if request.method == 'OPTIONS':
        return '', 204
    from playwright.sync_api import sync_playwright

    payload = request.json or {}
    html = generate_report_html(payload)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until='networkidle')
        pdf_bytes = page.pdf(
            format='A4',
            print_background=True,
            margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'},
        )
        browser.close()

    token = _build_report_token(payload.get('info', {}))
    with _PDF_CACHE_LOCK:
        _PDF_CACHE[token] = pdf_bytes
    threading.Thread(target=_expire_pdf, args=(token,), daemon=True).start()

    path = _shared_pdf_path(token)
    if path:
        try:
            with open(path, 'wb') as f:
                f.write(pdf_bytes)
        except OSError:
            pass

    return jsonify({'token': token})


@app.route('/report/pdf/<token>')
def download_report_pdf(token):
    """通过 token 下载已分享的 PDF（6 个月有效，兼容 iOS Safari）"""
    with _PDF_CACHE_LOCK:
        pdf_bytes = _PDF_CACHE.get(token)

    if not pdf_bytes:
        path = _shared_pdf_path(token)
        if not path or not os.path.exists(path):
            return '链接已过期，请重新生成', 404
        if time.time() - os.path.getmtime(path) > HTML_SHARE_TTL:
            try: os.remove(path)
            except OSError: pass
            return '链接已过期，请重新生成', 404
        with open(path, 'rb') as f:
            pdf_bytes = f.read()

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=False,
        download_name='车辆检测报告.pdf',
    )


@app.route('/report/html', methods=['POST', 'OPTIONS'])
def generate_report_html_token():
    """生成 HTML 报告，持久化到磁盘 6 个月，返回 token（兼容 iOS Safari）"""
    if request.method == 'OPTIONS':
        return '', 204
    payload = request.json or {}
    html = generate_report_html(payload)
    token = _build_report_token(payload.get('info', {}))
    data = html.encode('utf-8') if isinstance(html, str) else html
    path = _shared_html_path(token)
    if path:
        with open(path, 'wb') as f:
            f.write(data)
    return jsonify({'token': token})


@app.route('/report/html/<token>')
def download_report_html(token):
    """通过 token 查看已分享的 HTML 报告（6 个月有效）"""
    path = _shared_html_path(token)
    if not path or not os.path.exists(path):
        return '链接已过期，请重新生成', 404
    if time.time() - os.path.getmtime(path) > HTML_SHARE_TTL:
        try: os.remove(path)
        except OSError: pass
        return '链接已过期，请重新生成', 404
    with open(path, 'rb') as f:
        html_bytes = f.read()
    return html_bytes, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/report', methods=['POST', 'OPTIONS'])
def generate_report():
    if request.method == 'OPTIONS':
        return '', 204
    html = generate_report_html(request.json or {})
    return html


def generate_report_html(data):
    from datetime import date
    info    = data.get('info', {})
    photos  = data.get('photos', {})   # {"1": "data:image/jpeg;base64,..."}
    status  = data.get('status', {})   # {"ac:0": "受限"}
    today_str = date.today().strftime('%Y-%m-%d')
    for k in ('checkDate', 'reportTime', 'orderTime', 'completeTime'):
        if not info.get(k):
            info[k] = today_str

    sections = build_check_sections(status)
    by_page  = group_items_by_page(sections)

    # 各检测类别异常数
    def count_abnormal(sec_id):
        for s in sections:
            if s['id'] == sec_id:
                return sum(1 for it in s['items'] if it.get('status', '正常') != '正常')
        return 0

    # 公章图片 base64
    seal_b64 = ''
    seal_path = os.path.join(WORK_DIR, '微信图片_20260520162843_62_356.jpg')
    if os.path.exists(seal_path):
        with open(seal_path, 'rb') as f:
            seal_b64 = 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode()

    # 评估师签名图 base64
    sign_b64 = ''
    sign_path = os.path.join(WORK_DIR, 'signature_wxf.png')
    if os.path.exists(sign_path):
        with open(sign_path, 'rb') as f:
            sign_b64 = 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

    return render_template(
        'report_template.html',
        info=info,
        photos=photos,
        by_page=by_page,
        sections=sections,
        photo_pages=PHOTO_PAGES,
        seal_image=seal_b64,
        signature_image=sign_b64,
        company=COMPANY,
        company_short=COMPANY_SHORT,
        ac_pass=(count_abnormal('ac') == 0),
        wt_pass=(count_abnormal('wt') == 0),
        fr_pass=(count_abnormal('fr') == 0),
    )


# ─── HTML ──────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>车辆PDF模板工具</title>
<style>
:root{--bg:#1a1a1a;--card:#222;--border:#303030;--accent:#e07840;--text:#ddd;--muted:#777}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font:14px/1.6 system-ui,sans-serif;padding-bottom:60px}
.wrap{max-width:1100px;margin:0 auto;padding:24px 16px}
h1{font-size:19px;font-weight:700;margin-bottom:22px;color:#fff}
h1 em{color:var(--accent);font-style:normal}

/* Card */
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:18px}
.card-head{padding:13px 18px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px}
.num{background:var(--accent);color:#fff;width:22px;height:22px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;flex-shrink:0}
.card-head h2{font-size:14px;font-weight:600}
.head-actions{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
.card-body{padding:18px}

/* Forms */
label{display:block;font-size:12px;color:var(--muted);margin-bottom:4px}
input[type=text],input[type=number]{
  background:#141414;border:1px solid var(--border);color:var(--text);
  padding:7px 10px;border-radius:5px;font-size:13px;outline:none;width:100%
}
input[type=text]:focus,input[type=number]:focus{border-color:var(--accent)}
input[type=file]{display:none}

/* Buttons */
.btn{display:inline-flex;align-items:center;gap:5px;padding:7px 14px;border-radius:5px;
     font-size:13px;font-weight:600;cursor:pointer;border:none;transition:opacity .15s;white-space:nowrap}
.btn:hover:not(:disabled){opacity:.82}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-primary{background:var(--accent);color:#fff}
.btn-ghost{background:#2a2a2a;color:var(--text);border:1px solid var(--border)}
.btn-sm{padding:5px 10px;font-size:12px}

/* Switch tabs */
.tabs{display:inline-flex;border:1px solid var(--border);border-radius:5px;overflow:hidden;margin-bottom:14px}
.tabs button{padding:6px 14px;background:none;border:none;color:var(--muted);cursor:pointer;font-size:13px;transition:.15s}
.tabs button.on{background:var(--accent);color:#fff;font-weight:600}

/* File drop zone */
.dropzone{border:2px dashed var(--border);border-radius:6px;padding:18px;text-align:center;
           cursor:pointer;transition:border-color .2s}
.dropzone:hover,.dropzone.over{border-color:var(--accent)}
.dropzone p{color:var(--muted);font-size:13px}
.dropzone .fname{color:var(--accent);font-weight:600;margin-top:5px;font-size:13px}

/* Status */
.status{font-size:13px;padding:8px 12px;border-radius:5px;margin-top:10px}
.s-ok{background:rgba(60,180,80,.12);color:#6d6;border:1px solid #2a5a2a}
.s-err{background:rgba(220,60,60,.12);color:#f88;border:1px solid #5a2a2a}
.s-info{background:rgba(60,120,220,.12);color:#8af;border:1px solid #2a3a6a}
.hidden{display:none}

/* Slot table */
.slot-table{width:100%;border-collapse:collapse;font-size:13px}
.slot-table th{text-align:left;padding:7px 10px;color:var(--muted);font-weight:500;
               border-bottom:1px solid var(--border);font-size:12px}
.slot-table td{padding:5px 10px;border-bottom:1px solid rgba(255,255,255,.04);vertical-align:middle}
.slot-table tr:hover td{background:rgba(255,255,255,.025)}
.slot-table input[type=number]{width:58px;padding:4px 6px}
.tag{display:inline-block;padding:2px 6px;border-radius:3px;font-size:11px}
.tag-h{background:rgba(80,140,255,.18);color:#9af}
.tag-v{background:rgba(160,90,255,.18);color:#c9f}
.mono{font-family:monospace}
.muted{color:var(--muted)}

/* Preview */
.previews{display:flex;gap:14px;flex-wrap:wrap;margin-top:4px}
.prev-card{flex:0 0 auto}
.prev-title{font-size:12px;color:var(--muted);margin-bottom:6px;display:flex;align-items:center;gap:8px}
.prev-card img{max-width:320px;border:1px solid var(--border);border-radius:4px;display:block}
.link{color:var(--accent);cursor:pointer;text-decoration:underline;font-size:12px}

.row{display:flex;gap:16px;flex-wrap:wrap}
.col{flex:1;min-width:280px}
hr{border:none;border-top:1px solid var(--border);margin:16px 0}
</style>
</head>
<body>
<div class="wrap">
<h1>车辆PDF模板工具 <em>· Web版</em></h1>

<!-- ① 加载模板 -->
<div class="card">
  <div class="card-head"><span class="num">1</span><h2>加载PDF模板</h2></div>
  <div class="card-body">
    <div class="tabs" id="tpl-tabs">
      <button class="on" onclick="setTplMode('default')">默认模板</button>
      <button onclick="setTplMode('path')">指定路径</button>
      <button onclick="setTplMode('upload')">上传文件</button>
    </div>

    <div id="tpl-default">
      <p class="muted" style="font-size:13px">使用当前目录的
        <span class="mono" style="color:#aaa">template_decrypted.pdf</span>
      </p>
    </div>
    <div id="tpl-path" class="hidden">
      <label>PDF 文件绝对路径</label>
      <input type="text" id="pdf-path" placeholder="/path/to/template.pdf">
    </div>
    <div id="tpl-upload" class="hidden">
      <div class="dropzone" id="pdf-drop" onclick="document.getElementById('pdf-file').click()">
        <p>点击选择 或 拖拽 PDF 文件到此</p>
        <div class="fname" id="pdf-fname"></div>
        <input type="file" id="pdf-file" accept=".pdf" onchange="onPdfPick(this)">
      </div>
    </div>

    <div style="margin-top:14px">
      <button class="btn btn-primary" onclick="scanTemplate()">🔍 扫描模板</button>
    </div>
    <div id="scan-st"></div>
  </div>
</div>

<!-- ② 配置槽位 -->
<div class="card hidden" id="card2">
  <div class="card-head">
    <span class="num">2</span><h2>配置槽位映射</h2>
    <div class="head-actions">
      <button class="btn btn-ghost btn-sm" onclick="autoAssign()">自动编号</button>
      <button class="btn btn-ghost btn-sm" onclick="exportCfg()">导出配置</button>
      <button class="btn btn-ghost btn-sm" onclick="document.getElementById('import-file').click()">导入配置</button>
      <input type="file" id="import-file" accept=".json" onchange="importCfg(this)">
    </div>
  </div>
  <div class="card-body">
    <p class="muted" style="font-size:12px;margin-bottom:14px">
      为每个图片槽位分配照片编号，编号对应用户拍摄顺序（01.jpg, 02.jpg …）
    </p>
    <div class="row">
      <div class="col" style="min-width:360px;overflow-x:auto">
        <table class="slot-table">
          <thead>
            <tr>
              <th>照片编号</th><th>页码</th><th>xref</th><th>尺寸</th><th>方向</th>
            </tr>
          </thead>
          <tbody id="slot-tbody"></tbody>
        </table>
      </div>
      <div class="col">
        <p class="muted" style="font-size:12px;margin-bottom:8px">页面预览（点击加载/刷新）</p>
        <div class="previews" id="previews"></div>
      </div>
    </div>
    <hr>
    <button class="btn btn-primary" onclick="saveMap()">💾 保存映射并刷新预览</button>
    <div id="map-st"></div>
  </div>
</div>

<!-- ③ 应用照片 -->
<div class="card hidden" id="card3">
  <div class="card-head"><span class="num">3</span><h2>应用照片 → 生成PDF</h2></div>
  <div class="card-body">
    <div class="tabs" id="photo-tabs">
      <button class="on" onclick="setPhotoMode('dir')">本地文件夹</button>
      <button onclick="setPhotoMode('zip')">上传ZIP</button>
    </div>

    <div id="photos-dir">
      <label>照片文件夹路径（文件命名为 01.jpg, 02.jpg …）</label>
      <input type="text" id="dir-input" placeholder="photos  或  /absolute/path/photos">
    </div>
    <div id="photos-zip" class="hidden">
      <div class="dropzone" id="zip-drop" onclick="document.getElementById('zip-file').click()">
        <p>点击选择 或 拖拽 ZIP 文件（含 01.jpg, 02.jpg …）</p>
        <div class="fname" id="zip-fname"></div>
        <input type="file" id="zip-file" accept=".zip" onchange="onZipPick(this)">
      </div>
    </div>

    <div style="margin-top:14px;display:flex;align-items:center;gap:12px">
      <button class="btn btn-primary" id="apply-btn" onclick="applyPhotos()">⚡ 生成PDF</button>
    </div>
    <div id="apply-st"></div>
    <div id="dl-area" style="margin-top:12px"></div>
  </div>
</div>
</div><!-- wrap -->

<script>
// ── State ─────────────────────────────────────────────
let tplMode = 'default', photoMode = 'dir';
let pdfFile = null, zipFile = null;
let slots = [], photoMap = {}, pages = [];

// ── Mode switches ──────────────────────────────────────
function setTplMode(m) {
  tplMode = m;
  ['default','path','upload'].forEach(k =>
    document.getElementById('tpl-'+k).classList.toggle('hidden', k !== m));
  tabSwitch('tpl-tabs', ['default','path','upload'].indexOf(m));
}
function setPhotoMode(m) {
  photoMode = m;
  document.getElementById('photos-dir').classList.toggle('hidden', m !== 'dir');
  document.getElementById('photos-zip').classList.toggle('hidden', m !== 'zip');
  tabSwitch('photo-tabs', m === 'dir' ? 0 : 1);
}
function tabSwitch(id, idx) {
  document.getElementById(id).querySelectorAll('button')
    .forEach((b,i) => b.classList.toggle('on', i === idx));
}
function onPdfPick(inp) {
  pdfFile = inp.files[0];
  document.getElementById('pdf-fname').textContent = pdfFile?.name || '';
}
function onZipPick(inp) {
  zipFile = inp.files[0];
  document.getElementById('zip-fname').textContent = zipFile?.name || '';
}

// ── Drag-and-drop zones ────────────────────────────────
function initDrop(zoneId, onFile) {
  const z = document.getElementById(zoneId);
  z.addEventListener('dragover', e => { e.preventDefault(); z.classList.add('over'); });
  z.addEventListener('dragleave', () => z.classList.remove('over'));
  z.addEventListener('drop', e => {
    e.preventDefault(); z.classList.remove('over');
    if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0]);
  });
}
initDrop('pdf-drop', f => {
  if (!f.name.endsWith('.pdf')) return;
  pdfFile = f; document.getElementById('pdf-fname').textContent = f.name;
});
initDrop('zip-drop', f => {
  if (!f.name.endsWith('.zip')) return;
  zipFile = f; document.getElementById('zip-fname').textContent = f.name;
});

// ── Scan ──────────────────────────────────────────────
async function scanTemplate() {
  const fd = new FormData();
  if (tplMode === 'upload' && pdfFile) fd.append('pdf', pdfFile);
  else if (tplMode === 'path') fd.append('path', document.getElementById('pdf-path').value.trim());

  setSt('scan-st', 'info', '扫描中...');
  try {
    const r = await fetch('/api/scan', {method:'POST', body:fd});
    const d = await r.json();
    if (d.error) { setSt('scan-st','err', d.error); return; }

    slots = d.slots;
    photoMap = Object.fromEntries(Object.entries(d.photo_map).map(([k,v])=>[+k,+v]));
    pages = d.pages;

    setSt('scan-st','ok', `✓ 发现 ${d.total} 个图片槽位，共涉及第 ${pages.join('、')} 页`);
    renderTable();
    renderPreviewCards();
    document.getElementById('card2').classList.remove('hidden');
    document.getElementById('card3').classList.remove('hidden');
  } catch(e) { setSt('scan-st','err', e.message); }
}

// ── Slot table ─────────────────────────────────────────
function renderTable() {
  const xrefToPhoto = {};
  Object.entries(photoMap).forEach(([n,x]) => xrefToPhoto[x] = +n);

  const tbody = document.getElementById('slot-tbody');
  tbody.innerHTML = '';
  slots.forEach(s => {
    const pn = xrefToPhoto[s.xref] ?? '';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><input type="number" min="1" max="99" value="${pn}"
           onchange="onNumChange(${s.xref}, this.value)"></td>
      <td>第 ${s.page} 页</td>
      <td class="mono muted" style="font-size:12px">${s.xref}</td>
      <td class="muted" style="font-size:12px">${s.w}×${s.h}</td>
      <td><span class="tag ${s.orient==='横拍'?'tag-h':'tag-v'}">${s.orient}</span></td>`;
    tbody.appendChild(tr);
  });
}

function onNumChange(xref, val) {
  // 移除该 xref 的旧条目
  for (const k of Object.keys(photoMap)) {
    if (photoMap[k] === xref) delete photoMap[k];
  }
  if (val !== '') photoMap[+val] = xref;
}

function autoAssign() {
  photoMap = {};
  slots.forEach((s,i) => photoMap[i+1] = s.xref);
  renderTable();
}

// ── Previews ───────────────────────────────────────────
function renderPreviewCards() {
  const panel = document.getElementById('previews');
  panel.innerHTML = '';
  pages.forEach(pg => {
    const div = document.createElement('div');
    div.className = 'prev-card';
    div.id = 'prev-'+pg;
    div.innerHTML = `<div class="prev-title">第 ${pg} 页</div>
      <span class="link" onclick="loadPreview(${pg})">点击加载预览</span>`;
    panel.appendChild(div);
  });
}

async function loadPreview(pg) {
  const card = document.getElementById('prev-'+pg);
  card.innerHTML = `<div class="prev-title">第 ${pg} 页</div>
    <span class="muted" style="font-size:12px">加载中...</span>`;
  const img = new Image();
  img.src = `/api/preview/${pg}?t=${Date.now()}`;
  img.style.maxWidth = '320px';
  img.title = '点击刷新';
  img.onclick = () => loadPreview(pg);
  img.onload = () => {
    card.innerHTML = `<div class="prev-title">第 ${pg} 页
      <span class="link" onclick="loadPreview(${pg})">刷新</span></div>`;
    card.appendChild(img);
  };
  img.onerror = () => {
    card.innerHTML = `<div class="prev-title">第 ${pg} 页</div>
      <span class="link" onclick="loadPreview(${pg})">加载失败，点击重试</span>`;
  };
}

// ── Save map ───────────────────────────────────────────
async function saveMap() {
  await fetch('/api/update-map', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({photo_map: photoMap}),
  });
  setSt('map-st','ok','✓ 已保存，正在刷新预览...');
  // 刷新已加载的预览
  pages.forEach(pg => {
    const img = document.querySelector(`#prev-${pg} img`);
    if (img) loadPreview(pg);
  });
  setTimeout(() => document.getElementById('map-st').textContent='', 2000);
}

// ── Config export/import ───────────────────────────────
function exportCfg() {
  fetch('/api/export-config').then(r=>r.blob()).then(b=>{
    const a = document.createElement('a');
    a.href = URL.createObjectURL(b);
    a.download = 'slot_config.json'; a.click();
  });
}
function importCfg(inp) {
  const file = inp.files[0]; if (!file) return;
  const reader = new FileReader();
  reader.onload = async e => {
    const data = JSON.parse(e.target.result);
    const r = await fetch('/api/import-config', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(data),
    });
    const d = await r.json();
    if (data.photo_map) photoMap = Object.fromEntries(
      Object.entries(data.photo_map).map(([k,v])=>[+k,+v]));
    if (data.slots) slots = data.slots;
    renderTable();
    alert(`导入成功：${d.total} 个槽位`);
  };
  reader.readAsText(file);
}

// ── Apply photos ───────────────────────────────────────
async function applyPhotos() {
  const btn = document.getElementById('apply-btn');
  btn.disabled = true; btn.textContent = '生成中...';
  setSt('apply-st','info','正在处理，请稍候...');
  document.getElementById('dl-area').innerHTML = '';

  // 先同步 map
  await fetch('/api/update-map', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({photo_map: photoMap}),
  });

  let res;
  try {
    if (photoMode === 'zip' && zipFile) {
      const fd = new FormData();
      fd.append('photos_zip', zipFile);
      fd.append('photo_map', JSON.stringify(photoMap));
      res = await fetch('/api/apply', {method:'POST', body:fd});
    } else {
      const dir = document.getElementById('dir-input').value.trim() || 'photos';
      res = await fetch('/api/apply', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({photos_dir: dir}),
      });
    }

    if (!res.ok) {
      const t = await res.text();
      setSt('apply-st','err', t);
      return;
    }

    const replaced = res.headers.get('X-Replaced') || '?';
    const missing  = res.headers.get('X-Missing')  || '';
    const missMsg  = missing ? `，缺少编号: ${missing}` : '';
    setSt('apply-st','ok', `✓ 成功替换 ${replaced} 张${missMsg}`);

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    document.getElementById('dl-area').innerHTML =
      `<a class="btn btn-primary" href="${url}" download="output.pdf">⬇ 下载 output.pdf</a>`;
  } catch(e) {
    setSt('apply-st','err', e.message);
  } finally {
    btn.disabled = false; btn.textContent = '⚡ 生成PDF';
  }
}

// ── Util ───────────────────────────────────────────────
function setSt(id, type, msg) {
  const el = document.getElementById(id);
  el.className = 'status ' + {ok:'s-ok',err:'s-err',info:'s-info'}[type];
  el.textContent = msg;
  el.style.display = msg ? '' : 'none';
}
</script>
</body>
</html>"""


# ─── 启动 ──────────────────────────────────────────────────────

if __name__ == '__main__':
    import threading, webbrowser
    url = 'http://localhost:8877'
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    if debug:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    print(f'\n  车辆PDF模板工具 - Web版')
    print(f'  ─────────────────────')
    print(f'  打开浏览器: {url}')
    print(f'  按 Ctrl+C 停止\n')
    app.run(host='0.0.0.0', port=8877, debug=debug)
