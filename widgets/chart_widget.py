"""
Chart widget for displaying time-series data.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF
from typing import List, Tuple
import math


class ChartWidget(QWidget):
    """A simple chart widget for displaying time-series data."""

    def __init__(self, title: str, color: QColor = QColor(0, 150, 255), parent=None):
        super().__init__(parent)
        self.title = title
        self.line_color = color
        self.background_color = QColor(245, 245, 245)
        self.axis_color = QColor(200, 200, 200)
        self.text_color = QColor(80, 80, 80)
        
        # Data storage
        self.data_points: List[float] = []  # Y values (0-100 scale)
        self.max_points = 50  # Maximum number of points to display
        
        # UI setup
        self.setMinimumHeight(120)
        self.setMinimumWidth(200)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = self.title_label.font()
        font.setPointSize(10)
        font.setBold(True)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)
        
        # Chart area
        self.chart_frame = QFrame()
        self.chart_frame.setFrameStyle(QFrame.StyledPanel)
        self.chart_frame.setLineWidth(1)
        layout.addWidget(self.chart_frame)
        
        # Value label
        self.value_label = QLabel("0%")
        self.value_label.setAlignment(Qt.AlignCenter)
        font = self.value_label.font()
        font.setPointSize(9)
        self.value_label.setFont(font)
        layout.addWidget(self.value_label)

    def add_data_point(self, value: float, label: str = None):
        """
        Add a new data point to the chart.

        Args:
            value: Value to add (typically 0-100 for percentage)
            label: Optional label to display instead of percentage
        """
        self.data_points.append(float(value))
        if len(self.data_points) > self.max_points:
            self.data_points.pop(0)

        # Update current value display
        if label:
            self.value_label.setText(label)
        else:
            self.value_label.setText(f"{value:.1f}%")

        # Trigger repaint
        self.update()

    def clear_data(self):
        """Clear all data points."""
        self.data_points.clear()
        self.value_label.setText("0%")
        self.update()

    def set_data(self, values: List[float]):
        """
        Set the data points directly.
        
        Args:
            values: List of float values
        """
        self.data_values = values[-self.max_points:] if len(values) > self.max_points else values
        self.value_label.setText(f"{self.data_values[-1]:.1f}%" if self.data_values else "0%")
        self.update()

    def paintEvent(self, event):
        """Paint the chart."""
        super().paintEvent(event)
        
        # Get the chart frame's geometry
        frame_rect = self.chart_frame.frameRect()
        if not self.data_points or len(self.data_points) < 2:
            # Not enough data to draw a line
            painter = QPainter(self)
            painter.setPen(QPen(self.axis_color, 1))
            painter.drawText(frame_rect, Qt.AlignCenter, "No data")
            return
            
        # Create painter for the chart area
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate chart margins
        margin = 20
        chart_rect = QRectF(
            frame_rect.x() + margin,
            frame_rect.y() + margin,
            frame_rect.width() - 2 * margin,
            frame_rect.height() - 2 * margin
        )
        
        # Draw background
        painter.fillRect(chart_rect, self.background_color)
        
        # Draw axes
        pen = QPen(self.axis_color, 1)
        painter.setPen(pen)
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.bottomRight())  # X-axis
        painter.drawLine(chart_rect.topLeft(), chart_rect.bottomLeft())     # Y-axis
        
        if len(self.data_points) < 2:
            return
            
        # Calculate scaling
        max_val = max(self.data_points) if self.data_points else 100
        min_val = min(self.data_points) if self.data_points else 0
        
        # Add some padding to avoid touching the edges
        value_range = max(max_val - min_val, 10)  # Minimum range of 10
        max_val += value_range * 0.1
        min_val -= value_range * 0.1
        
        if max_val == min_val:
            max_val = min_val + 10
            
        # Scale factors
        x_scale = chart_rect.width() / max(1, len(self.data_points) - 1)
        y_scale = chart_rect.height() / (max_val - min_val)
        
        # Create points for the line
        points = []
        for i, value in enumerate(self.data_points):
            x = chart_rect.x() + i * x_scale
            y = chart_rect.bottom() - (value - min_val) * y_scale
            points.append(QPointF(x, y))
        
        # Draw the line
        if len(points) >= 2:
            pen = QPen(self.line_color, 2)
            painter.setPen(pen)
            
            # Draw lines between points
            for i in range(1, len(points)):
                painter.drawLine(points[i-1], points[i])
            
            # Draw points as circles
            painter.setBrush(QBrush(self.line_color))
            for point in points:
                painter.drawEllipse(point, 2, 2)

    def sizeHint(self):
        """Provide a size hint for the widget."""
        return self.size()


class NetworkTrafficChart(QWidget):
    """A widget that shows both upload and download traffic charts."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Upload chart
        self.upload_chart = ChartWidget("Upload Speed", QColor(255, 100, 100))
        layout.addWidget(self.upload_chart)
        
        # Download chart
        self.download_chart = ChartWidget("Download Speed", QColor(100, 200, 100))
        layout.addWidget(self.download_chart)
        
    def update_traffic(self, upload_percent: float, download_percent: float,
                       upload_label: str = None, download_label: str = None):
        """
        Update both charts with new traffic data.

        Args:
            upload_percent: Upload percentage (0-100)
            download_percent: Download percentage (0-100)
            upload_label: Optional label for upload speed
            download_label: Optional label for download speed
        """
        self.upload_chart.add_data_point(upload_percent, upload_label)
        self.download_chart.add_data_point(download_percent, download_label)
        
    def clear(self):
        """Clear all chart data."""
        self.upload_chart.clear_data()
        self.download_chart.clear_data()
        
    def set_data(self, upload_data: List[float], download_data: List[float]):
        """
        Set data for both charts.
        
        Args:
            upload_data: List of upload percentages
            download_data: List of download percentages
        """
        self.upload_chart.set_data(upload_data)
        self.download_chart.set_data(download_data)
