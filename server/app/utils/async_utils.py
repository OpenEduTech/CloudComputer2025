"""
PatPat-Inconsistency-Hunter 异步工具模块
提供异步并行执行等工具函数
"""

import asyncio
from typing import Any, Callable, List, TypeVar, Optional
from tqdm.asyncio import tqdm as async_tqdm

from .logger import logger

T = TypeVar("T")


async def run_async_in_parallel(
    async_function: Callable[..., T],
    *iterables,
    max_concurrency: int = 5,
    timeout: float = 3600,
    desc: str = "",
    show_progress: bool = True,
) -> List[Optional[T]]:
    """
    并行执行异步函数
    
    Args:
        async_function: 要执行的异步函数
        *iterables: 参数迭代器
        max_concurrency: 最大并发数
        timeout: 超时时间（秒）
        desc: 进度条描述
        show_progress: 是否显示进度条
    
    Returns:
        结果列表
    """
    if not iterables:
        return []
    
    length = len(iterables[0])
    for it in iterables:
        if len(it) != length:
            raise ValueError("所有迭代器必须具有相同的长度")
    
    # 创建任务队列
    queue: asyncio.Queue = asyncio.Queue()
    for index, args in enumerate(zip(*iterables)):
        await queue.put((index, args))
    
    results: List[Optional[T]] = [None] * length
    finished_count = 0
    
    # 创建进度条
    pbar = async_tqdm(
        total=length,
        desc=desc,
        disable=not (desc and show_progress),
    )
    
    async def worker():
        nonlocal finished_count
        while True:
            try:
                index, args = await asyncio.wait_for(
                    queue.get(), 
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                if queue.empty():
                    break
                continue
            except asyncio.CancelledError:
                break
            
            try:
                result = await asyncio.wait_for(
                    async_function(*args),
                    timeout=timeout,
                )
                results[index] = result
            except asyncio.TimeoutError:
                logger.warning(f"任务 {index} 超时")
                results[index] = None
            except Exception as e:
                logger.error(f"任务 {index} 执行失败: {e}")
                results[index] = None
            finally:
                finished_count += 1
                pbar.update(1)
                queue.task_done()
    
    # 启动工作协程
    workers = [asyncio.create_task(worker()) for _ in range(max_concurrency)]
    
    # 等待所有任务完成
    await queue.join()
    
    # 取消工作协程
    for w in workers:
        w.cancel()
    
    pbar.close()
    
    return results


async def retry_async(
    async_function: Callable[..., T],
    *args,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    **kwargs,
) -> T:
    """
    带重试的异步函数执行
    
    Args:
        async_function: 要执行的异步函数
        *args: 位置参数
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避因子
        **kwargs: 关键字参数
    
    Returns:
        函数返回值
    
    Raises:
        最后一次失败的异常
    """
    last_exception = None
    current_delay = delay
    
    for attempt in range(max_retries + 1):
        try:
            return await async_function(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    f"第 {attempt + 1} 次尝试失败: {e}, "
                    f"{current_delay:.1f}秒后重试..."
                )
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                logger.error(f"所有重试都失败了: {e}")
    
    raise last_exception


async def gather_with_concurrency(
    tasks: List[Callable[[], T]],
    max_concurrency: int = 5,
) -> List[T]:
    """
    带并发限制的任务收集
    
    Args:
        tasks: 任务列表（每个任务是一个无参数的协程函数）
        max_concurrency: 最大并发数
    
    Returns:
        结果列表
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def limited_task(task_func):
        async with semaphore:
            return await task_func()
    
    return await asyncio.gather(
        *[limited_task(task) for task in tasks],
        return_exceptions=True,
    )

