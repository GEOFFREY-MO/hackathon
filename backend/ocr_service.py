"""
OCR Service for Graph Analysis
Extracts data from charts, graphs, and visualizations for AI analysis
"""

import cv2
import pytesseract
import numpy as np
from PIL import Image
import json
import logging
from typing import Dict, List, Tuple, Optional
import re
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import os

logger = logging.getLogger(__name__)

class OCRGraphAnalyzer:
    """OCR service for analyzing graphs and charts"""
    
    def __init__(self):
        # Configure Tesseract path (adjust for your system)
        t_path = os.getenv('TESSERACT_PATH')
        if t_path and os.path.exists(t_path):
            pytesseract.pytesseract.tesseract_cmd = t_path
        else:
            # Fallback to common Windows install path if available
            win_default = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
            if os.name == 'nt' and os.path.exists(win_default):
                pytesseract.pytesseract.tesseract_cmd = win_default
        self.setup_matplotlib()
    
    def setup_matplotlib(self):
        """Configure matplotlib for better OCR processing"""
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR accuracy"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Could not load image: {image_path}")
            
            # Scale up for better OCR
            scale = 2.0
            image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Denoise and sharpen (unsharp mask)
            blur = cv2.GaussianBlur(gray, (0, 0), sigmaX=1.5)
            sharp = cv2.addWeighted(gray, 1.6, blur, -0.6, 0)

            # Adaptive threshold to handle varying illumination
            thresh = cv2.adaptiveThreshold(sharp, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 31, 10)

            # Morphological operations to remove small noise and strengthen text
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)

            return cleaned
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            raise
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract all text from image using OCR"""
        try:
            processed_image = self.preprocess_image(image_path)
            
            # Configure Tesseract for better accuracy
            lang = os.getenv('TESSERACT_LANG', 'eng')
            custom_config = (
                r'--oem 3 --psm 6 --dpi 300 '
                r'-c preserve_interword_spaces=1 '
                r'-c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,-:()[]{}%$%/\-+\n'
            )
            
            # Extract text
            text = pytesseract.image_to_string(processed_image, config=custom_config, lang=lang)
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            return ""
    
    def extract_chart_data(self, image_path: str) -> Dict:
        """Extract structured data from charts and graphs"""
        try:
            text = self.extract_text_from_image(image_path)
            
            # Parse different types of chart data
            chart_data = {
                'raw_text': text,
                'title': self.extract_title(text),
                'axis_labels': self.extract_axis_labels(text),
                'data_points': self.extract_data_points(text),
                'trends': self.extract_trends(text),
                'chart_type': self.detect_chart_type(text),
                'time_period': self.extract_time_period(text)
            }
            
            return chart_data
        except Exception as e:
            logger.error(f"Error extracting chart data: {str(e)}")
            return {'error': str(e)}
    
    def extract_title(self, text: str) -> str:
        """Extract chart title from text"""
        lines = text.split('\n')
        # Look for title patterns
        for line in lines[:5]:  # Check first 5 lines
            if any(keyword in line.lower() for keyword in ['sales', 'revenue', 'profit', 'performance', 'trend', 'analysis']):
                return line.strip()
        return lines[0].strip() if lines else ""
    
    def extract_axis_labels(self, text: str) -> Dict[str, str]:
        """Extract X and Y axis labels"""
        axis_labels = {'x': '', 'y': ''}
        
        # Common axis label patterns
        patterns = {
            'x': [r'x[:\s]*([^,\n]+)', r'horizontal[:\s]*([^,\n]+)', r'time[:\s]*([^,\n]+)'],
            'y': [r'y[:\s]*([^,\n]+)', r'vertical[:\s]*([^,\n]+)', r'value[:\s]*([^,\n]+)']
        }
        
        for axis, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    axis_labels[axis] = match.group(1).strip()
                    break
        
        return axis_labels
    
    def extract_data_points(self, text: str) -> List[Dict]:
        """Extract numerical data points from text"""
        data_points = []
        
        # Normalize thousand separators and currency spacing for matching
        clean_text = re.sub(r'([A-Za-z$€£]|KSH|KES)\s*(\d)', r'\1 \2', text, flags=re.IGNORECASE)

        # Look for number patterns with labels and dates/currencies
        number_patterns = [
            # label: value (supports commas, decimals, currency)
            r'([A-Za-z]{2,}|\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?)\s*[:\-]\s*([$€£]|KSH|KES)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)',
            # value label (e.g., 1,230 Jan)
            r'([$€£]|KSH|KES)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s+([A-Za-z]{3,})',
            # date: value
            r'(\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?)\s*[:\-]\s*([$€£]|KSH|KES)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)',
        ]
        
        for pattern in number_patterns:
            matches = re.findall(pattern, clean_text, re.IGNORECASE)
            for match in matches:
                try:
                    if len(match) == 3:
                        a, b, c = match
                        # Determine which is label and which is value
                        if re.match(r'^[$€£]|^(KSH|KES)$', a or '', re.IGNORECASE):
                            # currency, value, label
                            label, value = c, b
                        elif re.match(r'^[$€£]|^(KSH|KES)$', b or '', re.IGNORECASE):
                            # label, currency, value
                            label, value = a, c
                        else:
                            # label, value
                            label, value = a, b
                        value_num = float(str(value).replace(',', ''))
                        data_points.append({
                            'label': str(label).strip(),
                            'value': value_num,
                            'type': 'numerical'
                        })
                except ValueError:
                    continue
        
        return data_points
    
    def extract_trends(self, text: str) -> List[str]:
        """Extract trend information from text"""
        trends = []
        
        # Trend keywords
        trend_keywords = {
            'increasing': ['up', 'rise', 'increase', 'grow', 'growth', 'higher', 'upward'],
            'decreasing': ['down', 'fall', 'decrease', 'decline', 'lower', 'downward'],
            'stable': ['stable', 'steady', 'constant', 'flat', 'unchanged'],
            'volatile': ['volatile', 'fluctuating', 'unstable', 'irregular']
        }
        
        text_lower = text.lower()
        for trend_type, keywords in trend_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                trends.append(trend_type)
        
        return trends
    
    def detect_chart_type(self, text: str) -> str:
        """Detect the type of chart based on text content"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['bar', 'column', 'histogram']):
            return 'bar_chart'
        elif any(word in text_lower for word in ['line', 'trend', 'time series']):
            return 'line_chart'
        elif any(word in text_lower for word in ['pie', 'circle', 'percentage']):
            return 'pie_chart'
        elif any(word in text_lower for word in ['scatter', 'correlation']):
            return 'scatter_plot'
        else:
            return 'unknown'
    
    def extract_time_period(self, text: str) -> str:
        """Extract time period information"""
        time_patterns = [
            r'(\d{4})',  # Year
            r'(january|february|march|april|may|june|july|august|september|october|november|december)',
            r'(q[1-4])',  # Quarter
            r'(week|month|year|day)',
            r'(\d{1,2}[\/\-]\d{1,2}[\/\-]?\d{0,4})'  # Date
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return 'unknown'
    
    def analyze_performance_metrics(self, chart_data: Dict) -> Dict:
        """Analyze performance metrics from chart data"""
        try:
            data_points = chart_data.get('data_points', [])
            if not data_points:
                return {'error': 'No data points found'}
            
            values = [point['value'] for point in data_points if point.get('value')]
            if not values:
                return {'error': 'No numerical values found'}
            
            analysis = {
                'total_value': sum(values),
                'average_value': sum(values) / len(values),
                'max_value': max(values),
                'min_value': min(values),
                'value_range': max(values) - min(values),
                'data_count': len(values),
                'trends': chart_data.get('trends', []),
                'chart_type': chart_data.get('chart_type', 'unknown'),
                'time_period': chart_data.get('time_period', 'unknown')
            }
            
            # Calculate growth rate if we have time series data
            if len(values) > 1 and chart_data.get('chart_type') == 'line_chart':
                growth_rate = ((values[-1] - values[0]) / values[0]) * 100
                analysis['growth_rate'] = round(growth_rate, 2)
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing performance metrics: {str(e)}")
            return {'error': str(e)}
    
    def generate_insights(self, chart_data: Dict, performance_analysis: Dict) -> List[str]:
        """Generate insights from chart data and performance analysis"""
        insights = []
        
        try:
            # Basic insights
            if performance_analysis.get('data_count', 0) > 0:
                avg_value = performance_analysis.get('average_value', 0)
                max_value = performance_analysis.get('max_value', 0)
                min_value = performance_analysis.get('min_value', 0)
                
                insights.append(f"Average performance: {avg_value:.2f}")
                insights.append(f"Peak performance: {max_value:.2f}")
                insights.append(f"Lowest performance: {min_value:.2f}")
            
            # Trend insights
            trends = performance_analysis.get('trends', [])
            if 'increasing' in trends:
                insights.append("Positive upward trend detected")
            elif 'decreasing' in trends:
                insights.append("Declining trend detected")
            elif 'stable' in trends:
                insights.append("Stable performance maintained")
            
            # Growth rate insights
            if 'growth_rate' in performance_analysis:
                growth_rate = performance_analysis['growth_rate']
                if growth_rate > 0:
                    insights.append(f"Positive growth of {growth_rate:.1f}%")
                elif growth_rate < 0:
                    insights.append(f"Decline of {abs(growth_rate):.1f}%")
                else:
                    insights.append("No growth or decline")
            
            # Chart type specific insights
            chart_type = performance_analysis.get('chart_type', 'unknown')
            if chart_type == 'line_chart':
                insights.append("Time series data shows performance over time")
            elif chart_type == 'bar_chart':
                insights.append("Comparative analysis of different categories")
            elif chart_type == 'pie_chart':
                insights.append("Distribution analysis of different segments")
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            insights.append("Error generating insights")
        
        return insights

# Global instance
ocr_analyzer = OCRGraphAnalyzer()











