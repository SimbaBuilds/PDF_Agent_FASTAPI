"""
OCR Processor Service

Service for performing Optical Character Recognition on images.
"""

import logging
from typing import Optional, List
from PIL import Image

logger = logging.getLogger(__name__)


class OCRProcessor:
    """
    Service for OCR processing of images.
    """

    def __init__(self):
        """Initialize the OCR processor."""
        self.available = False
        logger.info("Initialized OCR processor (placeholder - OCR disabled)")

    def process_image(self, image: Image.Image) -> str:
        """
        Extract text from an image using OCR.

        Args:
            image: PIL Image object

        Returns:
            Extracted text string
        """
        if not self.available:
            logger.warning("OCR not available - returning empty string")
            return ""

        # Placeholder implementation
        return ""

    def process_images(self, images: List[Image.Image]) -> List[str]:
        """
        Extract text from multiple images.

        Args:
            images: List of PIL Image objects

        Returns:
            List of extracted text strings
        """
        return [self.process_image(img) for img in images]

    def is_available(self) -> bool:
        """Check if OCR is available."""
        return self.available


# Global instance
ocr_processor = OCRProcessor()
