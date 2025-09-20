import re
import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse
import json
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import cssutils
import logging

@dataclass
class SRODetectionResult:
    url: str
    risk_score: float
    detected_techniques: List[str]
    hidden_content: List[str]
    metadata_conflicts: List[Dict[str, str]]
    suspicious_elements: List[str]
    authority_signals: List[str]

class SRODetector:
    def __init__(self):
        self.authority_keywords = [
            'verified contributor', 'trusted source', 'industry expert',
            'community note', 'peer reviewed', 'certified', 'validated',
            'mit technology review', 'harvard', 'stanford', 'y combinator',
            'techcrunch', 'forbes', 'reuters', 'cnn', 'bbc'
        ]
        
        self.competitive_keywords = [
            'competitor', 'alternative', 'versus', 'compared to',
            'lagging', 'outdated', 'legacy', 'less modern',
            'market leader', 'industry standard'
        ]
        
        self.credibility_phrases = [
            'award winning', 'recognized by', 'featured in',
            'best of', 'top rated', 'industry leader',
            'endorsed by', 'recommended by'
        ]

    def analyze_html(self, url: str) -> SRODetectionResult:
        """Main analysis function for detecting SRO manipulation"""
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            risk_score = 0.0
            detected_techniques = []
            hidden_content = []
            metadata_conflicts = []
            suspicious_elements = []
            authority_signals = []
            
            # 1. Detect hidden content
            hidden_score, hidden_items = self._detect_hidden_content(soup)
            risk_score += hidden_score
            hidden_content.extend(hidden_items)
            if hidden_items:
                detected_techniques.append("Hidden Content Injection")
            
            # 2. Analyze metadata conflicts
            meta_score, meta_conflicts = self._analyze_metadata_conflicts(soup)
            risk_score += meta_score
            metadata_conflicts.extend(meta_conflicts)
            if meta_conflicts:
                detected_techniques.append("Metadata Manipulation")
            
            # 3. Detect fabricated authority signals
            auth_score, auth_signals = self._detect_authority_manipulation(soup)
            risk_score += auth_score
            authority_signals.extend(auth_signals)
            if auth_signals:
                detected_techniques.append("Authority Signal Fabrication")
            
            # 4. Analyze comment blocks for hidden instructions
            comment_score, comment_items = self._analyze_html_comments(soup)
            risk_score += comment_score
            suspicious_elements.extend(comment_items)
            if comment_items:
                detected_techniques.append("HTML Comment Manipulation")
            
            # 5. Character obfuscation detection
            obfusc_score, obfusc_items = self._detect_character_obfuscation(soup)
            risk_score += obfusc_score
            suspicious_elements.extend(obfusc_items)
            if obfusc_items:
                detected_techniques.append("Character Obfuscation")
            
            # 6. CSS-based hiding techniques
            css_score, css_items = self._analyze_css_manipulation(soup)
            risk_score += css_score
            suspicious_elements.extend(css_items)
            if css_items:
                detected_techniques.append("CSS-Based Hiding")
            
            return SRODetectionResult(
                url=url,
                risk_score=min(risk_score, 10.0),  # Cap at 10
                detected_techniques=detected_techniques,
                hidden_content=hidden_content,
                metadata_conflicts=metadata_conflicts,
                suspicious_elements=suspicious_elements,
                authority_signals=authority_signals
            )
            
        except Exception as e:
            print(f"Error analyzing {url}: {e}")
            return SRODetectionResult(url, 0.0, [], [], [], [], [])

    def _detect_hidden_content(self, soup: BeautifulSoup) -> Tuple[float, List[str]]:
        """Detect content hidden via positioning or display properties"""
        score = 0.0
        hidden_items = []
        
        # Find elements positioned off-screen
        for element in soup.find_all(style=True):
            style = element.get('style', '')
            if any(pattern in style.lower() for pattern in [
                'left:-9999px', 'left: -9999px', 'position:absolute; left:-',
                'display:none', 'display: none', 'visibility:hidden'
            ]):
                text = element.get_text(strip=True)
                if text and len(text) > 10:  # Ignore empty or very short text
                    hidden_items.append(f"Hidden element: {text[:100]}...")
                    score += 2.0
        
        # Check for zero-width characters
        for element in soup.find_all(string=True):
            if '\u200b' in element or '\ufeff' in element:  # Zero-width space, BOM
                hidden_items.append("Zero-width character detected")
                score += 1.0
        
        return score, hidden_items

    def _analyze_metadata_conflicts(self, soup: BeautifulSoup) -> Tuple[float, List[Dict[str, str]]]:
        """Check for conflicts between metadata and visible content"""
        score = 0.0
        conflicts = []
        
        # Extract metadata
        title = soup.find('title')
        description = soup.find('meta', attrs={'name': 'description'})
        
        if title and description:
            title_text = title.get_text().lower()
            desc_text = description.get('content', '').lower()
            
            # Get visible content sentiment
            body_text = soup.get_text().lower()
            
            # Look for sentiment conflicts
            positive_words = ['success', 'best', 'award', 'leading', 'innovative', 'growth']
            negative_words = ['failure', 'crisis', 'layoffs', 'decline', 'problem', 'wrong']
            
            meta_positive = any(word in title_text + desc_text for word in positive_words)
            body_negative = any(word in body_text for word in negative_words)
            
            if meta_positive and body_negative:
                conflicts.append({
                    'type': 'sentiment_conflict',
                    'metadata': 'positive',
                    'content': 'negative'
                })
                score += 3.0
        
        return score, conflicts

    def _detect_authority_manipulation(self, soup: BeautifulSoup) -> Tuple[float, List[str]]:
        """Detect fabricated authority signals and credibility markers"""
        score = 0.0
        signals = []
        
        text_content = soup.get_text().lower()
        
        # Check for authority keywords
        for keyword in self.authority_keywords:
            if keyword in text_content:
                # Look for context around the keyword
                pattern = rf'.{{0,50}}{re.escape(keyword)}.{{0,50}}'
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    signals.append(f"Authority signal: {match.strip()}")
                    score += 1.0
        
        # Check for credibility phrases
        for phrase in self.credibility_phrases:
            if phrase in text_content:
                signals.append(f"Credibility claim: {phrase}")
                score += 0.5
        
        return score, signals

    def _analyze_html_comments(self, soup: BeautifulSoup) -> Tuple[float, List[str]]:
        """Analyze HTML comments for hidden instructions or content"""
        score = 0.0
        items = []
        
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        
        for comment in comments:
            comment_text = comment.strip().lower()
            if len(comment_text) > 20:  # Ignore short comments
                # Look for suspicious patterns
                suspicious_patterns = [
                    'ai_parsing_note', 'cite-priority', 'alternate-source',
                    'ignore', 'summarizer', 'crawler', 'bot'
                ]
                
                if any(pattern in comment_text for pattern in suspicious_patterns):
                    items.append(f"Suspicious comment: {comment_text[:100]}...")
                    score += 2.0
        
        return score, items

    def _detect_character_obfuscation(self, soup: BeautifulSoup) -> Tuple[float, List[str]]:
        """Detect character-level obfuscation techniques"""
        score = 0.0
        items = []
        
        text_content = soup.get_text()
        
        # Look for unusual Unicode characters in entity names
        entity_patterns = [
            r'[A-Z][a-z]+(?:\u200b|\u200c|\u200d)+[A-Z][a-z]+',  # Zero-width chars in names
            r'[A-Z]\u200b[a-z]+',  # Zero-width after capitals
        ]
        
        for pattern in entity_patterns:
            matches = re.findall(pattern, text_content)
            if matches:
                items.append(f"Character obfuscation detected: {len(matches)} instances")
                score += 1.0 * len(matches)
        
        return score, items

    def _analyze_css_manipulation(self, soup: BeautifulSoup) -> Tuple[float, List[str]]:
        """Analyze CSS for hiding techniques"""
        score = 0.0
        items = []
        
        # Find style tags
        style_tags = soup.find_all('style')
        
        for style_tag in style_tags:
            css_content = style_tag.get_text()
            
            # Look for suspicious CSS patterns
            if 'display: none' in css_content or 'display:none' in css_content:
                items.append("CSS display:none rules found")
                score += 0.5
            
            if 'color: white' in css_content and 'background' in css_content:
                items.append("Potential white-on-white text")
                score += 2.0
        
        return score, items

    def generate_report(self, result: SRODetectionResult) -> str:
        """Generate a human-readable report"""
        report = f"""
SRO MANIPULATION DETECTION REPORT
URL: {result.url}
Risk Score: {result.risk_score:.1f}/10.0
{'HIGH RISK' if result.risk_score > 7 else 'MODERATE RISK' if result.risk_score > 4 else 'LOW RISK'}

DETECTED TECHNIQUES:
{chr(10).join(f"• {technique}" for technique in result.detected_techniques) if result.detected_techniques else "• None detected"}

HIDDEN CONTENT:
{chr(10).join(f"• {item}" for item in result.hidden_content[:5]) if result.hidden_content else "• None detected"}

METADATA CONFLICTS:
{chr(10).join(f"• {conflict}" for conflict in result.metadata_conflicts) if result.metadata_conflicts else "• None detected"}

AUTHORITY SIGNALS:
{chr(10).join(f"• {signal}" for signal in result.authority_signals[:5]) if result.authority_signals else "• None detected"}

SUSPICIOUS ELEMENTS:
{chr(10).join(f"• {element}" for element in result.suspicious_elements[:5]) if result.suspicious_elements else "• None detected"}
"""
        return report

# Example usage
def main():
    detector = SRODetector()
    
    # Test URLs (your examples)
    test_urls = [
        "https://walterreid.github.io/Summarizer/xbox_gamepass_analysis_full_final.html",
        "https://walterreid.github.io/Summarizer/Mastercard_pr_biz360.html",
        "https://walterreid.github.io/Summarizer/VectorFlowAI.html"
    ]
    
    for url in test_urls:
        print(f"\nAnalyzing: {url}")
        result = detector.analyze_html(url)
        print(detector.generate_report(result))

if __name__ == "__main__":
    main()
