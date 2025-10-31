#!/bin/bash

# Git ignored 파일 정리 스크립트 (.gitignore 파일만 대상)
# macOS (Bash 3.2) 호환

echo "=== .gitignore 파일 정리 (__pycache__, .venv 등) ==="
echo ""

# 삭제 대상 파일 목록 가져오기 (macOS 호환)
files=()
while IFS= read -r line; do
    files+=("$line")
done < <(git clean -fdX --dry-run | sed 's/Would remove //')

# 파일이 없으면 종료
if [ ${#files[@]} -eq 0 ]; then
    echo "✓ 정리할 파일이 없습니다."
    exit 0
fi

# 파일 목록 출력
echo "다음 파일/디렉토리가 삭제됩니다:"
echo ""
for i in "${!files[@]}"; do
    printf "%3d) %s\n" $((i+1)) "${files[$i]}"
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "제외할 항목 번호를 입력하세요 (쉼표 또는 공백으로 구분)"
echo "예: 1,3,5  또는  1 3 5"
echo "모두 삭제하려면 그냥 엔터를 누르세요"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "제외할 번호: " exclude_input

# 제외 목록 파싱 (공백으로 구분된 인덱스 문자열로 저장)
exclude_list=" "
if [ -n "$exclude_input" ]; then
    # 쉼표를 공백으로 변환
    exclude_input=$(echo "$exclude_input" | tr ',' ' ')
    for num in $exclude_input; do
        if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "${#files[@]}" ]; then
            exclude_list="${exclude_list}$((num-1)) "
        else
            echo "⚠ 경고: 잘못된 번호 '$num' (무시됨)"
        fi
    done
fi

# 삭제할 파일 목록 생성
to_delete=()
to_keep=()
for i in "${!files[@]}"; do
    # 제외 목록에 현재 인덱스가 있는지 확인
    if [[ "$exclude_list" == *" $i "* ]]; then
        to_keep+=("${files[$i]}")
    else
        to_delete+=("${files[$i]}")
    fi
done

# 제외된 파일 표시
if [ ${#to_keep[@]} -gt 0 ]; then
    echo ""
    echo "제외된 항목 (삭제하지 않음):"
    for file in "${to_keep[@]}"; do
        echo "  ✓ $file"
    done
fi

# 삭제할 파일이 없으면 종료
if [ ${#to_delete[@]} -eq 0 ]; then
    echo ""
    echo "✗ 삭제할 파일이 없습니다."
    exit 0
fi

# 최종 확인
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "삭제할 항목 (${#to_delete[@]}개):"
for file in "${to_delete[@]}"; do
    echo "  × $file"
done
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "정말 삭제하시겠습니까? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 파일 삭제
    for file in "${to_delete[@]}"; do
        rm -rf "$file"
        echo "  삭제: $file"
    done
    echo ""
    echo "✓ 정리 완료 (${#to_delete[@]}개 항목 삭제)"
else
    echo "✗ 취소됨"
fi
