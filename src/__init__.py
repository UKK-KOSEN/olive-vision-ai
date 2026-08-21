"""OliveVision package.

Only the small utility module is imported at package startup.  This keeps the
Raspberry Pi operational runtime independent from optional research packages
such as pandas and scikit-image.  Legacy public classes remain available and
are imported only when explicitly accessed.
"""
from importlib import import_module

__version__ = "0.3.0"
__author__ = "OliveVision AI Team"

from . import utils

_LAZY_EXPORTS = {
    "ImagePreprocessor": ("preprocessing", "ImagePreprocessor"),
    "ColorSpaceConverter": ("preprocessing", "ColorSpaceConverter"),
    "ObjectDetector": ("detection", "ObjectDetector"),
    "ColorAnalyzer": ("color_analysis", "ColorAnalyzer"),
    "FeatureExtractor": ("feature_extraction", "FeatureExtractor"),
    "TimeSeriesFeatureExtractor": ("feature_extraction", "TimeSeriesFeatureExtractor"),
    "FeatureScaler": ("feature_extraction", "FeatureScaler"),
    "VideoProcessor": ("video_processor", "VideoProcessor"),
    "FrameSequenceAnalyzer": ("video_processor", "FrameSequenceAnalyzer"),
    "BackgroundRemover": ("background_removal", "BackgroundRemover"),
    "AdvancedDetector": ("advanced_detection", "AdvancedDetector"),
    "ColorRangeOptimizer": ("advanced_detection", "ColorRangeOptimizer"),
    "TextureAnalyzer": ("texture_analysis", "TextureAnalyzer"),
    "OpticalFlowAnalyzer": ("optical_flow_analysis", "OpticalFlowAnalyzer"),
    "ObjectTracker": ("optical_flow_analysis", "ObjectTracker"),
}

def __getattr__(name):
    """Load optional legacy components on demand."""
    try:
        module_name, class_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    value = getattr(import_module("." + module_name, __name__), class_name)
    globals()[name] = value
    return value

__all__ = ["utils", *_LAZY_EXPORTS]
