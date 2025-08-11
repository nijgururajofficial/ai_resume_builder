from typing import Dict, List

class MarkdownFormattingAgent:
    """
    Formats tailored content into a clean, single-column, ATS-compliant Markdown resume.

    This agent is deterministic and rule-based, not AI-driven. This ensures that
    the final output strictly adheres to universal ATS formatting standards
    (e.g., standard fonts, no tables, single column), which is a common
    failure point for generative models.
    """

    def _format_contact(self, contact: Dict) -> str:
        """Formats contact info into a single, parsable line."""
        parts = [
            contact.get('phone'),
            contact.get('github'),
            contact.get('linkedin'),
            contact.get('email')
        ]
        # Filter out any empty strings and join with a standard separator.
        return ' | '.join(filter(None, parts))

    def _format_section(self, title: str, items: List[Dict], is_project: bool = False) -> List[str]:
        """A generic formatter for Experience and Projects sections."""
        lines = [f"## {title}\n"]
        for item in items:
            if is_project:
                header = f"**{item.get('name', '')}** | *{item.get('technologies', '')}*"
                description_points = item.get('description', [])
            else: # Work Experience
                header = f"**{item.get('title', '')}** | {item.get('company', '')} | {item.get('location', '')} | {item.get('dates', '')}"
                description_points = item.get('responsibilities', [])
            
            lines.append(header)
            for point in description_points:
                lines.append(f"- {point}")
            lines.append("")  # Add a blank line for readability between entries.
        return lines

    def _format_skills(self, skills: Dict) -> List[str]:
        """Formats the skills section from a dictionary."""
        lines = ["## Skills\n"]
        for category, skill_list in skills.items():
            if skill_list: # Only add category if it has skills
                lines.append(f"**{category}**: {', '.join(skill_list)}")
        return lines

    def run(self, user_profile: Dict, tailored_content: Dict) -> str:
        """
        Constructs the full resume in ATS-compliant Markdown.

        Args:
            user_profile: The user's data, needed for contact info.
            tailored_content: The LLM-generated tailored content.

        Returns:
            A string containing the complete resume in Markdown format.
        """
        resume_parts = []

        # 1. Name and Headline
        resume_parts.append(f"# {user_profile.get('name', 'User Name')}")
        if tailored_content.get('headline'):
            resume_parts.append(f"### {tailored_content['headline']}\n")
        
        # 2. Contact Information (must be in the main body)
        resume_parts.append(self._format_contact(user_profile.get('contact', {})) + "\n")
        
        # 3. Work Experience
        if tailored_content.get('tailored_experience'):
            resume_parts.extend(self._format_section("Work Experience", tailored_content['tailored_experience']))
            
        # 4. Projects
        if tailored_content.get('tailored_projects'):
            resume_parts.extend(self._format_section("Projects", tailored_content['tailored_projects'], is_project=True))

        # 5. Skills
        if tailored_content.get('tailored_skills'):
            resume_parts.extend(self._format_skills(tailored_content['tailored_skills']))

        # Join all parts into a single string with proper line breaks.
        return "\n".join(resume_parts).strip()