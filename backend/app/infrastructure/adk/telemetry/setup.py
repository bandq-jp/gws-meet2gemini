"""
ADK Telemetry Setup - Initialize OpenTelemetry providers for Arize Phoenix.

Registers:
1. OTLPSpanExporter → Arize Phoenix (trace analysis, token tracking, cache metrics)
2. GoogleADKInstrumentor → OpenInference semantic conventions
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
    - OTLPSpanExporter for Phoenix UI
    - GoogleADKInstrumentor for OpenInference semantic conventions
    - Cache token attribute patch for Phoenix cache metrics
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    try:
        from google.adk.telemetry.setup import OTelHooks, maybe_set_otel_providers
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        span_processors = []

        # Phoenix OTLP exporter
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
        else:
            logger.info("[Telemetry] No PHOENIX_ENDPOINT configured, telemetry disabled")
            return

        # Register processors with ADK's OTel setup
        hooks = OTelHooks(span_processors=span_processors)

        # Set OTEL_SERVICE_NAME for resource detection
        if not os.getenv("OTEL_SERVICE_NAME"):
            os.environ["OTEL_SERVICE_NAME"] = "bandq-agent"

        maybe_set_otel_providers(otel_hooks_to_setup=[hooks])
        logger.info("[Telemetry] ADK OTel providers initialized")

        # OpenInference ADK Instrumentor (enriches spans for Phoenix)
        try:
            from openinference.instrumentation.google_adk import GoogleADKInstrumentor

            GoogleADKInstrumentor().instrument()
            logger.info("[Telemetry] GoogleADKInstrumentor activated")

            # Patch: Add cache token attributes to spans
            # The upstream instrumentor doesn't extract cached_content_token_count
            # even though the semantic convention (LLM_TOKEN_COUNT_PROMPT_DETAILS_CACHE_READ)
            # is defined. This patch adds it so Phoenix can display cache hit metrics.
            _patch_cache_token_attributes()
        except ImportError:
            logger.info(
                "[Telemetry] openinference-instrumentation-google-adk not installed, "
                "instrumentor skipped"
            )
        except Exception as e:
            logger.warning(f"[Telemetry] GoogleADKInstrumentor failed: {e}")

    except Exception as e:
        logger.error(f"[Telemetry] Setup failed: {e}", exc_info=True)


def _patch_cache_token_attributes() -> None:
    """Patch OpenInference instrumentor to include Gemini cache token counts.

    The upstream _get_attributes_from_usage_metadata() doesn't extract
    cached_content_token_count from Gemini API responses, even though
    the OpenInference semantic convention defines the attribute.
    This patch adds it so Phoenix displays cache hit metrics in the UI.
    """
    try:
        import openinference.instrumentation.google_adk._wrappers as _wrappers
        from openinference.semconv.trace import SpanAttributes

        _original_fn = _wrappers._get_attributes_from_usage_metadata

        def _patched_fn(obj):  # type: ignore[no-untyped-def]
            yield from _original_fn(obj)
            try:
                cached = getattr(obj, "cached_content_token_count", None)
                if cached:
                    yield (
                        SpanAttributes.LLM_TOKEN_COUNT_PROMPT_DETAILS_CACHE_READ,
                        cached,
                    )
            except Exception:
                pass

        _wrappers._get_attributes_from_usage_metadata = _patched_fn
        logger.info("[Telemetry] Patched cache token attributes for Phoenix")
    except Exception as e:
        logger.warning(f"[Telemetry] Failed to patch cache token attributes: {e}")
