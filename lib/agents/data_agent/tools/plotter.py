"""Visualization tool for generating charts and plots.

Generates matplotlib/plotly charts and saves to artifacts directory.
"""

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px


@dataclass
class PlotResult:
    """Result from plot generation."""
    artifact_id: str
    file_path: str
    content_hash: str
    plot_type: str
    size_bytes: int
    execution_time_seconds: float
    metadata: Dict[str, Any]


class PlotGenerationError(Exception):
    """Plot generation failure."""
    def __init__(self, message: str, error_category: str):
        super().__init__(message)
        self.error_category = error_category


class Plotter:
    """Generate charts and visualizations.
    
    Supports:
    - Line charts
    - Bar charts
    - Scatter plots
    - Histograms
    - Box plots
    - Heatmaps
    """
    
    def __init__(self, artifacts_dir: Union[str, Path]):
        """Initialize plotter.
        
        Args:
            artifacts_dir: Directory to save generated plots
        """
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    def line_chart(
        self,
        df: pd.DataFrame,
        x: str,
        y: Union[str, List[str]],
        title: Optional[str] = None,
        backend: str = "matplotlib",
        **kwargs: Any,
    ) -> PlotResult:
        """Generate line chart.
        
        Args:
            df: Input DataFrame
            x: Column for x-axis
            y: Column(s) for y-axis
            title: Chart title
            backend: "matplotlib" or "plotly"
            **kwargs: Additional plotting parameters
        
        Returns:
            PlotResult with file path and metadata
        
        Raises:
            PlotGenerationError: Plot generation failed
        """
        start_time = time.time()
        
        try:
            if backend == "matplotlib":
                return self._matplotlib_line_chart(df, x, y, title, start_time, **kwargs)
            elif backend == "plotly":
                return self._plotly_line_chart(df, x, y, title, start_time, **kwargs)
            else:
                raise PlotGenerationError(
                    f"Unsupported backend: {backend}",
                    error_category="type_mismatch",
                )
        
        except Exception as e:
            raise PlotGenerationError(
                f"Line chart generation failed: {str(e)}",
                error_category="tool_failure",
            ) from e
    
    def bar_chart(
        self,
        df: pd.DataFrame,
        x: str,
        y: str,
        title: Optional[str] = None,
        backend: str = "matplotlib",
        **kwargs: Any,
    ) -> PlotResult:
        """Generate bar chart.
        
        Args:
            df: Input DataFrame
            x: Column for x-axis (categories)
            y: Column for y-axis (values)
            title: Chart title
            backend: "matplotlib" or "plotly"
            **kwargs: Additional plotting parameters
        
        Returns:
            PlotResult with file path and metadata
        """
        start_time = time.time()
        
        try:
            if backend == "matplotlib":
                return self._matplotlib_bar_chart(df, x, y, title, start_time, **kwargs)
            elif backend == "plotly":
                return self._plotly_bar_chart(df, x, y, title, start_time, **kwargs)
            else:
                raise PlotGenerationError(
                    f"Unsupported backend: {backend}",
                    error_category="type_mismatch",
                )
        
        except Exception as e:
            raise PlotGenerationError(
                f"Bar chart generation failed: {str(e)}",
                error_category="tool_failure",
            ) from e
    
    def scatter_plot(
        self,
        df: pd.DataFrame,
        x: str,
        y: str,
        color: Optional[str] = None,
        size: Optional[str] = None,
        title: Optional[str] = None,
        backend: str = "plotly",
        **kwargs: Any,
    ) -> PlotResult:
        """Generate scatter plot.
        
        Args:
            df: Input DataFrame
            x: Column for x-axis
            y: Column for y-axis
            color: Column for color encoding
            size: Column for size encoding
            title: Chart title
            backend: "matplotlib" or "plotly"
            **kwargs: Additional plotting parameters
        
        Returns:
            PlotResult with file path and metadata
        """
        start_time = time.time()
        
        try:
            if backend == "plotly":
                fig = px.scatter(df, x=x, y=y, color=color, size=size, title=title, **kwargs)
                return self._save_plotly_figure(fig, "scatter", start_time)
            elif backend == "matplotlib":
                fig, ax = plt.subplots(figsize=(10, 6))
                
                if color:
                    scatter = ax.scatter(df[x], df[y], c=df[color], cmap='viridis', alpha=0.6)
                    plt.colorbar(scatter, label=color)
                else:
                    ax.scatter(df[x], df[y], alpha=0.6)
                
                ax.set_xlabel(x)
                ax.set_ylabel(y)
                if title:
                    ax.set_title(title)
                plt.tight_layout()
                
                return self._save_matplotlib_figure(fig, "scatter", start_time)
            else:
                raise PlotGenerationError(
                    f"Unsupported backend: {backend}",
                    error_category="type_mismatch",
                )
        
        except Exception as e:
            raise PlotGenerationError(
                f"Scatter plot generation failed: {str(e)}",
                error_category="tool_failure",
            ) from e
    
    def _matplotlib_line_chart(
        self,
        df: pd.DataFrame,
        x: str,
        y: Union[str, List[str]],
        title: Optional[str],
        start_time: float,
        **kwargs: Any,
    ) -> PlotResult:
        """Generate matplotlib line chart."""
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        y_cols = [y] if isinstance(y, str) else y
        for col in y_cols:
            ax.plot(df[x], df[col], label=col, **kwargs)
        
        ax.set_xlabel(x)
        ax.set_ylabel('Value')
        if title:
            ax.set_title(title)
        if len(y_cols) > 1:
            ax.legend()
        plt.tight_layout()
        
        return self._save_matplotlib_figure(fig, "line", start_time)
    
    def _plotly_line_chart(
        self,
        df: pd.DataFrame,
        x: str,
        y: Union[str, List[str]],
        title: Optional[str],
        start_time: float,
        **kwargs: Any,
    ) -> PlotResult:
        """Generate plotly line chart."""
        
        y_cols = [y] if isinstance(y, str) else y
        fig = go.Figure()
        
        for col in y_cols:
            fig.add_trace(go.Scatter(x=df[x], y=df[col], mode='lines', name=col))
        
        fig.update_layout(
            title=title or 'Line Chart',
            xaxis_title=x,
            yaxis_title='Value',
        )
        
        return self._save_plotly_figure(fig, "line", start_time)
    
    def _matplotlib_bar_chart(
        self,
        df: pd.DataFrame,
        x: str,
        y: str,
        title: Optional[str],
        start_time: float,
        **kwargs: Any,
    ) -> PlotResult:
        """Generate matplotlib bar chart."""
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(df[x], df[y], **kwargs)
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        if title:
            ax.set_title(title)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        return self._save_matplotlib_figure(fig, "bar", start_time)
    
    def _plotly_bar_chart(
        self,
        df: pd.DataFrame,
        x: str,
        y: str,
        title: Optional[str],
        start_time: float,
        **kwargs: Any,
    ) -> PlotResult:
        """Generate plotly bar chart."""
        
        fig = px.bar(df, x=x, y=y, title=title, **kwargs)
        
        return self._save_plotly_figure(fig, "bar", start_time)
    
    def _save_matplotlib_figure(
        self,
        fig: matplotlib.figure.Figure,
        plot_type: str,
        start_time: float,
    ) -> PlotResult:
        """Save matplotlib figure to file."""
        import uuid
        
        artifact_id = str(uuid.uuid4())
        filename = f"{artifact_id}_{plot_type}.png"
        file_path = self.artifacts_dir / filename
        
        fig.savefig(file_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        
        content_hash = self._compute_file_hash(file_path)
        size_bytes = file_path.stat().st_size
        execution_time = time.time() - start_time
        
        return PlotResult(
            artifact_id=artifact_id,
            file_path=str(file_path),
            content_hash=content_hash,
            plot_type=plot_type,
            size_bytes=size_bytes,
            execution_time_seconds=execution_time,
            metadata={"backend": "matplotlib", "format": "png"},
        )
    
    def _save_plotly_figure(
        self,
        fig: go.Figure,
        plot_type: str,
        start_time: float,
    ) -> PlotResult:
        """Save plotly figure to file."""
        import uuid
        
        artifact_id = str(uuid.uuid4())
        filename = f"{artifact_id}_{plot_type}.html"
        file_path = self.artifacts_dir / filename
        
        fig.write_html(file_path)
        
        content_hash = self._compute_file_hash(file_path)
        size_bytes = file_path.stat().st_size
        execution_time = time.time() - start_time
        
        return PlotResult(
            artifact_id=artifact_id,
            file_path=str(file_path),
            content_hash=content_hash,
            plot_type=plot_type,
            size_bytes=size_bytes,
            execution_time_seconds=execution_time,
            metadata={"backend": "plotly", "format": "html"},
        )
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file content."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()