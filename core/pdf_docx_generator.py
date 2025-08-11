import logging
import markdown2
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from weasyprint import HTML, CSS

class PdfDocxGenerator:
    """
    Converts Markdown into a visually styled, professional DOCX and PDF.
    This version replicates a modern resume format, balancing aesthetics with
    parsability for modern ATS.
    """

    def __init__(self, markdown_content: str):
        self.markdown = markdown_content
        self.font_name = 'Calibri'  # A standard, professional font

    def _set_paragraph_border(self, paragraph):
        """Helper function to add a bottom border to a paragraph in DOCX."""
        p_pr = paragraph._p.get_or_add_pPr()
        p_bdr = OxmlElement('w:pBdr')
        p_pr.append(p_bdr)
        bottom_bdr = OxmlElement('w:bottom')
        bottom_bdr.set(qn('w:val'), 'single')
        bottom_bdr.set(qn('w:sz'), '6') # Border size
        bottom_bdr.set(qn('w:space'), '1')
        bottom_bdr.set(qn('w:color'), 'auto')
        p_bdr.append(bottom_bdr)

    def to_docx(self, output_path: str):
        """
        Creates a visually styled .docx file that mimics the target image.
        """
        logging.info(f"Generating styled DOCX file at: {output_path}")
        doc = Document()
        # Set document margins
        doc.sections[0].left_margin = Inches(0.75)
        doc.sections[0].right_margin = Inches(0.75)
        doc.sections[0].top_margin = Inches(0.5)
        doc.sections[0].bottom_margin = Inches(0.5)

        # Default font for the document
        doc.styles['Normal'].font.name = self.font_name
        doc.styles['Normal'].font.size = Pt(10.5)

        lines = self.markdown.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            p = doc.add_paragraph()
            # Remove default paragraph spacing
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)

            if line.startswith('# '): # Name
                run = p.add_run(line.replace('# ', ''))
                run.font.name = self.font_name
                run.font.size = Pt(24)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(4)
            
            elif line.startswith('### '): # Headline
                run = p.add_run(line.replace('### ', ''))
                run.font.name = self.font_name
                run.font.size = Pt(11)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(6)

            elif ' | ' in line and '@' in line: # Contact Info
                p.text = line
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(12)

            elif line.startswith('## '): # Section Headers (e.g., "## Experience")
                p.text = line.replace('## ', '').upper()
                p.runs[0].font.bold = True
                p.runs[0].font.size = Pt(12)
                p.paragraph_format.space_after = Pt(4)
                self._set_paragraph_border(p) # Add the horizontal line

            elif line.startswith('**') and '|' in lines[i+1]: # Experience/Project Title
                # This is the tricky part: use a table for left/right alignment
                table = doc.add_table(rows=1, cols=2)
                table.autofit = True
                
                # Left cell: Job Title
                left_cell = table.cell(0, 0)
                left_p = left_cell.paragraphs[0]
                left_p.add_run(line.replace('**', '')).bold = True
                left_cell.width = Inches(4.5)

                # Right cell: Company/Date
                right_cell = table.cell(0, 1)
                right_p = right_cell.paragraphs[0]
                right_p.text = lines[i+1]
                right_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                right_cell.width = Inches(2.5)
                
                # Remove spacing from table paragraphs
                for cell in [left_cell, right_cell]:
                    cell.paragraphs[0].paragraph_format.space_before = Pt(0)
                    cell.paragraphs[0].paragraph_format.space_after = Pt(4)
                
                i += 1 # Skip the next line since we've processed it
            
            elif line.startswith('- '): # Bullet points
                p.text = f"•\t{line[2:]}" # Use a tab for proper indentation
                p.paragraph_format.left_indent = Inches(0.25)
                p.paragraph_format.space_after = Pt(2)

            elif line.startswith('**'): # Skills
                parts = line.split(':')
                p.add_run(parts[0].replace('**', '')).bold = True
                p.add_run(f":{parts[1]}")
                p.paragraph_format.space_after = Pt(3)

            i += 1
        
        doc.save(output_path)
        logging.info("Styled DOCX generation complete.")

    def to_pdf(self, output_path: str):
        """
        Creates a visually styled .pdf file using HTML and CSS.
        """
        logging.info(f"Generating styled PDF file at: {output_path}")
        
        # Convert markdown to a more structured HTML
        html_lines = []
        lines = self.markdown.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('# '):
                html_lines.append(f"<h1>{line.replace('# ', '')}</h1>")
            elif line.startswith('### '):
                html_lines.append(f"<h3>{line.replace('### ', '')}</h3>")
            elif ' | ' in line and '@' in line:
                html_lines.append(f"<p class='contact'>{line}</p>")
            elif line.startswith('## '):
                html_lines.append(f"<h2>{line.replace('## ', '').upper()}</h2>")
            elif line.startswith('**') and '|' in lines[i+1]:
                title = line.replace('**', '')
                details = lines[i+1]
                html_lines.append(f"<div class='item-header'><span><strong>{title}</strong></span><span>{details}</span></div>")
                i += 1
            elif line.startswith('- '):
                if not html_lines[-1].startswith('<ul>'):
                    html_lines.append('<ul>')
                html_lines.append(f"<li>{line[2:]}</li>")
                if i+1 >= len(lines) or not lines[i+1].strip().startswith('- '):
                    html_lines.append('</ul>')
            elif line.startswith('**'):
                html_lines.append(f"<p class='skills'>{line}</p>")
            i += 1

        html_content = "\n".join(html_lines)

        # CSS to style the HTML to look like the image
        css = CSS(string=f"""
            @page {{ margin: 0.5in 0.75in; }}
            body {{ font-family: '{self.font_name}', sans-serif; font-size: 10.5pt; color: #333; }}
            h1 {{ font-size: 24pt; text-align: center; margin: 0; font-weight: normal; }}
            h3 {{ font-size: 11pt; text-align: center; margin: 0 0 6pt 0; font-weight: normal; }}
            .contact {{ font-size: 10pt; text-align: center; margin-bottom: 12pt; }}
            h2 {{ 
                font-size: 12pt; 
                font-weight: bold;
                margin: 12pt 0 4pt 0; 
                padding-bottom: 2px;
                border-bottom: 1px solid #333; 
            }}
            .item-header {{ display: flex; justify-content: space-between; margin-top: 5pt; }}
            ul {{ margin: 0; padding-left: 20px; }}
            li {{ margin-bottom: 3pt; }}
            .skills {{ margin: 0 0 3pt 0; }}
        """)
        
        HTML(string=html_content).write_pdf(output_path, stylesheets=[css])
        logging.info("Styled PDF generation complete.")