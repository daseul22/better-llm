#!/usr/bin/env python3
"""
Better LLM - 그룹 챗 오케스트레이션 시스템 v4.0
Setup script for package installation
"""

import os
from setuptools import setup, find_packages

# Read README file for long description
def read_file(filename):
    """Read file contents."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""

# Read requirements from requirements.txt
def read_requirements():
    """Read requirements from requirements.txt."""
    requirements = []
    try:
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    requirements.append(line)
    except FileNotFoundError:
        pass
    return requirements

setup(
    name="better-llm",
    version="4.0.0",
    author="Better LLM Team",
    author_email="dev@better-llm.org",
    description="그룹 챗 오케스트레이션 시스템 - Manager Agent가 전문화된 Worker Agent들을 조율하여 복잡한 소프트웨어 개발 작업을 자동화",
    long_description=read_file("README.md") or "Better LLM - AI-powered software development orchestration system",
    long_description_content_type="text/markdown",
    url="https://github.com/better-llm/better-llm",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "": [
            "config/*.json",
            "prompts/*.txt",
            "*.md",
        ],
    },
    data_files=[
        ("config", ["config/agent_config.json", "config/system_config.json"]),
        ("prompts", [
            "prompts/planner.txt",
            "prompts/coder.txt", 
            "prompts/reviewer.txt",
            "prompts/tester.txt",
            "prompts/committer.txt",
            "prompts/ideator.txt",
            "prompts/product_manager.txt"
        ]),
    ],
    entry_points={
        "console_scripts": [
            "better-llm=presentation.cli.orchestrator_cli:main",
            "better-llm-tui=presentation.tui.tui_app:main",
        ],
    },
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.0.0",
            "mkdocstrings[python]>=0.24.0",
            "pymdown-extensions>=10.0.0",
        ],
    },
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Code Generators",
        "Operating System :: OS Independent",
    ],
    keywords="ai, llm, agent, orchestration, software-development, automation, claude, anthropic",
    project_urls={
        "Bug Reports": "https://github.com/better-llm/better-llm/issues",
        "Source": "https://github.com/better-llm/better-llm",
        "Documentation": "https://better-llm.readthedocs.io/",
    },
)