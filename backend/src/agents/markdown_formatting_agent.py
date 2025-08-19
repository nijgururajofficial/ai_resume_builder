from turtle import left
from typing import Dict, List

class MarkdownFormattingAgent:
    """
    Formats tailored content into a clean, ATS-compliant Markdown resume.
    This version creates a specific structure for complex, single-line headers
    and ensures all bullet point content is plain text.
    """

    def _format_contact(self, contact: Dict) -> str:
        parts = [
            contact.get('phone'),
            contact.get('github'),
            contact.get('linkedin'),
            contact.get('email')
        ]
        return ' | '.join(filter(None, parts))

    # --- THIS IS THE ONLY METHOD THAT HAS BEEN MODIFIED ---
    def _format_experience_or_projects(self, title: str, items: List[Dict], is_project: bool = False) -> List[str]:
        lines = [f"## {title}"]
        for item in items:
            if is_project:
                # Create a simple, single line for the project header. No '|||'.
                project_header = f"**{item.get('name', '')}** | *{item.get('technologies', '')}*"
                lines.append(project_header)
            else: # Work Experience still uses the two-column separator
                left_part = f"**{item.get('title', '')}** | {item.get('company', '')} | {item.get('location', '')}"
                right_part = f"{item.get('dates', '')}"
                lines.append(f"{left_part} ||| {right_part}")
            
            description_points = item.get('description' if is_project else 'responsibilities', [])
            
            for point in description_points:
                clean_point = point.replace('**', '').replace('*', '').replace('`', '')
                lines.append(f"- {clean_point}")
            lines.append("")
        return lines

    def _format_skills(self, skills: Dict) -> List[str]:
        """Formats skills with one category per line for the generator to parse."""
        lines = [f"## Skills"]
        for category, skill_list in skills.items():
            if skill_list:
                lines.append(f"**{category}:** {', '.join(skill_list)}")
        return lines

    def _format_education(self, items: List[Dict]) -> List[str]:
        """
        Formats education with two simple lines to ensure it is always rendered.
        """
        lines = [f"## Education"]
        for item in items:
            # Line 1: Degree and Dates, formatted like a project header.
            degree_line = f"**{item.get('degree', '')}** ||| {item.get('dates', '')}"
            lines.append(degree_line)
            
            # Line 2: Institution on its own line.
            institution_line = f"*{item.get('institution', '')}*"
            lines.append(institution_line)
            
            lines.append("")
        return lines

    def run(self, user_profile: Dict, tailored_content: Dict) -> str:
        """Constructs the full resume in a structured Markdown format."""
        resume_parts = []
        resume_parts.append(f"# {user_profile.get('name', 'User Name')}")
        resume_parts.append(self._format_contact(user_profile.get('contact', {})))
        resume_parts.append("")

        if tailored_content.get('tailored_skills'):
            resume_parts.extend(self._format_skills(tailored_content['tailored_skills']))
            resume_parts.append("")

        if tailored_content.get('tailored_experience'):
            resume_parts.extend(self._format_experience_or_projects("Experience", tailored_content['tailored_experience']))

        if tailored_content.get('tailored_projects'):
            resume_parts.extend(self._format_experience_or_projects("Projects", tailored_content['tailored_projects'], is_project=True))
            
        if tailored_content.get('education'):
             resume_parts.extend(self._format_education(tailored_content['education']))

        return "\n".join(resume_parts).strip()