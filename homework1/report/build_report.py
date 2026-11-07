#!/usr/bin/env python3
"""Render the editable report Markdown to a paginated, selectable-text PDF."""
from pathlib import Path
import argparse
import datetime
import re
from html import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Preformatted, Image

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, default=ROOT/'Homework1_Report_Draft.md')
parser.add_argument('--output', type=Path, default=ROOT/'Homework1_Report.pdf')
parser.add_argument('--date', type=datetime.date.fromisoformat, default=datetime.date.today(),
                    help='Report/footer date in YYYY-MM-DD format')
args = parser.parse_args()
pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuBold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuMono', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))
pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVuBold',italic='DejaVu',boldItalic='DejaVuBold')
styles = {
    'title': ParagraphStyle('Title', fontName='DejaVuBold', fontSize=20, leading=25, textColor=colors.HexColor('#16344d'), spaceAfter=18),
    'h2': ParagraphStyle('Heading', fontName='DejaVuBold', fontSize=14, leading=19, textColor=colors.HexColor('#16344d'), spaceAfter=14),
    'body': ParagraphStyle('Body',fontName='DejaVu',fontSize=9.5,leading=14.1,spaceAfter=9,wordWrap='CJK'),
    'cell': ParagraphStyle('Cell',fontName='DejaVu',fontSize=8.1,leading=11.5,spaceAfter=0),
    'head': ParagraphStyle('Head',fontName='DejaVuBold',fontSize=8.1,leading=11.5,textColor=colors.white),
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
lines = args.input.read_text().splitlines()
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
    illustration = re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)', line.strip())
    if illustration:
        caption, source = illustration.groups()
        path = (args.input.parent / source).resolve()
        picture = Image(str(path))
        scale = min((A4[0]-90)/picture.imageWidth, 540/picture.imageHeight)
        picture.drawWidth = picture.imageWidth * scale
        picture.drawHeight = picture.imageHeight * scale
        story.extend([picture, Spacer(1, 7), paragraph(caption), Spacer(1, 8)])
        i += 1; continue
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
        # Give numbers and short words enough space before distributing the rest.
        # Character-count proportions alone split headers and crowd timing values.
        minimums = []
        for column in range(n):
            token_widths = []
            for index, row in enumerate(rows):
                font = 'DejaVuBold' if index == 0 else 'DejaVu'
                plain = re.sub(r'[`*]', '', row[column])
                token_widths += [min(110, pdfmetrics.stringWidth(token, font, 8.1))
                                 for token in plain.split()]
            minimums.append(max(token_widths or [0]) + 14)
        if sum(minimums) <= width:
            extra = width - sum(minimums)
            colwidth = [m + extra*w/sum(weights) for m, w in zip(minimums, weights)]
        else:
            colwidth = [width*m/sum(minimums) for m in minimums]
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
    canvas.drawString(45,h-28,'HOMEWORK 1 / FOUR-MACHINE LABORATORY EXPERIMENT')
    canvas.line(45,35,w-45,35)
    canvas.drawString(45,23,'Hadoop 3.3.6 / Java 11 / HDFS + YARN | '+str(args.date.day)+args.date.strftime(' %b %Y'))
    canvas.drawRightString(w-45,23,str(doc.page))
    canvas.restoreState()


output = args.output
doc = SimpleDocTemplate(str(output),pagesize=A4,leftMargin=45,rightMargin=45,
                        topMargin=54,bottomMargin=49,title='Homework 1 - Four-Machine Hadoop Laboratory Experiment',
                        author='Prepared with ChatGPT/Codex assistance')
doc.build(story,onFirstPage=page,onLaterPages=page)
print(output)
