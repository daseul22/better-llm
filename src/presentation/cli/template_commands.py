"""
템플릿 관리 CLI 명령어

템플릿 목록, 적용, 생성, 검색 등의 CLI 명령어를 제공합니다.
"""

import json
import click
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint

from application.use_cases.template_management import (
    ListTemplatesUseCase,
    ApplyTemplateUseCase,
    CreateTemplateUseCase,
    SearchTemplatesUseCase
)
from domain.models.template import (
    Template,
    TemplateCategory,
    TemplateVariable,
    TemplateFile,
    VariableType,
    TemplateNotFoundError,
    TemplateValidationError
)
from infrastructure.template import (
    FileBasedTemplateRepository,
    Jinja2TemplateEngine,
    get_builtin_templates
)

console = Console()


def get_template_repository() -> FileBasedTemplateRepository:
    """템플릿 리포지토리 생성"""
    return FileBasedTemplateRepository()


def get_template_engine() -> Jinja2TemplateEngine:
    """템플릿 엔진 생성"""
    return Jinja2TemplateEngine()


@click.group(name="template")
def template_commands():
    """템플릿 관리 명령어"""
    pass


@template_commands.command(name="list")
@click.option("--category", "-c", help="카테고리 필터")
@click.option("--tags", "-t", multiple=True, help="태그 필터 (여러 개 지정 가능)")
def list_templates(category: Optional[str], tags: tuple):
    """
    템플릿 목록 조회

    저장된 템플릿들의 목록을 표시합니다.

    Args:
        category: 카테고리 필터 (web_api, testing, database, frontend 등)
        tags: 태그 필터 (여러 개 지정 가능)

    Examples:
        template list
        template list --category web_api
        template list --tags fastapi --tags crud
    """
    try:
        # Use Case 생성
        repo = get_template_repository()
        use_case = ListTemplatesUseCase(repo)

        # 카테고리 변환
        category_enum = None
        if category:
            try:
                category_enum = TemplateCategory(category)
            except ValueError:
                console.print(f"[red]잘못된 카테고리입니다: {category}[/red]")
                console.print(f"사용 가능한 카테고리: {', '.join([c.value for c in TemplateCategory])}")
                raise click.Abort()

        # 템플릿 조회
        tag_list = list(tags) if tags else None
        templates = use_case.execute(category=category_enum, tags=tag_list)

        if not templates:
            console.print("[yellow]조회된 템플릿이 없습니다.[/yellow]")
            return

        # 테이블 생성
        table = Table(title=f"템플릿 목록 (총 {len(templates)}건)")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("이름", style="green")
        table.add_column("카테고리", style="magenta")
        table.add_column("설명", style="white")
        table.add_column("태그", style="yellow")

        for template in templates:
            table.add_row(
                template.id,
                template.name,
                template.category.value,
                template.description[:50] + ("..." if len(template.description) > 50 else ""),
                ", ".join(template.tags[:3]) + ("..." if len(template.tags) > 3 else "")
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]템플릿 목록 조회 실패: {e}[/red]")
        raise click.Abort()


@template_commands.command(name="show")
@click.argument("template_id")
def show_template(template_id: str):
    """
    템플릿 상세 정보 조회

    특정 템플릿의 상세 정보를 표시합니다.

    Args:
        template_id: 템플릿 ID

    Examples:
        template show fastapi-crud
        template show pytest-test
    """
    try:
        # 리포지토리 생성
        repo = get_template_repository()

        # 템플릿 조회
        template = repo.get(template_id)

        if not template:
            console.print(f"[red]템플릿을 찾을 수 없습니다: {template_id}[/red]")
            raise click.Abort()

        # 템플릿 정보 표시
        info_text = f"""
[cyan]ID:[/cyan] {template.id}
[cyan]이름:[/cyan] {template.name}
[cyan]설명:[/cyan] {template.description}
[cyan]카테고리:[/cyan] {template.category.value}
[cyan]태그:[/cyan] {', '.join(template.tags)}
[cyan]파일 수:[/cyan] {len(template.files)}
"""
        console.print(Panel(info_text.strip(), title="템플릿 정보", border_style="blue"))

        # 변수 정보 표시
        if template.variables:
            console.print("\n[bold]템플릿 변수[/bold]\n")
            var_table = Table()
            var_table.add_column("변수명", style="cyan")
            var_table.add_column("타입", style="yellow")
            var_table.add_column("필수", style="magenta")
            var_table.add_column("기본값", style="green")
            var_table.add_column("설명", style="white")

            for var in template.variables:
                var_table.add_row(
                    var.name,
                    var.type.value,
                    "✓" if var.required else "",
                    str(var.default) if var.default is not None else "",
                    var.description
                )

            console.print(var_table)

        # 파일 정보 표시
        if template.files:
            console.print("\n[bold]생성될 파일[/bold]\n")
            for file in template.files:
                console.print(f"  • {file.path}")

    except Exception as e:
        console.print(f"[red]템플릿 조회 실패: {e}[/red]")
        raise click.Abort()


@template_commands.command(name="apply")
@click.argument("template_id")
@click.option("--output", "-o", default=".", help="출력 디렉토리 (기본값: 현재 디렉토리)")
@click.option("--var", "-v", multiple=True, help="템플릿 변수 (key=value 형식)")
@click.option("--interactive", "-i", is_flag=True, help="대화형 모드")
def apply_template(template_id: str, output: str, var: tuple, interactive: bool):
    """
    템플릿 적용

    템플릿을 렌더링하여 파일을 생성합니다.

    Args:
        template_id: 템플릿 ID
        output: 출력 디렉토리
        var: 템플릿 변수 (key=value 형식, 여러 개 지정 가능)
        interactive: 대화형 모드 사용 여부

    Examples:
        template apply fastapi-crud -v entity_name=user -v entity_name_plural=users
        template apply pytest-test --output tests/ -v module_name=auth
        template apply react-component --interactive
    """
    try:
        # Use Case 생성
        repo = get_template_repository()
        engine = get_template_engine()
        use_case = ApplyTemplateUseCase(repo, engine)

        # 템플릿 조회
        template = repo.get(template_id)
        if not template:
            console.print(f"[red]템플릿을 찾을 수 없습니다: {template_id}[/red]")
            raise click.Abort()

        # 변수 수집
        variables = {}

        # 1. --var 옵션에서 변수 파싱
        for var_str in var:
            if "=" not in var_str:
                console.print(f"[red]잘못된 변수 형식: {var_str} (key=value 형식이어야 합니다)[/red]")
                raise click.Abort()

            key, value = var_str.split("=", 1)
            variables[key.strip()] = value.strip()

        # 2. 대화형 모드: 누락된 필수 변수 입력받기
        if interactive:
            for template_var in template.variables:
                if template_var.name not in variables:
                    default_str = f" (기본값: {template_var.default})" if template_var.default else ""
                    required_str = " [필수]" if template_var.required else ""

                    # LIST 타입일 때 입력 안내 추가
                    if template_var.type == VariableType.LIST:
                        console.print(f"\n[dim]  (JSON 배열 또는 콤마로 구분: [\"a\",\"b\"] or a,b)[/dim]")

                    value = Prompt.ask(
                        f"{template_var.description}{required_str}{default_str}",
                        default=str(template_var.default) if template_var.default else ""
                    )

                    if value:
                        # 타입 변환
                        if template_var.type == VariableType.INTEGER:
                            variables[template_var.name] = int(value)
                        elif template_var.type == VariableType.BOOLEAN:
                            variables[template_var.name] = value.lower() in ["true", "yes", "1"]
                        elif template_var.type == VariableType.LIST:
                            # JSON 리스트 파싱 시도 (예: '["id", "name"]')
                            if value.startswith("[") and value.endswith("]"):
                                try:
                                    variables[template_var.name] = json.loads(value)
                                except json.JSONDecodeError:
                                    # JSON 파싱 실패 시 콤마로 split
                                    variables[template_var.name] = [v.strip() for v in value.split(",")]
                            else:
                                # JSON 형식이 아니면 콤마로 split
                                variables[template_var.name] = [v.strip() for v in value.split(",")]
                        else:
                            variables[template_var.name] = value

        # 출력 디렉토리 표시
        output_path = Path(output).resolve()
        console.print(f"\n[cyan]템플릿:[/cyan] {template.name}")
        console.print(f"[cyan]출력 경로:[/cyan] {output_path}")
        console.print(f"[cyan]변수:[/cyan] {json.dumps(variables, ensure_ascii=False, indent=2)}")

        # 확인
        if not Confirm.ask("\n템플릿을 적용하시겠습니까?"):
            console.print("[yellow]취소되었습니다.[/yellow]")
            return

        # 템플릿 적용
        created_files = use_case.execute(
            template_id=template_id,
            variables=variables,
            output_dir=output_path
        )

        # 결과 표시
        console.print(f"\n[green]✓ 템플릿 적용 완료: {len(created_files)}개 파일 생성[/green]\n")
        for file_path in created_files:
            console.print(f"  • {file_path}")

    except TemplateNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise click.Abort()
    except TemplateValidationError as e:
        console.print(f"[red]변수 검증 실패:[/red]\n{e}")
        raise click.Abort()
    except ValueError as e:
        console.print(f"[red]입력값 오류: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]템플릿 적용 실패: {e}[/red]")
        raise click.Abort()


@template_commands.command(name="search")
@click.argument("query")
def search_templates(query: str):
    """
    템플릿 검색

    키워드로 템플릿을 검색합니다.

    Args:
        query: 검색 쿼리 (이름, 설명, 태그에서 검색)

    Examples:
        template search fastapi
        template search test
        template search react
    """
    try:
        # Use Case 생성
        repo = get_template_repository()
        use_case = SearchTemplatesUseCase(repo)

        # 검색 실행
        templates = use_case.execute(query)

        if not templates:
            console.print(f"[yellow]'{query}'에 대한 검색 결과가 없습니다.[/yellow]")
            return

        # 테이블 생성
        table = Table(title=f"검색 결과: '{query}' (총 {len(templates)}건)")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("이름", style="green")
        table.add_column("카테고리", style="magenta")
        table.add_column("설명", style="white")

        for template in templates:
            table.add_row(
                template.id,
                template.name,
                template.category.value,
                template.description[:60] + ("..." if len(template.description) > 60 else "")
            )

        console.print(table)

    except ValueError as e:
        console.print(f"[red]입력값 오류: {e}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]검색 실패: {e}[/red]")
        raise click.Abort()


@template_commands.command(name="init")
@click.option("--force", "-f", is_flag=True, help="기존 템플릿 덮어쓰기")
def init_builtin_templates(force: bool):
    """
    내장 템플릿 초기화

    Built-in 템플릿들을 저장소에 추가합니다.

    Args:
        force: True면 기존 템플릿 덮어쓰기

    Examples:
        template init
        template init --force
    """
    try:
        # 리포지토리 생성
        repo = get_template_repository()
        use_case = CreateTemplateUseCase(repo)

        # Built-in 템플릿 가져오기
        builtin_templates = get_builtin_templates()

        console.print(f"\n[cyan]내장 템플릿 초기화: {len(builtin_templates)}개[/cyan]\n")

        saved_count = 0
        skipped_count = 0

        for template in builtin_templates:
            # 기존 템플릿 확인
            existing = repo.get(template.id)

            if existing and not force:
                console.print(f"  [yellow]⊘ {template.id} (이미 존재, 건너뜀)[/yellow]")
                skipped_count += 1
                continue

            # 템플릿 저장
            use_case.execute(template)
            console.print(f"  [green]✓ {template.id}[/green]")
            saved_count += 1

        console.print(f"\n[green]완료: {saved_count}개 저장, {skipped_count}개 건너뜀[/green]")

        if skipped_count > 0:
            console.print("[yellow]기존 템플릿을 덮어쓰려면 --force 옵션을 사용하세요.[/yellow]")

    except Exception as e:
        console.print(f"[red]내장 템플릿 초기화 실패: {e}[/red]")
        raise click.Abort()
