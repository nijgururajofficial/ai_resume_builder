import logging
import os
import datetime
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from xhtml2pdf import pisa

class PdfDocxGenerator:
    """
    Converts Markdown into a visually styled, professional DOCX and PDF.
    This version uses python-docx for DOCX and xhtml2pdf for PDF.
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
        bottom_bdr.set(qn('w:sz'), '6')  # Border size
        bottom_bdr.set(qn('w:space'), '1')
        bottom_bdr.set(qn('w:color'), 'auto')
        p_bdr.append(bottom_bdr)

    def to_docx(self, output_path: str):
        """
        Creates a visually styled .docx file.
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
            
            # Skip adding a paragraph for table elements since the table is added directly
            if line.startswith('**') and (i + 1 < len(lines)) and '|' in lines[i+1]:
                table = doc.add_table(rows=1, cols=2)
                table.autofit = True
                
                left_cell = table.cell(0, 0)
                left_p = left_cell.paragraphs[0]
                left_p.add_run(line.replace('**', '')).bold = True
                left_cell.width = Inches(4.5)

                right_cell = table.cell(0, 1)
                right_p = right_cell.paragraphs[0]
                right_p.text = lines[i+1]
                right_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                right_cell.width = Inches(2.5)
                
                for cell in [left_cell, right_cell]:
                    cell.paragraphs[0].paragraph_format.space_before = Pt(0)
                    cell.paragraphs[0].paragraph_format.space_after = Pt(4)
                
                i += 1
            
            else:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)

                if line.startswith('# '):
                    run = p.add_run(line.replace('# ', ''))
                    run.font.name = self.font_name
                    run.font.size = Pt(24)
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_after = Pt(4)
                
                elif line.startswith('### '):
                    run = p.add_run(line.replace('### ', ''))
                    run.font.name = self.font_name
                    run.font.size = Pt(11)
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_after = Pt(6)

                elif ' | ' in line and '@' in line:
                    p.text = line
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_after = Pt(12)

                elif line.startswith('## '):
                    p.text = line.replace('## ', '').upper()
                    p.runs[0].font.bold = True
                    p.runs[0].font.size = Pt(12)
                    p.paragraph_format.space_after = Pt(4)
                    self._set_paragraph_border(p)
                
                elif line.startswith('- '):
                    p.text = f"•\t{line[2:]}"
                    p.paragraph_format.left_indent = Inches(0.25)
                    p.paragraph_format.space_after = Pt(2)

                elif line.startswith('**'):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        p.add_run(parts[0].replace('**', '')).bold = True
                        p.add_run(f":{parts[1]}")
                    else:
                        p.add_run(line).bold = True
                    p.paragraph_format.space_after = Pt(3)
            i += 1
        
        doc.save(output_path)
        logging.info("Styled DOCX generation complete.")

    def to_pdf(self, output_path: str):
        """
        Creates a visually styled .pdf file using xhtml2pdf.
        """
        logging.info(f"Generating styled PDF file with xhtml2pdf at: {output_path}")
        
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
            elif line.startswith('**') and (i + 1 < len(lines)) and '|' in lines[i+1]:
                title = line.replace('**', '')
                details = lines[i+1]
                html_lines.append(f"""
                    <table class="item-header">
                        <tr>
                            <td><strong>{title}</strong></td>
                            <td class="details">{details}</td>
                        </tr>
                    </table>
                """)
                i += 1
            elif line.startswith('- '):
                if not (html_lines and html_lines[-1].strip().startswith('<ul>')):
                    html_lines.append('<ul>')
                html_lines.append(f"<li>{line[2:]}</li>")
                if i + 1 >= len(lines) or not lines[i+1].strip().startswith('- '):
                    html_lines.append('</ul>')
            elif line.startswith('**'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    html_lines.append(f"<p class='skills'><strong>{parts[0].replace('**', '')}</strong>:{parts[1]}</p>")
                else:
                    html_lines.append(f"<p class='skills'><strong>{line.replace('**', '')}</strong></p>")
            i += 1
        
        html_content = "\n".join(html_lines)

        css_string = f"""
            @page {{ 
                margin: 0.5in 0.75in; 
            }}
            body {{ 
                font-family: '{self.font_name}', sans-serif; 
                font-size: 10.5pt; 
                color: #333; 
            }}
            h1 {{ font-size: 24pt; text-align: center; margin: 0; font-weight: normal; }}
            h3 {{ font-size: 11pt; text-align: center; margin: 0 0 6pt 0; font-weight: normal; }}
            .contact {{ font-size: 10.5pt; text-align: center; margin-bottom: 12pt; }}
            h2 {{ 
                font-size: 12pt; 
                font-weight: bold;
                margin: 12pt 0 4pt 0; 
                padding-bottom: 2px;
                border-bottom: 1px solid #333; 
            }}
            .item-header {{ 
                width: 100%;
                margin-top: 5pt; 
                border-spacing: 0;
            }}
            .item-header .details {{
                text-align: right;
                font-size: 10.5pt;
            }}
            ul {{ 
                margin: 4pt 0; 
                padding-left: 20px; 
                list-style-type: disc;
            }}
            li {{ margin-bottom: 3pt; }}
            p {{ margin: 0; padding: 0; }}
            .skills {{ margin-bottom: 3pt; }}
        """

        final_html = f"<html><head><style>{css_string}</style></head><body>{html_content}</body></html>"

        with open(output_path, "w+b") as pdf_file:
            pisa_status = pisa.CreatePDF(
                src=final_html,
                dest=pdf_file
            )
        
        if pisa_status.err:
            logging.error(f"Error generating PDF: {pisa_status.err}")
        else:
            logging.info("Styled PDF generation complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    sample_markdown = """# John Doe
### Software Engineer | Full Stack Developer
john.doe@email.com | (555) 123-4567 | linkedin.com/in/johndoe | github.com/johndoe

## Experience

**Senior Software Engineer**
TechCorp Inc. | 2021 - Present
- Led development of microservices architecture serving 1M+ users.
- Implemented CI/CD pipeline reducing deployment time by 60%.
- Mentored 3 junior developers and conducted code reviews.

**Software Developer**
StartupXYZ | 2019 - 2021
- Built RESTful APIs using Node.js and Express.
- Developed responsive web applications with React and TypeScript.
- Collaborated with design team to implement user interface improvements.

## Skills

**Programming Languages**: JavaScript, TypeScript, Python, Java, SQL
**Frameworks & Tools**: React, Node.js, Express, Django, Docker, AWS
**Databases**: PostgreSQL, MongoDB, Redis
**Other**: Git, CI/CD, Agile methodologies, RESTful APIs"""

    # --- SCRIPT EXECUTION LOGIC ---

    # 1. Define the output directory and ensure it exists
    # os.path.join("..", "output") creates a path like "../output"
    output_dir = os.path.join("..", "output")
    os.makedirs(output_dir, exist_ok=True)
    logging.info(f"Output directory is set to: {os.path.abspath(output_dir)}")

    # 2. Extract the name from the first line of the markdown
    # e.g., "# John Doe" -> "john-doe"
    try:
        first_line = sample_markdown.split('\n')[0]
        name = first_line.replace('# ', '').strip().lower().replace(' ', '-')
    except IndexError:
        name = "resume" # Fallback name

    # 3. Get the current date in ddmm format
    # e.g., August 12th -> "1208"
    date_str = datetime.date.today().strftime('%d%m')

    # 4. Create the base filename
    # e.g., "john-doe-1208"
    base_filename = f"{name}-{date_str}"

    # 5. Construct the full output paths
    docx_output = os.path.join(output_dir, f"{base_filename}.docx")
    pdf_output = os.path.join(output_dir, f"{base_filename}.pdf")

    # --- END SCRIPT EXECUTION LOGIC ---

    # Initialize the generator
    generator = PdfDocxGenerator(sample_markdown)
    
    # Test DOCX generation
    try:
        generator.to_docx(docx_output)
        print(f"✅ DOCX file generated successfully: {docx_output}")
    except Exception as e:
        print(f"❌ Error generating DOCX: {e}")
        logging.exception("DOCX generation failed")
    
    # Test PDF generation
    try:
        generator.to_pdf(pdf_output)
        print(f"✅ PDF file generated successfully: {pdf_output}")
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        logging.exception("PDF generation failed")
    
    print("\n🎉 Testing complete! Check the output files in the specified directory.")