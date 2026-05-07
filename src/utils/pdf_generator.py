# PDF生成模块
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io

# 注册中文字体
try:
    pdfmetrics.registerFont(TTFont('WenQuanYi', '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'))
    CHINESE_FONT = 'WenQuanYi'
except:
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        CHINESE_FONT = 'DejaVuSans'
    except:
        CHINESE_FONT = 'Helvetica'

def _flatten_questions(questions):
    """将嵌套结构的题目展平"""
    flattened = []
    for q in questions:
        q_type = q.get('type', '未知')
        for idx, sq in enumerate(q.get('questions', []), 1):
            flat_q = {
                'type': q_type,
                'question': sq.get('question', ''),
                'answer': sq.get('answer', ''),
                'knowledge_point': sq.get('knowledge', ''),
                'options': sq.get('options', [])
            }
            flattened.append(flat_q)
    return flattened

def generate_questions_pdf(questions, subject, grade, title="智能学习助手 - 诊断测试"):
    """生成题目PDF"""
    # 处理嵌套结构
    if questions and isinstance(questions[0], dict) and 'questions' in questions[0]:
        questions = _flatten_questions(questions)

    buffer = io.BytesIO()

    # 创建PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    # 样式
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        fontName=CHINESE_FONT,
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=10*mm,
        textColor=colors.HexColor('#333333')
    )

    header_style = ParagraphStyle(
        'Header',
        fontName=CHINESE_FONT,
        fontSize=12,
        alignment=TA_LEFT,
        spaceAfter=5*mm,
        textColor=colors.HexColor('#666666')
    )

    question_style = ParagraphStyle(
        'Question',
        fontName=CHINESE_FONT,
        fontSize=11,
        leading=18,
        spaceAfter=8*mm,
        textColor=colors.black
    )

    option_style = ParagraphStyle(
        'Option',
        fontName=CHINESE_FONT,
        fontSize=10,
        leading=15,
        leftIndent=15*mm,
        spaceAfter=3*mm
    )

    # 内容元素
    elements = []

    # 标题
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(f"学科：{subject}　　年级：{grade}　　题目数量：{len(questions)}", header_style))
    elements.append(Spacer(1, 10*mm))

    # 题目列表
    for i, q in enumerate(questions, 1):
        q_type = q.get('type', '未知')
        q_text = q.get('question', '')
        q_answer = q.get('answer', '')
        q_knowledge = q.get('knowledge_point', q.get('knowledge', ''))
        q_options = q.get('options', [])

        # 题目标题
        elements.append(Paragraph(f"<b>题目 {i}</b>（{q_type}）", question_style))

        # 题目内容
        elements.append(Paragraph(f"{q_text}", question_style))

        # 选项（如果是选择题）
        if q_options:
            option_labels = ['A', 'B', 'C', 'D', 'E', 'F']
            for j, opt in enumerate(q_options):
                label = option_labels[j] if j < len(option_labels) else chr(65+j)
                elements.append(Paragraph(f"{label}. {opt}", option_style))

        # 答案区（留空或显示）
        answer_text = f"答案：{q_answer}"
        elements.append(Paragraph(answer_text, option_style))

        # 知识点
        if q_knowledge:
            elements.append(Paragraph(f"<font color='#888888'>知识点：{q_knowledge}</font>", option_style))

        elements.append(Spacer(1, 5*mm))

        # 每10题分页
        if i % 10 == 0 and i < len(questions):
            elements.append(PageBreak())

    # 生成PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_answer_sheet_pdf(questions, subject, grade, title="智能学习助手 - 答案卷"):
    """生成答案卷PDF"""
    # 处理嵌套结构
    if questions and isinstance(questions[0], dict) and 'questions' in questions[0]:
        questions = _flatten_questions(questions)

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        fontName=CHINESE_FONT,
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=10*mm,
        textColor=colors.HexColor('#333333')
    )

    header_style = ParagraphStyle(
        'Header',
        fontName=CHINESE_FONT,
        fontSize=12,
        alignment=TA_LEFT,
        spaceAfter=5*mm,
        textColor=colors.HexColor('#666666')
    )

    question_style = ParagraphStyle(
        'Question',
        fontName=CHINESE_FONT,
        fontSize=11,
        leading=18,
        spaceAfter=8*mm,
        textColor=colors.black
    )

    answer_style = ParagraphStyle(
        'Answer',
        fontName=CHINESE_FONT,
        fontSize=10,
        leading=15,
        leftIndent=15*mm,
        spaceAfter=5*mm
    )

    elements = []
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(f"学科：{subject}　　年级：{grade}　　题目数量：{len(questions)}", header_style))
    elements.append(Spacer(1, 10*mm))

    for i, q in enumerate(questions, 1):
        q_type = q.get('type', '未知')
        q_text = q.get('question', '')
        q_answer = q.get('answer', '')
        q_options = q.get('options', [])

        elements.append(Paragraph(f"<b>题目 {i}</b>（{q_type}）", question_style))
        elements.append(Paragraph(f"{q_text}", question_style))

        if q_options:
            option_labels = ['A', 'B', 'C', 'D', 'E', 'F']
            for j, opt in enumerate(q_options):
                label = option_labels[j] if j < len(option_labels) else chr(65+j)
                elements.append(Paragraph(f"{label}. {opt}", answer_style))

        elements.append(Paragraph(f"<b>答案：{q_answer}</b>", answer_style))
        elements.append(Spacer(1, 5*mm))

        if i % 10 == 0 and i < len(questions):
            elements.append(PageBreak())

    doc.build(elements)
    buffer.seek(0)
    return buffer