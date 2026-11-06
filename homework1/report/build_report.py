#!/usr/bin/env python3
"""Render the editable report Markdown to a paginated, selectable-text PDF."""
from pathlib import Path
import re
from html import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted

ROOT = Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuBold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuMono', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))
pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVuBold',italic='DejaVu',boldItalic='DejaVuBold')
styles = {
    'title': ParagraphStyle('Title', fontName='DejaVuBold', fontSize=20, leading=25, textColor=colors.HexColor('#16344d'), spaceAfter=18),
    'h2': ParagraphStyle('Heading', fontName='DejaVuBold', fontSize=14, leading=19, textColor=colors.HexColor('#16344d'), spaceAfter=14),
    'body': ParagraphStyle('Body',fontName='DejaVu',fontSize=9.5,leading=14.1,spaceAfter=9,wordWrap='CJK'),
    'cell': ParagraphStyle('Cell',fontName='DejaVu',fontSize=8.1,leading=11.5,spaceAfter=0,wordWrap='CJK'),
    'head': ParagraphStyle('Head',fontName='DejaVuBold',fontSize=8.1,leading=11.5,textColor=colors.white,wordWrap='CJK'),
    'code': ParagraphStyle('Code',fontName='DejaVuMono',fontSize=8.5,leading=12,backColor=colors.HexColor('#f2f5f7'),borderPadding=10,spaceAfter=13),
}


def inline(text):
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    text = re.sub(r'`([^`]+)`',r'<font name="DejaVuMono" size="8.4">\1</font>',text)
    return text


def paragraph(text, style='body'):
    return Paragraph(inline(text), styles[style])


story = []
lines = (ROOT/'Homework1_Report_Draft.md').read_text().splitlines()
i = 0
while i < len(lines):
    line = lines[i]
    if not line.strip():
        i += 1
        continue
    if line == '---PAGE---':
        story.append(PageBreak()); i += 1; continue
    if line.startswith('## '):
        story.append(paragraph(line[3:], 'h2')); i += 1; continue
    if line.startswith('# '):
        story.append(paragraph(line[2:], 'title')); i += 1; continue
    if line.startswith('```'):
        code = []; i += 1
        while i < len(lines) and not lines[i].startswith('```'):
            code.append(lines[i]); i += 1
        i += 1
        story.append(Preformatted('\n'.join(code),styles['code']))
        continue
    if line.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            if not re.match(r'^\|[\s:|\-]+\|$', lines[i]):
                rows.append([cell.strip() for cell in lines[i].strip('|').split('|')])
            i += 1
        n = len(rows[0])
        weights = [max(min(len(row[j]),50) for row in rows) ** .7 for j in range(n)]
        width = A4[0]-90
        colwidth = [width*w/sum(weights) for w in weights]
        contents = [[paragraph(cell,'head' if index == 0 else 'cell') for cell in row] for index,row in enumerate(rows)]
        table = Table(contents,colWidths=colwidth,repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#21465f')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f3f6f8'),colors.white]),
            ('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#21465f')),
            ('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#d4dde4')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),
            ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),
            ('BOTTOMPADDING',(0,0),(-1,-1),7),
        ]))
        story.extend([table,Spacer(1,13)])
        continue
    para = [line]; i += 1
    while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','---PAGE---')):
        para.append(lines[i]); i += 1
    story.append(paragraph(' '.join(para)))


def page(canvas,doc):
    w,h = A4
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#d4dde4')); canvas.setLineWidth(.5)
    canvas.line(45,h-38,w-45,h-38)
    canvas.setFont('DejaVu',7.4);canvas.setFillColor(colors.HexColor('#667583'))
    canvas.drawString(45,h-28,'HOMEWORK 1 / REFERENCE IMPLEMENTATION AND REPORT DRAFT')
    canvas.line(45,35,w-45,35)
    canvas.drawString(45,23,'Unmeasured cloud experiments are explicitly marked. | 3 Nov 2026')
    canvas.drawRightString(w-45,23,str(doc.page))
    canvas.restoreState()


output = ROOT/'Homework1_Report_Draft.pdf'
doc = SimpleDocTemplate(str(output),pagesize=A4,leftMargin=45,rightMargin=45,
                        topMargin=54,bottomMargin=49,title='Homework 1 - Reference Implementation and Report Draft',
                        author='Prepared with ChatGPT/Codex assistance')
doc.build(story,onFirstPage=page,onLaterPages=page)
print(output)
