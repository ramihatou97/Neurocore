#!/usr/bin/env python3
"""
Complete Image Search System Setup
Analyzes images, generates embeddings, and enables semantic search with recommendations
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database.connection import get_db
# Import all models to ensure relationships are configured
from backend.database import models
from backend.database.models import Image
from backend.services.image_analysis_service import ImageAnalysisService
from backend.services.embedding_service import EmbeddingService
from backend.utils import get_logger

logger = get_logger(__name__)


async def setup_image_search_system(
    pdf_id: str,
    sample_size: int = 50,
    skip_analysis: bool = False
):
    """
    Complete setup for image search system:
    1. Analyze images with AI (if not done)
    2. Generate embeddings
    3. Enable semantic search

    Args:
        pdf_id: PDF ID to process images from
        sample_size: Number of images to process
        skip_analysis: Skip image analysis if already done
    """
    db = next(get_db())

    try:
        # ================================================================
        # PHASE 1: IMAGE ANALYSIS
        # ================================================================

        if not skip_analysis:
            print(f"\n{'='*60}")
            print(f"PHASE 1: AI IMAGE ANALYSIS ({sample_size} images)")
            print(f"{'='*60}\n")

            # Get sample of unanalyzed images
            images = db.query(Image)\
                .filter(Image.pdf_id == pdf_id)\
                .filter(Image.ai_description.is_(None))\
                .order_by(Image.page_number)\
                .limit(sample_size)\
                .all()

            if not images:
                print("❌ No unanalyzed images found")
                return

            print(f"📊 Found {len(images)} images to analyze")
            print(f"   PDF ID: {pdf_id}")
            print(f"   Pages: {images[0].page_number} to {images[-1].page_number}\n")

            # Prepare image paths and contexts
            image_data = []
            for img in images:
                image_path = Path(img.file_path)
                if image_path.exists():
                    image_data.append({
                        'image': img,
                        'path': str(image_path),
                        'context': {
                            'image_id': str(img.id),
                            'pdf_id': pdf_id,
                            'page_number': img.page_number
                        }
                    })

            print(f"✅ {len(image_data)} image files found\n")

            # Analyze images using GPT-4o (Claude credits exhausted)
            print("🔍 Analyzing images with GPT-4o Vision...")
            print(f"   Estimated time: {len(image_data) * 5} seconds (~{len(image_data) * 5 / 60:.1f} minutes)")
            print(f"   Estimated cost: ${len(image_data) * 0.003:.2f}\n")

            analysis_service = ImageAnalysisService()

            successful = 0
            failed = 0
            total_cost = 0.0

            for i, data in enumerate(image_data):
                try:
                    image_id_str = str(data['image'].id)
                    print(f"[{i+1}/{len(image_data)}] Analyzing image {image_id_str[:8]}...", end=" ")

                    result = await analysis_service.analyze_image(
                        data['path'],
                        data['context']
                    )

                    if result.get('analysis'):
                        analysis = result['analysis']
                        img = data['image']

                        # Update image record
                        img.ai_description = str(analysis)
                        img.image_type = analysis.get('image_type', 'unknown')
                        img.anatomical_structures = analysis.get('anatomical_structures', [])
                        img.quality_score = analysis.get('quality', {}).get('score', 0) / 10.0  # Convert to 0-1
                        img.confidence_score = result.get('confidence_score', 0.0)
                        # Note: ai_provider and analysis_cost_usd tracked via AIProviderMetric model

                        successful += 1
                        total_cost += result.get('cost_usd', 0.0)

                        print(f"✓ {img.image_type} (cost: ${result.get('cost_usd', 0.0):.4f})")
                    else:
                        failed += 1
                        print(f"✗ {result.get('error', 'Unknown error')}")

                except Exception as e:
                    failed += 1
                    print(f"✗ Error: {str(e)}")

            # Commit all analyses
            db.commit()

            print(f"\n{'='*60}")
            print(f"📊 ANALYSIS COMPLETE")
            print(f"{'='*60}")
            print(f"✅ Successful: {successful}/{len(image_data)} ({successful/len(image_data)*100:.1f}%)")
            print(f"❌ Failed: {failed}/{len(image_data)}")
            print(f"💰 Total Cost: ${total_cost:.4f}")
            print(f"{'='*60}\n")

        # ================================================================
        # PHASE 2: EMBEDDING GENERATION
        # ================================================================

        print(f"\n{'='*60}")
        print(f"PHASE 2: EMBEDDING GENERATION")
        print(f"{'='*60}\n")

        # Get images with descriptions but no embeddings
        images_for_embedding = db.query(Image)\
            .filter(Image.pdf_id == pdf_id)\
            .filter(Image.ai_description.isnot(None))\
            .filter(Image.embedding.is_(None))\
            .all()

        if not images_for_embedding:
            print("❌ No images need embeddings")
            return

        print(f"📊 Found {len(images_for_embedding)} images needing embeddings")
        print(f"   Model: text-embedding-3-large (1536 dims)")
        print(f"   Estimated cost: ${len(images_for_embedding) * 0.00003:.5f}\n")

        embedding_service = EmbeddingService(db)

        embedding_success = 0
        embedding_failed = 0

        for i, img in enumerate(images_for_embedding):
            try:
                img_id_str = str(img.id)
                print(f"[{i+1}/{len(images_for_embedding)}] Generating embedding for {img_id_str[:8]}...", end=" ")

                # Generate embedding from AI description
                result = await embedding_service.generate_image_embeddings(
                    str(img.id),
                    img.ai_description
                )

                embedding_success += 1
                print(f"✓ {result.get('embedding_dim', 1536)} dims")

            except Exception as e:
                embedding_failed += 1
                print(f"✗ Error: {str(e)}")

        print(f"\n{'='*60}")
        print(f"📊 EMBEDDINGS COMPLETE")
        print(f"{'='*60}")
        print(f"✅ Successful: {embedding_success}/{len(images_for_embedding)}")
        print(f"❌ Failed: {embedding_failed}/{len(images_for_embedding)}")
        print(f"{'='*60}\n")

        # ================================================================
        # PHASE 3: VALIDATION
        # ================================================================

        print(f"\n{'='*60}")
        print(f"PHASE 3: SYSTEM VALIDATION")
        print(f"{'='*60}\n")

        # Count final status
        total = db.query(Image).filter(Image.pdf_id == pdf_id).count()
        with_descriptions = db.query(Image).filter(
            Image.pdf_id == pdf_id,
            Image.ai_description.isnot(None)
        ).count()
        with_embeddings = db.query(Image).filter(
            Image.pdf_id == pdf_id,
            Image.embedding.isnot(None)
        ).count()

        print(f"📊 Final Status:")
        print(f"   Total Images: {total}")
        print(f"   With AI Descriptions: {with_descriptions} ({with_descriptions/total*100:.1f}%)")
        print(f"   With Embeddings: {with_embeddings} ({with_embeddings/total*100:.1f}%)")
        print(f"\n✅ Image Search System Ready!")
        print(f"\n💡 Test semantic search:")
        print(f"   GET /api/search/semantic/images?q=brain+MRI&max_results=5")
        print(f"\n{'='*60}\n")

    except Exception as e:
        logger.error(f"Setup failed: {str(e)}", exc_info=True)
        print(f"\n❌ Setup failed: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    # Configuration
    PDF_ID = "daec9f44-f448-4b4e-9b11-406c0b772347"  # Keyhole Approaches textbook
    SAMPLE_SIZE = 100  # Process to reach ~100 total images

    print("="*60)
    print("🚀 IMAGE SEARCH SYSTEM SETUP")
    print("="*60)
    print(f"PDF ID: {PDF_ID}")
    print(f"Sample Size: {SAMPLE_SIZE} images")
    print("="*60)

    # Run setup
    asyncio.run(setup_image_search_system(PDF_ID, SAMPLE_SIZE))
