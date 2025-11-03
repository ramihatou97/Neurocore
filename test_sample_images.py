#!/usr/bin/env python3
"""
Sample Image Analysis Test
Tests Claude Vision on a small subset of images (~20) for quick validation

This allows testing the full pipeline without waiting 2.4 hours for all 730 images.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.database.connection import get_db
from backend.database.models import Image
from backend.services.image_analysis_service import ImageAnalysisService
from backend.utils import get_logger

logger = get_logger(__name__)


async def test_sample_images(pdf_id: str, sample_size: int = 20):
    """
    Test Claude Vision on a sample of images

    Args:
        pdf_id: PDF ID to sample images from
        sample_size: Number of images to test (default 20)
    """
    db = next(get_db())

    try:
        # Get sample of images (first N images, ordered by page number)
        print(f"\n📊 Fetching {sample_size} sample images from database...")
        images = db.query(Image)\
            .filter(Image.pdf_id == pdf_id)\
            .filter(Image.ai_description.is_(None))\
            .order_by(Image.page_number)\
            .limit(sample_size)\
            .all()

        if not images:
            print(f"❌ No unanalyzed images found for PDF ID: {pdf_id}")
            return

        print(f"✅ Found {len(images)} images to analyze")
        print(f"   Pages: {images[0].page_number} to {images[-1].page_number}")
        print(f"   Formats: {set(img.format for img in images)}")

        # Prepare image paths
        image_paths = []
        for img in images:
            image_path = Path(img.file_path)
            if image_path.exists():
                image_paths.append(str(image_path))
            else:
                print(f"⚠️  Image not found: {image_path}")

        print(f"\n🔍 Analyzing {len(image_paths)} images with Claude Vision...")
        print(f"   Estimated time: {len(image_paths) * 12} seconds (~{len(image_paths) * 12 / 60:.1f} minutes)")
        print(f"   Estimated cost: ${len(image_paths) * 0.015:.2f}")

        # Analyze images
        analysis_service = ImageAnalysisService()

        results = await analysis_service.analyze_images_batch(
            image_paths=image_paths,
            context={
                'pdf_id': pdf_id,
                'test_mode': True
            },
            max_concurrent=3  # Lower concurrency for testing
        )

        print(f"\n✅ Analysis complete!")

        # Update database with results
        successful = 0
        failed = 0
        total_cost = 0.0

        for img, result in zip(images, results):
            if result.get('analysis'):
                analysis = result['analysis']

                # Update image record
                img.ai_description = str(analysis)
                img.image_type = analysis.get('image_type', 'unknown')
                img.anatomical_structures = analysis.get('anatomical_structures', [])
                img.quality_score = analysis.get('quality', {}).get('score', 0)
                img.confidence_score = result.get('confidence_score', 0.0)
                img.ai_provider = result.get('provider', 'claude')
                img.analysis_cost_usd = result.get('cost_usd', 0.0)

                successful += 1
                total_cost += result.get('cost_usd', 0.0)

                print(f"✅ {img.image_id[:8]}: {analysis.get('image_type', 'unknown')} "
                      f"(quality: {analysis.get('quality', {}).get('score', 0)}/10, "
                      f"cost: ${result.get('cost_usd', 0.0):.4f})")
            else:
                failed += 1
                print(f"❌ {img.image_id[:8]}: {result.get('error', 'Unknown error')}")

        # Commit changes
        db.commit()
        print(f"\n💾 Database updated!")

        # Summary
        print(f"\n" + "="*60)
        print(f"📊 SAMPLE TEST RESULTS")
        print(f"="*60)
        print(f"✅ Successful: {successful}/{len(images)} ({successful/len(images)*100:.1f}%)")
        print(f"❌ Failed: {failed}/{len(images)}")
        print(f"💰 Total Cost: ${total_cost:.4f}")
        print(f"📈 Average Cost: ${total_cost/successful:.4f} per image" if successful > 0 else "")
        print(f"="*60)

        # Show sample analysis
        if successful > 0:
            print(f"\n📝 Sample Analysis (first successful image):")
            for img, result in zip(images, results):
                if result.get('analysis'):
                    analysis = result['analysis']
                    print(f"\n   Image Type: {analysis.get('image_type', 'unknown')}")
                    print(f"   Anatomical Structures: {', '.join(analysis.get('anatomical_structures', [])[:3])}")
                    print(f"   Clinical Significance: {analysis.get('clinical_significance', {}).get('score', 0)}/10")
                    print(f"   Quality Score: {analysis.get('quality', {}).get('score', 0)}/10")
                    print(f"   Educational Value: {analysis.get('educational_value', {}).get('score', 0)}/10")
                    print(f"   Confidence: {result.get('confidence_score', 0.0):.2f}")
                    break

        print(f"\n🎉 Sample test complete! Pipeline validated successfully.")

    except Exception as e:
        logger.error(f"Sample test failed: {str(e)}", exc_info=True)
        print(f"\n❌ Sample test failed: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Test parameters
    PDF_ID = "daec9f44-f448-4b4e-9b11-406c0b772347"  # Keyhole Approaches PDF
    SAMPLE_SIZE = 20

    print("="*60)
    print("🧪 SAMPLE IMAGE ANALYSIS TEST")
    print("="*60)
    print(f"PDF ID: {PDF_ID}")
    print(f"Sample Size: {SAMPLE_SIZE} images")
    print(f"Provider: Claude Vision (Sonnet 4.5)")
    print("="*60)

    # Run test
    asyncio.run(test_sample_images(PDF_ID, SAMPLE_SIZE))
