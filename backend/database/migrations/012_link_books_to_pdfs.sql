-- Migration 012: Link pdf_books to pdfs table for image extraction
-- Date: 2025-11-02
-- Purpose: Enable image extraction pipeline for textbook uploads
--
-- Context:
-- - Textbook uploads create records in pdf_books table
-- - Image extraction operates on pdfs table
-- - This migration creates the link between both systems
--
-- Impact:
-- - Adds pdf_id column to pdf_books (nullable for backward compatibility)
-- - Enables textbook uploads to trigger image extraction
-- - Allows chapter generation to access analyzed images

BEGIN;

-- Step 1: Add pdf_id column to pdf_books
-- Nullable to support existing books that don't have pdf records yet
ALTER TABLE pdf_books
ADD COLUMN IF NOT EXISTS pdf_id UUID;

-- Step 2: Add foreign key constraint
-- ON DELETE SET NULL ensures books aren't deleted if pdf record is removed
-- This is safe because pdfs table is now secondary (books can exist without pdfs entry)
ALTER TABLE pdf_books
ADD CONSTRAINT fk_pdf_books_pdf_id
FOREIGN KEY (pdf_id)
REFERENCES pdfs(id)
ON DELETE SET NULL;

-- Step 3: Create index for performance
-- Speeds up queries that join pdf_books to pdfs via pdf_id
CREATE INDEX IF NOT EXISTS idx_pdf_books_pdf_id ON pdf_books(pdf_id);

-- Step 4: Add comment for documentation
COMMENT ON COLUMN pdf_books.pdf_id IS 'Link to pdfs table for image extraction pipeline. Nullable for books uploaded before migration 012.';

COMMIT;

-- Verification query (run after migration):
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'pdf_books' AND column_name = 'pdf_id';
--
-- Expected result:
-- column_name | data_type | is_nullable
-- ------------+-----------+-------------
-- pdf_id      | uuid      | YES
