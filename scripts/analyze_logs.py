#!/usr/bin/env python3
"""Analyze LangChain observability logs from structured JSON logs."""

import json
import sys
from collections import defaultdict
from typing import Dict, List, Optional


def analyze_logs(log_file: str, request_id: Optional[str] = None):
    """
    Analyze structured logs for LangChain operations.

    Args:
        log_file: Path to log file (or '-' for stdin)
        request_id: Optional request ID to filter by
    """

    llm_calls = []
    retrievals = []
    chains = []
    requests = defaultdict(list)
    errors = []

    # Open file or stdin
    if log_file == '-':
        f = sys.stdin
    else:
        f = open(log_file, 'r')

    try:
        for line in f:
            try:
                log = json.loads(line.strip())
                event = log.get('event')
                req_id = log.get('request_id')

                # Filter by request ID if provided
                if request_id and req_id != request_id:
                    continue

                if req_id:
                    requests[req_id].append(log)

                if event == 'llm_start':
                    llm_calls.append(log)
                elif event == 'llm_end':
                    llm_calls.append(log)
                elif event == 'llm_error':
                    errors.append(log)
                elif event == 'retriever_end':
                    retrievals.append(log)
                elif event == 'retriever_error':
                    errors.append(log)
                elif event == 'chain_end':
                    chains.append(log)
                elif event == 'chain_error':
                    errors.append(log)
            except json.JSONDecodeError:
                continue
    finally:
        if log_file != '-':
            f.close()

    # Print statistics
    print("=" * 60)
    print("LANGCHAIN OBSERVABILITY ANALYSIS")
    print("=" * 60)

    if request_id:
        print(f"\nFiltered by request_id: {request_id}")

    print(f"\n📊 SUMMARY")
    print(f"  Total LLM calls: {len([l for l in llm_calls if l.get('event') == 'llm_end'])}")
    print(f"  Total retrievals: {len(retrievals)}")
    print(f"  Total chains: {len(chains)}")
    print(f"  Total errors: {len(errors)}")
    print(f"  Total requests: {len(requests)}")

    # LLM Statistics
    llm_ends = [l for l in llm_calls if l.get('event') == 'llm_end']
    if llm_ends:
        print(f"\n🤖 LLM PERFORMANCE")
        latencies = [l.get('duration_ms', 0) for l in llm_ends if l.get('duration_ms')]
        if latencies:
            print(f"  Average latency: {sum(latencies) / len(latencies):.2f}ms")
            print(f"  Min latency: {min(latencies):.2f}ms")
            print(f"  Max latency: {max(latencies):.2f}ms")

        # Token usage
        total_tokens = sum(
            l.get('token_usage', {}).get('total_tokens', 0)
            for l in llm_ends
            if l.get('token_usage', {}).get('total_tokens')
        )
        if total_tokens > 0:
            print(f"  Total tokens used: {total_tokens:,}")

        # Models used
        models = set(l.get('model', 'unknown') for l in llm_ends if l.get('model'))
        if models:
            print(f"  Models used: {', '.join(models)}")

    # Retrieval Statistics
    if retrievals:
        print(f"\n🔍 RETRIEVAL PERFORMANCE")
        doc_counts = [r.get('document_count', 0) for r in retrievals if r.get('document_count')]
        if doc_counts:
            print(f"  Average documents per retrieval: {sum(doc_counts) / len(doc_counts):.2f}")
            print(f"  Total documents retrieved: {sum(doc_counts):,}")

        latencies = [r.get('duration_ms', 0) for r in retrievals if r.get('duration_ms')]
        if latencies:
            print(f"  Average retrieval latency: {sum(latencies) / len(latencies):.2f}ms")

        # Sources
        all_sources = []
        for r in retrievals:
            sources = r.get('sources', [])
            if isinstance(sources, list):
                all_sources.extend(sources)
        if all_sources:
            source_counts = defaultdict(int)
            for source in all_sources:
                source_counts[source] += 1
            print(f"  Document sources: {dict(source_counts)}")

    # Chain Statistics
    if chains:
        print(f"\n⛓️  CHAIN PERFORMANCE")
        latencies = [c.get('duration_ms', 0) for c in chains if c.get('duration_ms')]
        if latencies:
            print(f"  Average chain latency: {sum(latencies) / len(latencies):.2f}ms")
            print(f"  Min chain latency: {min(latencies):.2f}ms")
            print(f"  Max chain latency: {max(latencies):.2f}ms")

        # Chain names
        chain_names = set(c.get('chain_name', 'unknown') for c in chains if c.get('chain_name'))
        if chain_names:
            print(f"  Chains executed: {', '.join(chain_names)}")

    # Error Statistics
    if errors:
        print(f"\n❌ ERRORS")
        error_types = defaultdict(int)
        for e in errors:
            error_type = e.get('error_type', 'unknown')
            error_types[error_type] += 1
        for error_type, count in error_types.items():
            print(f"  {error_type}: {count}")

    # Request-level analysis
    if requests and not request_id:
        print(f"\n📈 REQUEST ANALYSIS")
        request_durations = {}
        for req_id, logs in requests.items():
            total_duration = sum(l.get('duration_ms', 0) for l in logs if l.get('duration_ms'))
            if total_duration > 0:
                request_durations[req_id] = total_duration

        if request_durations:
            avg_duration = sum(request_durations.values()) / len(request_durations)
            print(f"  Average request duration: {avg_duration:.2f}ms")

            slowest = max(request_durations.items(), key=lambda x: x[1])
            print(f"  Slowest request: {slowest[0]}")
            print(f"    Total duration: {slowest[1]:.2f}ms")

    # Detailed request trace (if request_id provided)
    if request_id and request_id in requests:
        print(f"\n🔍 DETAILED REQUEST TRACE")
        print(f"Request ID: {request_id}")
        print("-" * 60)
        for log in sorted(requests[request_id], key=lambda x: x.get('timestamp', '')):
            event = log.get('event', 'unknown')
            timestamp = log.get('timestamp', '')
            duration = log.get('duration_ms')

            print(f"[{timestamp}] {event}", end="")
            if duration:
                print(f" ({duration:.2f}ms)", end="")
            print()

            # Print relevant details
            if event == 'llm_end':
                model = log.get('model')
                tokens = log.get('token_usage', {}).get('total_tokens')
                if model:
                    print(f"  Model: {model}")
                if tokens:
                    print(f"  Tokens: {tokens}")
            elif event == 'retriever_end':
                doc_count = log.get('document_count')
                sources = log.get('sources', [])
                if doc_count:
                    print(f"  Documents: {doc_count}")
                if sources:
                    print(f"  Sources: {', '.join(set(sources[:5]))}")
            elif event == 'chain_end':
                chain_name = log.get('chain_name')
                if chain_name:
                    print(f"  Chain: {chain_name}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python analyze_logs.py <log_file> [request_id]")
        print("       python analyze_logs.py - [request_id]  # Read from stdin")
        sys.exit(1)

    log_file = sys.argv[1]
    request_id = sys.argv[2] if len(sys.argv) > 2 else None

    analyze_logs(log_file, request_id)

