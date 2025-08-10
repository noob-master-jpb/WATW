"""
AI Summarizer for WATW
Handles AI-powered document summarization using OpenAI GPT-4 or Claude
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    import openai
except ImportError:
    print("⚠️ OpenAI library not installed. Run: pip install openai")

try:
    import anthropic
except ImportError:
    print("⚠️ Anthropic library not installed. Run: pip install anthropic")

class AISummarizer:
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.setup_clients()
    
    def setup_clients(self):
        """Initialize AI clients based on available API keys"""
        
        # OpenAI setup
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            try:
                import openai
                self.openai_client = openai.OpenAI(api_key=openai_key)
                print("✅ OpenAI client initialized")
            except Exception as e:
                print(f"⚠️ OpenAI setup failed: {e}")
        
        # Anthropic setup
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                print("✅ Anthropic client initialized")
            except Exception as e:
                print(f"⚠️ Anthropic setup failed: {e}")
    
    def summarize_folder(self, folder_contents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize all files in a folder"""
        
        if not folder_contents:
            return {'error': 'No files to summarize'}
        
        # Prepare content for AI
        folder_summary = {
            'total_files': len(folder_contents),
            'files': [],
            'summary': ''
        }
        
        # Process each file
        for file_info in folder_contents:
            if file_info.get('content'):
                file_summary = self.summarize_single_file(
                    file_info['content'], 
                    file_info['file_path']
                )
                folder_summary['files'].append({
                    'path': file_info['file_path'],
                    'type': file_info.get('type', 'unknown'),
                    'summary': file_summary.get('summary', 'No summary available')
                })
        
        # Generate overall folder summary
        if folder_summary['files']:
            combined_content = '\n\n'.join([
                f"File: {f['path']}\nSummary: {f['summary']}" 
                for f in folder_summary['files']
            ])
            
            overall_summary = self._generate_summary(
                combined_content,
                f"Folder containing {len(folder_summary['files'])} files"
            )
            
            folder_summary['summary'] = overall_summary.get('summary', 'Unable to generate folder summary')
        
        return folder_summary
    
    def summarize_single_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Summarize a single file's content"""
        
        if not content or len(content.strip()) < 10:
            return {'error': 'Content too short to summarize'}
        
        # Truncate content if too long (to fit within token limits)
        max_content_length = 8000  # Conservative limit
        if len(content) > max_content_length:
            content = content[:max_content_length] + "... [truncated]"
        
        return self._generate_summary(content, file_path)
    
    def _generate_summary(self, content: str, context: str) -> Dict[str, Any]:
        """Generate summary using available AI service"""
        
        # Try OpenAI first
        if self.openai_client:
            try:
                return self._openai_summary(content, context)
            except Exception as e:
                print(f"OpenAI failed: {e}")
        
        # Try Anthropic as fallback
        if self.anthropic_client:
            try:
                return self._anthropic_summary(content, context)
            except Exception as e:
                print(f"Anthropic failed: {e}")
        
        # Fallback to basic summary
        return self._basic_summary(content, context)
    
    def _openai_summary(self, content: str, context: str) -> Dict[str, Any]:
        """Generate summary using OpenAI GPT-4"""
        
        prompt = f"""Please provide a concise bullet-point summary of the following document content.

Context: {context}

Content:
{content}

Please format your response as:
• Key point 1
• Key point 2  
• Key point 3
(etc.)

Focus on the main themes, important decisions, action items, and key findings."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use mini for cost efficiency
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates concise, bullet-point summaries of documents."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content
            
            return {
                'success': True,
                'summary': summary,
                'service': 'OpenAI GPT-4',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'OpenAI API error: {e}'}
    
    def _anthropic_summary(self, content: str, context: str) -> Dict[str, Any]:
        """Generate summary using Anthropic Claude"""
        
        prompt = f"""Please provide a concise bullet-point summary of the following document content.

Context: {context}

Content:
{content}

Please format your response as:
• Key point 1
• Key point 2  
• Key point 3
(etc.)

Focus on the main themes, important decisions, action items, and key findings."""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",  # Use Haiku for cost efficiency
                max_tokens=300,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            summary = response.content[0].text
            
            return {
                'success': True,
                'summary': summary,
                'service': 'Anthropic Claude',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'Anthropic API error: {e}'}
    
    def _basic_summary(self, content: str, context: str) -> Dict[str, Any]:
        """Generate basic summary when AI services are unavailable"""
        
        # Simple extractive summary
        lines = content.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        # Take first few lines and some middle content
        summary_lines = []
        
        if len(non_empty_lines) > 0:
            summary_lines.append(f"• Document contains {len(non_empty_lines)} lines of text")
        
        if len(non_empty_lines) > 2:
            summary_lines.append(f"• Starts with: {non_empty_lines[0][:100]}...")
        
        if len(non_empty_lines) > 10:
            middle_line = non_empty_lines[len(non_empty_lines)//2]
            summary_lines.append(f"• Contains: {middle_line[:100]}...")
        
        # Word count
        word_count = len(content.split())
        summary_lines.append(f"• Total word count: approximately {word_count} words")
        
        # Character analysis
        if '.' in content:
            sentence_count = content.count('.')
            summary_lines.append(f"• Estimated {sentence_count} sentences")
        
        summary = '\n'.join(summary_lines)
        
        return {
            'success': True,
            'summary': summary,
            'service': 'Basic Text Analysis',
            'note': 'AI services unavailable - using basic text analysis',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_available_services(self) -> List[str]:
        """Get list of available AI services"""
        services = []
        
        if self.openai_client:
            services.append('OpenAI GPT-4')
        
        if self.anthropic_client:
            services.append('Anthropic Claude')
        
        services.append('Basic Text Analysis')  # Always available
        
        return services

def test_ai_summarizer():
    """Test AI summarization functionality"""
    
    summarizer = AISummarizer()
    
    print("🤖 Testing AI Summarizer...")
    print(f"Available services: {summarizer.get_available_services()}")
    
    # Test content
    test_content = """
    Project Status Report - Q4 2024
    
    Executive Summary:
    The project is currently 85% complete and on track for delivery in Q1 2025.
    Budget utilization stands at 78% of allocated resources.
    
    Key Achievements:
    - Completed user interface design and development
    - Integrated payment gateway successfully
    - Conducted security testing with zero critical vulnerabilities
    - User acceptance testing achieved 92% satisfaction rate
    
    Challenges:
    - Minor delays in third-party API integration
    - Need additional testing for mobile responsiveness
    
    Next Steps:
    - Complete mobile optimization by December 15
    - Final security review scheduled for December 20
    - Production deployment planned for January 10, 2025
    """
    
    result = summarizer.summarize_single_file(test_content, "test_report.txt")
    print(f"Summary result: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    test_ai_summarizer()
