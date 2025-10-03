# AI Features for SmartRetail AI

This document describes the new AI-powered features added to SmartRetail AI for retail analytics and trend analysis.

## 🚀 Features Added

### 1. OCR Chart Analysis
- **Purpose**: Extract data from uploaded charts, graphs, and visualizations
- **Technology**: OpenCV + Tesseract OCR
- **Capabilities**:
  - Extract text and numerical data from images
  - Identify chart types (bar, line, pie, scatter)
  - Analyze trends and patterns
  - Generate performance metrics

### 2. AI Chat Agent
- **Purpose**: Provide intelligent insights and recommendations
- **Technology**: OpenAI GPT-3.5-turbo
- **Capabilities**:
  - Answer questions about shop performance
  - Provide trend analysis and insights
  - Generate recommendations for improvement
  - Interpret chart data and provide business context

### 3. Advanced Analytics
- **Purpose**: Generate comprehensive performance analysis
- **Features**:
  - Revenue and profit analysis
  - Sales trend detection
  - Product performance ranking
  - Comparative shop analysis
  - Interactive visualizations

## 📁 New Files Added

```
backend/
├── ocr_service.py          # OCR functionality for chart analysis
├── ai_agent.py             # AI chat agent and analytics
├── ai_analytics.py         # API endpoints for AI features
└── templates/admin/
    └── ai_assistant.html   # AI assistant interface

setup_ai_features.py        # Setup script for dependencies
AI_FEATURES_README.md       # This documentation
```

## 🛠️ Setup Instructions

### 1. Install Dependencies
```bash
# Run the setup script
python setup_ai_features.py

# Or install manually
pip install opencv-python pytesseract Pillow openai matplotlib seaborn plotly
```

### 2. Install Tesseract OCR
- **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
- **macOS**: `brew install tesseract`
- **Ubuntu**: `sudo apt-get install tesseract-ocr`

### 3. Configure Environment
Create a `.env` file in the project root:
```env
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///smartretail.db
```

### 4. Run the Application
```bash
cd backend
python app.py
```

## 🎯 Usage Guide

### Accessing AI Assistant
1. Navigate to the admin dashboard
2. Click on "AI Assistant" in the navigation
3. Or visit: `http://localhost:5000/admin/ai-assistant`

### Chat with AI Agent
- Ask questions about your shop's performance
- Get insights on sales trends
- Request recommendations for improvement
- Examples:
  - "What are my top performing products?"
  - "How is my shop performing this month?"
  - "What recommendations do you have for improving sales?"

### Upload Charts for Analysis
1. Click on the upload area or drag and drop an image
2. Supported formats: PNG, JPG, JPEG, GIF, BMP, TIFF
3. The AI will analyze the chart and provide insights
4. Get business interpretations of the data

### API Endpoints

#### Chat with AI
```http
POST /ai_analytics/api/ai/chat
Content-Type: application/json

{
    "message": "What are my top products?",
    "shop_id": 1
}
```

#### Upload Chart
```http
POST /ai_analytics/api/ai/upload-chart
Content-Type: multipart/form-data

file: [chart_image]
shop_id: 1
```

#### Get Performance Analysis
```http
GET /ai_analytics/api/ai/performance?shop_id=1&time_period=30d
```

#### Generate Visualization
```http
GET /ai_analytics/api/ai/visualization?shop_id=1&chart_type=revenue_trend
```

## 🔧 Configuration

### OpenAI API Key
1. Get an API key from [OpenAI](https://platform.openai.com/)
2. Add it to your `.env` file: `OPENAI_API_KEY=your-key-here`
3. The AI agent will use this for generating insights

### Tesseract OCR Path
If Tesseract is not in your system PATH, update the path in `backend/ocr_service.py`:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## 📊 Chart Analysis Capabilities

### Supported Chart Types
- **Bar Charts**: Product comparisons, sales by category
- **Line Charts**: Time series data, trend analysis
- **Pie Charts**: Market share, distribution analysis
- **Scatter Plots**: Correlation analysis

### Data Extraction
- Numerical values and labels
- Chart titles and axis labels
- Trend identification (increasing, decreasing, stable)
- Time period detection
- Performance metrics calculation

### AI Interpretation
- Business context for the data
- Trend analysis and predictions
- Recommendations based on patterns
- Comparative analysis with industry standards

## 🎨 UI Features

### Chat Interface
- Real-time conversation with AI agent
- Message history and context
- Quick action buttons for common questions
- File upload for chart analysis

### Performance Dashboard
- Real-time revenue and profit metrics
- Visual indicators for trends
- Quick access to key insights
- Responsive design for mobile devices

### Chart Upload
- Drag and drop functionality
- Multiple file format support
- Real-time analysis feedback
- Results display with insights

## 🔍 Troubleshooting

### Common Issues

1. **Tesseract not found**
   - Install Tesseract OCR
   - Update the path in `ocr_service.py`

2. **OpenAI API errors**
   - Check your API key in `.env`
   - Verify you have credits in your OpenAI account

3. **Chart analysis fails**
   - Ensure image is clear and high quality
   - Try different image formats
   - Check that text in charts is readable

4. **Import errors**
   - Run `python setup_ai_features.py`
   - Check that all dependencies are installed

### Debug Mode
Enable debug logging by setting in your `.env`:
```env
FLASK_ENV=development
```

## 🚀 Future Enhancements

- **Machine Learning Models**: Custom models for retail prediction
- **Advanced Visualizations**: Interactive charts and dashboards
- **Multi-language Support**: OCR in multiple languages
- **Real-time Analytics**: Live data streaming and analysis
- **Mobile App**: Native mobile interface for AI features

## 📝 Notes

- The AI agent maintains conversation context for better responses
- Chart analysis works best with clear, high-contrast images
- Performance data is calculated in real-time from your database
- All AI features require an active internet connection for OpenAI API calls

## 🤝 Support

For issues or questions about the AI features:
1. Check the troubleshooting section above
2. Review the console logs for error messages
3. Ensure all dependencies are properly installed
4. Verify your API keys are correctly configured











