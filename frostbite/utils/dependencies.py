from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any, Callable, cast

from fastapi.background import BackgroundTasks
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import (
    get_dependant,
    is_async_gen_callable,
    is_coroutine_callable,
    is_gen_callable,
    solve_generator,
)
from starlette.background import BackgroundTasks as StarletteBackgroundTasks
from starlette.concurrency import run_in_threadpool


@dataclass
class SolvedDependency:
    values: dict[str, Any]
    errors: list[Any]
    background_tasks: StarletteBackgroundTasks | None
    dependency_cache: dict[tuple[Callable[..., Any], tuple[str]], Any]


async def solve_dependencies(
    *,
    dependant: Dependant,
    dependency_overrides: Any | None = None,
    dependency_cache: dict[tuple[Callable[..., Any], tuple[str]], Any] | None = None,
    background_tasks: StarletteBackgroundTasks | None = None,
    async_exit_stack: AsyncExitStack,
) -> SolvedDependency:
    values: dict[str, Any] = {}
    errors: list[Any] = []
    dependency_cache = dependency_cache or {}
    sub_dependant: Dependant
    for sub_dependant in dependant.dependencies:
        sub_dependant.call = cast(Callable[..., Any], sub_dependant.call)
        sub_dependant.cache_key = cast(
            tuple[Callable[..., Any], tuple[str]], sub_dependant.cache_key
        )
        call = sub_dependant.call
        use_sub_dependant = sub_dependant
        if dependency_overrides:
            original_call = sub_dependant.call
            call = (dependency_overrides or {}).get(original_call, original_call)
            use_path: str = sub_dependant.path  # type: ignore
            use_sub_dependant = get_dependant(
                path=use_path,
                call=call,
                name=sub_dependant.name,
                security_scopes=sub_dependant.security_scopes,
            )

        solved_result = await solve_dependencies(
            dependant=use_sub_dependant,
            dependency_overrides=dependency_overrides,
            dependency_cache=dependency_cache,
            async_exit_stack=async_exit_stack,
        )
        background_tasks = solved_result.background_tasks
        dependency_cache.update(solved_result.dependency_cache)
        if solved_result.errors:
            errors.extend(solved_result.errors)
            continue
        if sub_dependant.use_cache and sub_dependant.cache_key in dependency_cache:
            solved = dependency_cache[sub_dependant.cache_key]
        elif is_gen_callable(call) or is_async_gen_callable(call):
            solved = await solve_generator(
                call=call, stack=async_exit_stack, sub_values=solved_result.values
            )
        elif is_coroutine_callable(call):
            solved = await call(**solved_result.values)
        else:
            solved = await run_in_threadpool(call, **solved_result.values)
        if sub_dependant.name is not None:
            values[sub_dependant.name] = solved
        if sub_dependant.cache_key not in dependency_cache:
            dependency_cache[sub_dependant.cache_key] = solved
    if dependant.background_tasks_param_name:
        if background_tasks is None:
            background_tasks = BackgroundTasks()
        values[dependant.background_tasks_param_name] = background_tasks
    return SolvedDependency(
        values=values,
        errors=errors,
        background_tasks=background_tasks,
        dependency_cache=dependency_cache,
    )
