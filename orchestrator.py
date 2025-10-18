#!/usr/bin/env python3
"""
Better-LLM Orchestrator CLI

Group chat orchestration system with Manager and Worker agents.

Usage:
    python orchestrator.py "task description"
    python orchestrator.py --verbose "task description"
    python orchestrator.py --config custom_config.json "task"
"""

from src.presentation.cli.orchestrator import main

if __name__ == "__main__":
    main()
