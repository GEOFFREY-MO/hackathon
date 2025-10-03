"""
AI Chat Agent for Retail Analytics
Provides intelligent insights and trend analysis for shop performance
"""

import openai
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os
from database import db, Shop, Sale, Product, Service, ServiceSale, Expense, FinancialRecord
from ocr_service import ocr_analyzer
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

logger = logging.getLogger(__name__)

class RetailAIAgent:
    """AI Agent for retail analytics and insights"""
    
    def __init__(self):
        # Initialize OpenAI (you'll need to set OPENAI_API_KEY in environment)
        # Attempt to load from .env at project root and backend/.env as a convenience
        try:
            # project root .env (two levels up from this file)
            project_root_env = Path(__file__).resolve().parents[1] / '.env'
            load_dotenv(dotenv_path=project_root_env)
        except Exception:
            pass
        try:
            # backend/.env (same directory as this module)
            backend_env = Path(__file__).resolve().parent / '.env'
            load_dotenv(dotenv_path=backend_env)
        except Exception:
            pass
        api_key = os.getenv('OPENAI_API_KEY')
        gemini_key = os.getenv('GEMINI_API_KEY')
        if api_key and api_key != 'sk-placeholder-key':
            self.client = openai.OpenAI(api_key=api_key)
            self.model = "gpt-4o-mini"
        elif gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                self.client = None
                # Dynamically select a supported Gemini model
                self.model = self._select_gemini_model() or "models/gemini-1.5-pro"
                logger.info(f"Gemini configured as AI backend. Using model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to configure Gemini: {e}")
                self.client = None
                self.model = "gpt-4o-mini"
        else:
            self.client = None
            self.model = "gpt-4o-mini"
            logger.warning("No AI key found; AI chat disabled until key is set.")
        self.conversation_history = []

    def _ensure_client(self) -> bool:
        """Attempt to (re)initialize OpenAI client from environment at runtime."""
        if self.client is not None or os.getenv('GEMINI_API_KEY'):
            # Ensure Gemini has a valid model name if it's the selected backend
            if self.client is None and 'gemini' in (self.model or '').lower():
                try:
                    selected = self._select_gemini_model()
                    if selected:
                        self.model = selected
                except Exception:
                    pass
            return True
        # Reload .env in case it was added after process start (both locations)
        try:
            project_root_env = Path(__file__).resolve().parents[1] / '.env'
            load_dotenv(dotenv_path=project_root_env)
        except Exception:
            pass
        try:
            backend_env = Path(__file__).resolve().parent / '.env'
            load_dotenv(dotenv_path=backend_env)
        except Exception:
            pass
        api_key = os.getenv('OPENAI_API_KEY')
        gemini_key = os.getenv('GEMINI_API_KEY')
        if api_key and api_key != 'sk-placeholder-key':
            try:
                self.client = openai.OpenAI(api_key=api_key)
                logger.info("OPENAI client initialized at runtime.")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
        if gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                # Ensure model is valid
                self.model = self._select_gemini_model() or self.model or "models/gemini-1.5-pro"
                logger.info(f"Gemini initialized at runtime. Using model: {self.model}")
                return True
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
        return False

    def _select_gemini_model(self) -> Optional[str]:
        """Pick a supported Gemini model for generateContent, preferring flash variants.

        Returns full model name (e.g., "models/gemini-1.5-flash"), or None if unavailable.
        """
        try:
            models = list(genai.list_models())
        except Exception as e:
            logger.error(f"Failed to list Gemini models: {e}")
            return None

        def supports_generate(m) -> bool:
            try:
                methods = getattr(m, 'supported_generation_methods', None)
                if not methods:
                    return False
                # Some SDK versions store methods as list of strings
                return any(str(x).lower() in ("generatecontent", "streamgeneratecontent") for x in methods)
            except Exception:
                return False

        # Prefer flash variants, then pro
        preferred_order = [
            'models/gemini-1.5-flash',
            'models/gemini-1.5-flash-001',
            'models/gemini-1.5-flash-latest',
            'models/gemini-1.5-flash-8b',
            'models/gemini-1.5-pro',
            'models/gemini-1.5-pro-001',
            'models/gemini-1.0-pro',
            'models/gemini-pro'
        ]

        name_to_model = {getattr(m, 'name', ''): m for m in models if supports_generate(m)}
        for name in preferred_order:
            if name in name_to_model:
                return name
        # Fallback to any generate-capable model
        for name in name_to_model.keys():
            return name
        return None
    
    def analyze_shop_performance(self, shop_id: int, time_period: str = "30d") -> Dict[str, Any]:
        """Analyze overall shop performance"""
        try:
            shop = Shop.query.get(shop_id)
            if not shop:
                return {"error": "Shop not found"}
            
            # Calculate time range
            end_date = datetime.utcnow()
            if time_period == "7d":
                start_date = end_date - timedelta(days=7)
            elif time_period == "30d":
                start_date = end_date - timedelta(days=30)
            elif time_period == "90d":
                start_date = end_date - timedelta(days=90)
            else:
                start_date = end_date - timedelta(days=30)
            
            # Get sales data
            sales = Sale.query.filter(
                Sale.shop_id == shop_id,
                Sale.sale_date >= start_date,
                Sale.sale_date <= end_date
            ).all()
            
            # Get service sales
            service_sales = ServiceSale.query.filter(
                ServiceSale.shop_id == shop_id,
                ServiceSale.sale_date >= start_date,
                ServiceSale.sale_date <= end_date
            ).all()
            
            # Get expenses
            expenses = Expense.query.filter(
                Expense.shop_id == shop_id,
                Expense.date >= start_date,
                Expense.date <= end_date
            ).all()
            
            # Calculate metrics
            total_sales_revenue = sum(float(sale.total or 0) for sale in sales)
            total_service_revenue = sum(float(sale.price or 0) for sale in service_sales)
            total_revenue = float(total_sales_revenue + total_service_revenue)
            total_expenses = sum(float(expense.amount or 0) for expense in expenses)
            net_profit = total_revenue - total_expenses
            
            # Product performance
            product_sales = {}
            for sale in sales:
                product_name = sale.product.name if sale.product else "Unknown"
                if product_name not in product_sales:
                    product_sales[product_name] = {'quantity': 0, 'revenue': 0}
                product_sales[product_name]['quantity'] += sale.quantity
                product_sales[product_name]['revenue'] += sale.total
            
            # Top performing products
            top_products = sorted(product_sales.items(), 
                                key=lambda x: x[1]['revenue'], reverse=True)[:5]
            
            analysis = {
                'shop_name': shop.name,
                'time_period': time_period,
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'net_profit': net_profit,
                'profit_margin': (net_profit / total_revenue * 100) if total_revenue > 0 else 0,
                'total_sales_count': len(sales) + len(service_sales),
                'top_products': top_products,
                'sales_trend': self._calculate_sales_trend(sales, time_period),
                'revenue_by_day': self._get_revenue_by_day(sales, service_sales, start_date, end_date)
            }
            
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing shop performance: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_sales_trend(self, sales: List, time_period: str) -> str:
        """Calculate sales trend direction"""
        if len(sales) < 2:
            return "insufficient_data"
        
        # Group sales by week
        weekly_sales = {}
        for sale in sales:
            week = sale.sale_date.isocalendar()[1]
            if week not in weekly_sales:
                weekly_sales[week] = 0
                weekly_sales[week] += float(sale.total or 0)
        
        if len(weekly_sales) < 2:
            return "insufficient_data"
        
        # Calculate trend
        weeks = sorted(weekly_sales.keys())
        first_week_sales = weekly_sales[weeks[0]]
        last_week_sales = weekly_sales[weeks[-1]]
        
        if last_week_sales > first_week_sales * 1.1:
            return "increasing"
        elif last_week_sales < first_week_sales * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    def _get_revenue_by_day(self, sales: List, service_sales: List, start_date: datetime, end_date: datetime) -> Dict:
        """Get daily revenue breakdown"""
        daily_revenue = {}
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            daily_revenue[date_str] = 0
            current_date += timedelta(days=1)
        
        # Add sales revenue
        for sale in sales:
            date_str = sale.sale_date.strftime('%Y-%m-%d')
            if date_str in daily_revenue:
                daily_revenue[date_str] += float(sale.total or 0)
        
        # Add service revenue
        for sale in service_sales:
            date_str = sale.sale_date.strftime('%Y-%m-%d')
            if date_str in daily_revenue:
                daily_revenue[date_str] += float(sale.price or 0)
        
        return daily_revenue
    
    def generate_insights(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate AI-powered insights from performance analysis"""
        try:
            if "error" in analysis:
                return [f"Error: {analysis['error']}"]
            
            insights = []
            
            # Revenue insights
            total_revenue = analysis.get('total_revenue', 0)
            net_profit = analysis.get('net_profit', 0)
            profit_margin = analysis.get('profit_margin', 0)
            
            if total_revenue > 0:
                insights.append(f"💰 Total Revenue: ${total_revenue:,.2f}")
                insights.append(f"📈 Net Profit: ${net_profit:,.2f}")
                insights.append(f"📊 Profit Margin: {profit_margin:.1f}%")
            
            # Trend insights
            sales_trend = analysis.get('sales_trend', 'unknown')
            if sales_trend == 'increasing':
                insights.append("🚀 Sales are trending upward - great performance!")
            elif sales_trend == 'decreasing':
                insights.append("⚠️ Sales are declining - consider promotional strategies")
            elif sales_trend == 'stable':
                insights.append("📊 Sales are stable - maintain current strategies")
            
            # Top products insights
            top_products = analysis.get('top_products', [])
            if top_products:
                best_product = top_products[0]
                insights.append(f"🏆 Top Product: {best_product[0]} (${best_product[1]['revenue']:,.2f})")
            
            # Profit margin insights
            if profit_margin > 20:
                insights.append("✅ Excellent profit margin - business is very healthy")
            elif profit_margin > 10:
                insights.append("👍 Good profit margin - business is performing well")
            elif profit_margin > 0:
                insights.append("⚠️ Low profit margin - consider cost optimization")
            else:
                insights.append("🚨 Negative profit margin - immediate action needed")
            
            return insights
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return [f"Error generating insights: {str(e)}"]
    
    def chat_with_agent(self, message: str, shop_id: int, context: Dict = None) -> str:
        """Chat with AI agent for retail insights"""
        try:
            # Ensure OpenAI client is available (lazy init)
            if not self.client and not self._ensure_client():
                return "AI features are not available. Please set OPENAI_API_KEY and retry."
            
            # Get current shop performance data
            performance_data = self.analyze_shop_performance(shop_id)
            insights = self.generate_insights(performance_data)
            
            # Prepare context for AI
            context_data = {
                "shop_performance": performance_data,
                "insights": insights,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Create system prompt
            system_prompt = f"""
            You are an AI retail analytics assistant for SmartRetail AI. 
            You help shop administrators understand their business performance through data analysis and insights.
            
            Current Shop Performance Data:
            {json.dumps(context_data, indent=2)}
            
            Provide helpful, actionable insights based on the data. Be conversational but professional.
            Focus on:
            - Revenue and profit analysis
            - Sales trends and patterns
            - Product performance
            - Recommendations for improvement
            - Answer specific questions about the data
            """
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Call the selected AI backend
            if self.client is not None:
                # OpenAI
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                ai_response = response.choices[0].message.content
            else:
                # Gemini
                model = genai.GenerativeModel(self.model)
                resp = model.generate_content([
                    {"text": system_prompt},
                    {"text": message}
                ])
                ai_response = resp.text or ""
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return ai_response
            
        except Exception as e:
            err_text = str(e)
            logger.error(f"Error in chat with agent: {err_text}")
            # Graceful fallback if quota exceeded or API unavailable
            if 'insufficient_quota' in err_text or 'You exceeded your current quota' in err_text or '429' in err_text:
                # Try Gemini as secondary if available
                try:
                    gemini_key = os.getenv('GEMINI_API_KEY')
                    if gemini_key:
                        genai.configure(api_key=gemini_key)
                        selected = self._select_gemini_model() or 'models/gemini-1.5-pro'
                        model = genai.GenerativeModel(selected)
                        resp = model.generate_content([
                            {"text": system_prompt},
                            {"text": message}
                        ])
                        ai_text = (resp.text or '').strip()
                        if ai_text:
                            return ai_text
                except Exception as ge:
                    logger.error(f"Gemini fallback failed: {ge}")
                try:
                    fallback = self.analyze_shop_performance(shop_id)
                    insights = self.generate_insights(fallback)
                    summary_lines = [
                        "AI cloud service is unavailable (quota/keys). Showing local insights instead:",
                    ]
                    if 'total_revenue' in fallback:
                        summary_lines.append(f"- Total Revenue: ${fallback.get('total_revenue', 0):,.2f}")
                    if 'net_profit' in fallback:
                        summary_lines.append(f"- Net Profit: ${fallback.get('net_profit', 0):,.2f}")
                    if 'profit_margin' in fallback:
                        summary_lines.append(f"- Profit Margin: {fallback.get('profit_margin', 0):.1f}%")
                    if fallback.get('sales_trend'):
                        summary_lines.append(f"- Sales Trend: {fallback['sales_trend']}")
                    if fallback.get('top_products'):
                        tp = fallback['top_products'][0]
                        summary_lines.append(f"- Top Product: {tp[0]} (${tp[1]['revenue']:,.2f})")
                    if insights:
                        summary_lines.append("- Insights:")
                        for s in insights[:5]:
                            summary_lines.append(f"  • {s}")
                    summary_lines.append("Set a valid OPENAI_API_KEY or GEMINI_API_KEY to re-enable full AI chat.")
                    return "\n".join(summary_lines)
                except Exception as _:
                    return "AI cloud service quota exceeded and local fallback failed. Please check API billing or try again later."
            return f"I apologize, but I encountered an error: {err_text}. Please try again."
    
    def analyze_uploaded_chart(self, image_path: str, shop_id: int) -> Dict[str, Any]:
        """Analyze uploaded chart/graph image"""
        try:
            # Extract data using OCR
            chart_data = ocr_analyzer.extract_chart_data(image_path)
            performance_analysis = ocr_analyzer.analyze_performance_metrics(chart_data)
            insights = ocr_analyzer.generate_insights(chart_data, performance_analysis)
            
            # Get AI interpretation
            chart_summary = f"""
            Chart Analysis Results:
            - Chart Type: {chart_data.get('chart_type', 'Unknown')}
            - Title: {chart_data.get('title', 'No title detected')}
            - Data Points: {len(chart_data.get('data_points', []))}
            - Trends: {', '.join(chart_data.get('trends', []))}
            - Performance Metrics: {performance_analysis}
            - Insights: {insights}
            """
            
            ai_interpretation = self.chat_with_agent(
                f"Please analyze this chart data and provide business insights: {chart_summary}",
                shop_id
            )
            
            return {
                'chart_data': chart_data,
                'performance_analysis': performance_analysis,
                'insights': insights,
                'ai_interpretation': ai_interpretation,
                'chart_type': chart_data.get('chart_type', 'unknown'),
                'title': chart_data.get('title', ''),
                'raw_text': chart_data.get('raw_text', '')
            }
            
        except Exception as e:
            logger.error(f"Error analyzing uploaded chart: {str(e)}")
            return {"error": str(e)}
    
    def generate_visualization(self, shop_id: int, chart_type: str = "revenue_trend") -> str:
        """Generate visualization for shop data"""
        try:
            analysis = self.analyze_shop_performance(shop_id)
            
            if chart_type == "revenue_trend":
                # Create revenue trend chart
                revenue_data = analysis.get('revenue_by_day', {})
                dates = list(revenue_data.keys())
                values = list(revenue_data.values())
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=values,
                    mode='lines+markers',
                    name='Daily Revenue',
                    line=dict(color='#2F80ED', width=3)
                ))
                
                fig.update_layout(
                    title=f"Revenue Trend - {analysis.get('shop_name', 'Shop')}",
                    xaxis_title="Date",
                    yaxis_title="Revenue ($)",
                    template="plotly_white",
                    font=dict(family="Poppins, sans-serif")
                )
                
            elif chart_type == "product_performance":
                # Create product performance chart
                top_products = analysis.get('top_products', [])
                if not top_products:
                    return json.dumps({"error": "No product data available"})
                
                products = [item[0] for item in top_products]
                revenues = [item[1]['revenue'] for item in top_products]
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=products,
                    y=revenues,
                    name='Product Revenue',
                    marker_color='#56CC9D'
                ))
                
                fig.update_layout(
                    title=f"Top Products Performance - {analysis.get('shop_name', 'Shop')}",
                    xaxis_title="Products",
                    yaxis_title="Revenue ($)",
                    template="plotly_white",
                    font=dict(family="Poppins, sans-serif")
                )
            
            # Convert to JSON
            chart_json = json.dumps(fig, cls=PlotlyJSONEncoder)
            return chart_json
            
        except Exception as e:
            logger.error(f"Error generating visualization: {str(e)}")
            return json.dumps({"error": str(e)})
    
    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history[-10:]  # Return last 10 messages
    
    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []

# Global instance
ai_agent = RetailAIAgent()
