from typing import Dict, List

class MarkdownFormattingAgent:
    """
    Formats tailored content into a clean, ATS-compliant Markdown resume.
    This version creates a specific structure for complex, single-line headers.
    """

    def _format_contact(self, contact: Dict) -> str:
        parts = [
            contact.get('phone'),
            contact.get('github'),
            contact.get('linkedin'),
            contact.get('email')
        ]
        return ' | '.join(filter(None, parts))

    # FIXED: This method is now much simpler and creates the single-line structure.
    def _format_experience_or_projects(self, title: str, items: List[Dict], is_project: bool = False) -> List[str]:
        lines = [f"## {title}"]
        for item in items:
            if is_project:
                left_part = f"**{item.get('name', '')}**"
                right_part = f"*{item.get('technologies', '')}*"
            else: # Work Experience
                left_part = f"**{item.get('title', '')}** | {item.get('company', '')}"
                right_part = f"{item.get('location', '')} | {item.get('dates', '')}"
            
            # Combine into a single line with a unique separator
            lines.append(f"{left_part} ||| {right_part}")
            
            description_points = item.get('description' if is_project else 'responsibilities', [])
            for point in description_points:
                lines.append(f"- {point}")
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
        lines = [f"## Education"]
        for item in items:
            left_part = f"**{item.get('degree', '')}** | {item.get('institution', '')}"
            right_part = f"{item.get('dates', '')}"
            lines.append(f"{left_part} ||| {right_part}")
            lines.append("")
        return lines

    def run(self, user_profile: Dict, tailored_content: Dict) -> str:
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