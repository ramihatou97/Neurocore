#!/usr/bin/env python3
"""
Manual Trigger Script: Image Extraction for "Keyhole Approaches in Neurosurgery"
Purpose: Test image extraction pipeline on existing book that was uploaded before fix
Book ID: f2e1cd71-2db5-4ba1-a5ba-7206b74f3b2b
"""

import sys
import uuid
from datetime import datetime

# Add backend to path
sys.path.insert(0, '/app/backend')

from backend.database.connection import db
from backend.database.models import PDF, PDFBook
from backend.services.background_tasks import extract_images_task, analyze_images_task
from backend.utils import get_logger

logger = get_logger(__name__)

# Book details
BOOK_ID = uuid.UUID('f2e1cd71-2db5-4ba1-a5ba-7206b74f3b2b')
BOOK_TITLE = "Keyhole Approaches in Neurosurgery"

def main():
    """Trigger image extraction for existing book"""

    print("="*80)
    print("IMAGE EXTRACTION TRIGGER SCRIPT")
    print(f"Book: {BOOK_TITLE}")
    print(f"Book ID: {BOOK_ID}")
    print("="*80)

    session = db.get_session()

    try:
        # Step 1: Get the book
        print("\n[1/5] Fetching book record...")
        book = session.query(PDFBook).filter(PDFBook.id == BOOK_ID).first()

        if not book:
            print(f"❌ ERROR: Book {BOOK_ID} not found!")
            return 1

        print(f"✅ Book found: {book.title}")
        print(f"   - File path: {book.file_path}")
        print(f"   - Total pages: {book.total_pages}")
        print(f"   - File size: {book.file_size_bytes / (1024*1024):.2f} MB")
        print(f"   - Uploaded: {book.uploaded_at}")

        # Step 2: Check if pdfs record already exists
        print("\n[2/5] Checking for existing pdfs record...")
        if book.pdf_id:
            existing_pdf = session.query(PDF).filter(PDF.id == book.pdf_id).first()
            if existing_pdf:
                print(f"⚠️  WARNING: pdfs record already exists: {existing_pdf.id}")
                print(f"   Status: {existing_pdf.indexing_status}")

                # Check if images already extracted
                from backend.database.models import Image
                image_count = session.query(Image).filter(Image.pdf_id == existing_pdf.id).count()
                print(f"   Images extracted: {image_count}")

                if image_count > 0:
                    print(f"✅ Book already has {image_count} images extracted!")
                    print("   No need to re-trigger extraction.")
                    return 0
                else:
                    print("   Re-triggering extraction for existing pdfs record...")
                    pdf_record = existing_pdf
            else:
                print(f"⚠️  Book has pdf_id={book.pdf_id} but record not found. Creating new one...")
                book.pdf_id = None
                pdf_record = None
        else:
            print("✅ No existing pdfs record. Will create new one.")
            pdf_record = None

        # Step 3: Create pdfs record if needed
        if not pdf_record:
            print("\n[3/5] Creating pdfs table record...")

            pdf_record = PDF(
                id=uuid.uuid4(),
                file_path=book.file_path,
                filename=f"{book.title}.pdf",
                file_size_bytes=book.file_size_bytes,
                indexing_status="pending",  # Valid status: will transition to extracting_images
                text_extracted=True  # Text already extracted
            )
            session.add(pdf_record)
            session.flush()  # Get pdf_record.id

            print(f"✅ Created pdfs record: {pdf_record.id}")

            # Step 4: Link book to pdf record
            print("\n[4/5] Linking book to pdfs record...")
            book.pdf_id = pdf_record.id
            session.commit()

            print(f"✅ Linked book.pdf_id = {book.pdf_id}")

        # Step 5: Queue image extraction tasks
        print("\n[5/5] Queueing image extraction tasks...")

        # Queue extract_images_task
        task1 = extract_images_task.delay(str(pdf_record.id))
        print(f"✅ Queued extract_images_task")
        print(f"   Task ID: {task1.id}")

        print("\n" + "="*80)
        print("SUCCESS! Image extraction pipeline triggered.")
        print("="*80)
        print("\nMonitoring Instructions:")
        print("1. Watch Celery Flower: http://localhost:5555/tasks")
        print("2. Monitor logs: docker logs -f neurocore-celery-worker-images")
        print("3. Check progress:")
        print(f"""
   docker exec neurocore-postgres psql -U nsurg_admin -d neurosurgery_kb -c "
   SELECT
     COUNT(*) as total_images,
     COUNT(CASE WHEN ai_description IS NOT NULL THEN 1 END) as analyzed,
     AVG(quality_score)::numeric(3,2) as avg_quality
   FROM images
   WHERE pdf_id = '{pdf_record.id}';"
        """)
        print("\nExpected Results:")
        print("- 40-60 images extracted (from 310 pages)")
        print("- Claude Vision 24-field analysis per image")
        print("- Processing time: ~10-15 minutes")
        print("="*80)

        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return 1

    finally:
        session.close()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
