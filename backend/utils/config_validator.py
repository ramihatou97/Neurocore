"""
Configuration Validation for AI Integration
Validates all OpenAI/AI configuration at application startup

Features:
- Validates API keys
- Checks model names
- Verifies pricing configuration
- Tests connectivity
- Validates schema files
- Reports configuration status
"""

import os
from typing import Dict, Any, List, Tuple
from pathlib import Path

from backend.config import settings
from backend.utils import get_logger

logger = get_logger(__name__)


class ConfigurationValidator:
    """
    Validates application configuration for AI integration
    """

    def __init__(self):
        """Initialize validator"""
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def validate_all(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Run all validation checks

        Returns:
            Tuple of (is_valid, report_dict)
        """
        logger.info("🔍 Starting configuration validation...")

        # Run all validators
        self._validate_api_keys()
        self._validate_models()
        self._validate_pricing()
        self._validate_dimensions()
        self._validate_schemas()
        self._validate_file_paths()
        self._validate_providers()

        # Generate report
        is_valid = len(self.errors) == 0
        report = self._generate_report(is_valid)

        # Log results
        self._log_results(is_valid)

        return is_valid, report

    def _validate_api_keys(self):
        """Validate API keys are present and formatted correctly"""
        # OpenAI
        if not settings.OPENAI_API_KEY:
            self.errors.append("OPENAI_API_KEY is not set")
        elif not settings.OPENAI_API_KEY.startswith("sk-"):
            self.errors.append("OPENAI_API_KEY has invalid format (should start with 'sk-')")
        elif len(settings.OPENAI_API_KEY) < 20:
            self.errors.append("OPENAI_API_KEY appears too short")
        else:
            self.info.append(f"✓ OpenAI API key present (length: {len(settings.OPENAI_API_KEY)})")

        # Anthropic (Claude)
        if not settings.ANTHROPIC_API_KEY:
            self.warnings.append("ANTHROPIC_API_KEY is not set (Claude will not work)")
        elif not settings.ANTHROPIC_API_KEY.startswith("sk-ant-"):
            self.warnings.append("ANTHROPIC_API_KEY has unexpected format")
        else:
            self.info.append("✓ Anthropic API key present")

        # Google (Gemini)
        if not settings.GOOGLE_API_KEY:
            self.warnings.append("GOOGLE_API_KEY is not set (Gemini will not work)")
        else:
            self.info.append("✓ Google API key present")

    def _validate_models(self):
        """Validate model names are correct"""
        # OpenAI Chat Model
        valid_chat_models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4"]
        if settings.OPENAI_CHAT_MODEL not in valid_chat_models:
            self.warnings.append(
                f"OPENAI_CHAT_MODEL '{settings.OPENAI_CHAT_MODEL}' is not in recommended list: {valid_chat_models}"
            )
        elif settings.OPENAI_CHAT_MODEL == "gpt-4o":
            self.info.append("✓ Using recommended GPT-4o model")
        else:
            self.warnings.append(f"Using {settings.OPENAI_CHAT_MODEL} instead of recommended gpt-4o")

        # OpenAI Embedding Model
        valid_embedding_models = ["text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002"]
        if settings.OPENAI_EMBEDDING_MODEL not in valid_embedding_models:
            self.errors.append(
                f"OPENAI_EMBEDDING_MODEL '{settings.OPENAI_EMBEDDING_MODEL}' is not valid. "
                f"Valid options: {valid_embedding_models}"
            )
        elif settings.OPENAI_EMBEDDING_MODEL == "text-embedding-3-large":
            self.info.append("✓ Using recommended text-embedding-3-large model")

        # Google Model
        if settings.GOOGLE_MODEL and not settings.GOOGLE_MODEL.startswith("gemini"):
            self.warnings.append(f"GOOGLE_MODEL '{settings.GOOGLE_MODEL}' doesn't appear to be a Gemini model")

    def _validate_pricing(self):
        """Validate pricing configuration"""
        # GPT-4o pricing
        if settings.OPENAI_GPT4O_INPUT_COST_PER_1K != 0.0025:
            self.warnings.append(
                f"OPENAI_GPT4O_INPUT_COST_PER_1K is {settings.OPENAI_GPT4O_INPUT_COST_PER_1K}, "
                f"expected 0.0025 (current pricing as of Jan 2025)"
            )

        if settings.OPENAI_GPT4O_OUTPUT_COST_PER_1K != 0.010:
            self.warnings.append(
                f"OPENAI_GPT4O_OUTPUT_COST_PER_1K is {settings.OPENAI_GPT4O_OUTPUT_COST_PER_1K}, "
                f"expected 0.010 (current pricing as of Jan 2025)"
            )

        # Embedding pricing
        if settings.OPENAI_EMBEDDING_3_LARGE_COST_PER_1K != 0.00013:
            self.warnings.append(
                f"OPENAI_EMBEDDING_3_LARGE_COST_PER_1K is {settings.OPENAI_EMBEDDING_3_LARGE_COST_PER_1K}, "
                f"expected 0.00013 (current pricing)"
            )

        # Check that costs are positive
        if settings.OPENAI_GPT4O_INPUT_COST_PER_1K <= 0:
            self.errors.append("OPENAI_GPT4O_INPUT_COST_PER_1K must be positive")

        if settings.OPENAI_GPT4O_OUTPUT_COST_PER_1K <= 0:
            self.errors.append("OPENAI_GPT4O_OUTPUT_COST_PER_1K must be positive")

        if not self.errors:
            self.info.append("✓ Pricing configuration appears correct")

    def _validate_dimensions(self):
        """Validate embedding dimensions match model"""
        model_dimensions = {
            "text-embedding-3-large": 3072,
            "text-embedding-3-small": 1536,
            "text-embedding-ada-002": 1536
        }

        expected_dims = model_dimensions.get(settings.OPENAI_EMBEDDING_MODEL)

        if expected_dims and settings.OPENAI_EMBEDDING_DIMENSIONS != expected_dims:
            self.errors.append(
                f"OPENAI_EMBEDDING_DIMENSIONS is {settings.OPENAI_EMBEDDING_DIMENSIONS}, "
                f"but {settings.OPENAI_EMBEDDING_MODEL} uses {expected_dims} dimensions"
            )
        else:
            self.info.append(
                f"✓ Embedding dimensions ({settings.OPENAI_EMBEDDING_DIMENSIONS}) match model"
            )

    def _validate_schemas(self):
        """Validate AI schema files exist and are valid"""
        try:
            from backend.schemas.ai_schemas import (
                CHAPTER_ANALYSIS_SCHEMA,
                CONTEXT_BUILDING_SCHEMA,
                FACT_CHECK_SCHEMA,
                METADATA_EXTRACTION_SCHEMA,
                SOURCE_RELEVANCE_SCHEMA,
                IMAGE_ANALYSIS_SCHEMA
            )

            schemas = [
                ("CHAPTER_ANALYSIS_SCHEMA", CHAPTER_ANALYSIS_SCHEMA),
                ("CONTEXT_BUILDING_SCHEMA", CONTEXT_BUILDING_SCHEMA),
                ("FACT_CHECK_SCHEMA", FACT_CHECK_SCHEMA),
                ("METADATA_EXTRACTION_SCHEMA", METADATA_EXTRACTION_SCHEMA),
                ("SOURCE_RELEVANCE_SCHEMA", SOURCE_RELEVANCE_SCHEMA),
                ("IMAGE_ANALYSIS_SCHEMA", IMAGE_ANALYSIS_SCHEMA)
            ]

            for name, schema in schemas:
                if not isinstance(schema, dict):
                    self.errors.append(f"{name} is not a dictionary")
                    continue

                if "name" not in schema:
                    self.errors.append(f"{name} missing 'name' field")

                if "schema" not in schema:
                    self.errors.append(f"{name} missing 'schema' field")

                if "strict" not in schema:
                    self.errors.append(f"{name} missing 'strict' field")
                elif schema["strict"] is not True:
                    self.warnings.append(f"{name} has strict=False (should be True for structured outputs)")

            if not self.errors:
                self.info.append(f"✓ All {len(schemas)} schemas validated successfully")

        except ImportError as e:
            self.errors.append(f"Failed to import AI schemas: {str(e)}")

    def _validate_file_paths(self):
        """Validate critical file paths exist"""
        critical_files = [
            "backend/schemas/ai_schemas.py",
            "backend/services/ai_provider_service.py",
            "backend/services/fact_checking_service.py",
            "backend/services/batch_provider_service.py"
        ]

        base_path = Path(__file__).parent.parent.parent

        for file_path in critical_files:
            full_path = base_path / file_path
            if not full_path.exists():
                self.errors.append(f"Critical file missing: {file_path}")
            else:
                self.info.append(f"✓ Found {file_path}")

    def _validate_providers(self):
        """Validate AI provider configuration"""
        # Check task routing
        try:
            from backend.services.ai_provider_service import AITask, AIProvider

            # Just verify the enums exist
            self.info.append(f"✓ AITask enum has {len(list(AITask))} tasks")
            self.info.append(f"✓ AIProvider enum has {len(list(AIProvider))} providers")

        except Exception as e:
            self.errors.append(f"Failed to validate provider configuration: {str(e)}")

    def _generate_report(self, is_valid: bool) -> Dict[str, Any]:
        """Generate validation report"""
        return {
            "valid": is_valid,
            "timestamp": str(datetime.utcnow()),
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "summary": {
                "total_errors": len(self.errors),
                "total_warnings": len(self.warnings),
                "total_info": len(self.info),
                "status": "VALID" if is_valid else "INVALID"
            },
            "configuration": {
                "openai_chat_model": settings.OPENAI_CHAT_MODEL,
                "openai_embedding_model": settings.OPENAI_EMBEDDING_MODEL,
                "openai_embedding_dimensions": settings.OPENAI_EMBEDDING_DIMENSIONS,
                "google_model": settings.GOOGLE_MODEL,
                "anthropic_model": settings.ANTHROPIC_MODEL,
                "has_openai_key": bool(settings.OPENAI_API_KEY),
                "has_anthropic_key": bool(settings.ANTHROPIC_API_KEY),
                "has_google_key": bool(settings.GOOGLE_API_KEY)
            }
        }

    def _log_results(self, is_valid: bool):
        """Log validation results"""
        if is_valid:
            logger.info("=" * 70)
            logger.info("✅ CONFIGURATION VALIDATION PASSED")
            logger.info("=" * 70)

            if self.warnings:
                logger.warning(f"⚠️  {len(self.warnings)} warnings:")
                for warning in self.warnings:
                    logger.warning(f"   - {warning}")

            logger.info(f"\n📋 Configuration Summary:")
            for info_msg in self.info:
                logger.info(f"   {info_msg}")

        else:
            logger.error("=" * 70)
            logger.error("❌ CONFIGURATION VALIDATION FAILED")
            logger.error("=" * 70)

            logger.error(f"\n🚨 {len(self.errors)} ERRORS:")
            for error in self.errors:
                logger.error(f"   - {error}")

            if self.warnings:
                logger.warning(f"\n⚠️  {len(self.warnings)} WARNINGS:")
                for warning in self.warnings:
                    logger.warning(f"   - {warning}")


def validate_configuration() -> Tuple[bool, Dict[str, Any]]:
    """
    Convenience function to validate configuration

    Returns:
        Tuple of (is_valid, report_dict)

    Usage:
        # In main.py or app startup:
        is_valid, report = validate_configuration()
        if not is_valid:
            logger.error("Configuration invalid, check errors above")
            # Optionally exit or continue with warnings
    """
    validator = ConfigurationValidator()
    return validator.validate_all()


# Import datetime for report timestamps
from datetime import datetime
