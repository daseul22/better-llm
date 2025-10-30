#!/bin/bash

# Git untracked 파일 정리 스크립트

echo "=== Git Untracked 파일 정리 ==="
echo ""

# 삭제될 파일 미리보기
echo "다음 파일들이 삭제됩니다:"
git clean -fd --dry-run

echo ""
read -p "정말 삭제하시겠습니까? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    git clean -fd
    echo "✓ 정리 완료"
else
    echo "✗ 취소됨"
fi
