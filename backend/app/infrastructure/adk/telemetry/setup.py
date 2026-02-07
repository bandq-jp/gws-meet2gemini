"""
ADK Telemetry Setup - Initialize OpenTelemetry providers for agent analytics.

Registers two span processors in parallel:
1. SupabaseSpanExporter → Supabase DB (for custom dashboard)
2. OTLPSpanExporter → Arize Phoenix (for advanced trace analysis)
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)

_initialized = False


def setup_adk_telemetry(settings: Settings) -> None:
    """Initialize ADK OpenTelemetry providers (call once at app startup).

    Sets up:
    - SupabaseSpanExporter for custom dashboard data
    - OTLPSpanExporter for Phoenix UI (if phoenix_endpoint configured)
    - GoogleADKInstrumentor for OpenInference semantic conventions
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    try:
        from google.adk.telemetry.setup import OTelHooks, maybe_set_otel_providers
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        from .supabase_exporter import SupabaseSpanExporter

        span_processors = []

        # 1. Supabase exporter (always enabled)
        supabase_exporter = SupabaseSpanExporter()
        span_processors.append(
            BatchSpanProcessor(
                supabase_exporter,
                max_queue_size=2048,
                max_export_batch_size=128,
            )
        )
        logger.info("[Telemetry] SupabaseSpanExporter registered")

        # 2. Phoenix OTLP exporter (if endpoint configured)
        phoenix_endpoint = settings.phoenix_endpoint
        if phoenix_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter,
                )

                otlp_exporter = OTLPSpanExporter(endpoint=phoenix_endpoint)
                span_processors.append(BatchSpanProcessor(otlp_exporter))
                logger.info(
                    f"[Telemetry] Phoenix OTLPSpanExporter registered → {phoenix_endpoint}"
                )
            except ImportError:
                logger.warning(
                    "[Telemetry] opentelemetry-exporter-otlp-proto-http not installed, "
                    "Phoenix exporter skipped"
                )
            except Exception as e:
                logger.warning(f"[Telemetry] Failed to initialize Phoenix exporter: {e}")

        # Register all processors with ADK's OTel setup
        hooks = OTelHooks(span_processors=span_processors)

        # Set OTEL_SERVICE_NAME for resource detection
        if not os.getenv("OTEL_SERVICE_NAME"):
            os.environ["OTEL_SERVICE_NAME"] = "bandq-agent"

        maybe_set_otel_providers(otel_hooks_to_setup=[hooks])
        logger.info("[Telemetry] ADK OTel providers initialized")

        # 3. OpenInference ADK Instrumentor (enriches spans for Phoenix)
        try:
            from openinference.instrumentation.google_adk import GoogleADKInstrumentor

            GoogleADKInstrumentor().instrument()
            logger.info("[Telemetry] GoogleADKInstrumentor activated")
        except ImportError:
            logger.info(
                "[Telemetry] openinference-instrumentation-google-adk not installed, "
                "instrumentor skipped"
            )
        except Exception as e:
            logger.warning(f"[Telemetry] GoogleADKInstrumentor failed: {e}")

    except Exception as e:
        logger.error(f"[Telemetry] Setup failed: {e}", exc_info=True)
