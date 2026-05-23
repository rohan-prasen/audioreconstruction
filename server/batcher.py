from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import torch

logger = logging.getLogger("audioreconstruction")

MAX_BATCH_SIZE = 8
MAX_WAIT_S = 0.25


@dataclass
class SegmentRequest:
    tensor: torch.Tensor
    future: asyncio.Future


class InferenceBatcher:
    def __init__(
        self,
        generator: torch.nn.Module,
        device: torch.device,
        *,
        max_batch: int = MAX_BATCH_SIZE,
        max_wait_s: float = MAX_WAIT_S,
    ) -> None:
        self._generator = generator
        self._device = device
        self._max_batch = max_batch
        self._max_wait_s = max_wait_s
        self._queue: asyncio.Queue[SegmentRequest | None] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        await self._queue.put(None)
        try:
            await asyncio.wait_for(self._task, timeout=10.0)
        except asyncio.TimeoutError:
            self._task.cancel()

    async def submit(self, segment: torch.Tensor) -> torch.Tensor:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        await self._queue.put(SegmentRequest(tensor=segment, future=future))
        return await future

    async def _worker_loop(self) -> None:
        while True:
            first = await self._queue.get()
            if first is None:
                break

            batch: list[SegmentRequest] = [first]
            deadline = asyncio.get_event_loop().time() + self._max_wait_s

            while len(batch) < self._max_batch:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                try:
                    item = await asyncio.wait_for(
                        self._queue.get(), timeout=remaining
                    )
                    if item is None:
                        break
                    batch.append(item)
                except asyncio.TimeoutError:
                    break

            await self._process_batch(batch)

    async def _process_batch(self, batch: list[SegmentRequest]) -> None:
        actual_size = len(batch)
        logger.info("Processing batch of %d segment(s)", actual_size)

        inputs = torch.stack([req.tensor for req in batch])
        if actual_size < self._max_batch:
            padding = torch.zeros(
                self._max_batch - actual_size,
                *inputs.shape[1:],
                dtype=inputs.dtype,
            )
            inputs = torch.cat([inputs, padding], dim=0)

        inputs = inputs.to(self._device)

        try:
            loop = asyncio.get_running_loop()
            outputs = await loop.run_in_executor(None, self._gpu_forward, inputs)

            for i, req in enumerate(batch):
                if not req.future.cancelled():
                    req.future.set_result(outputs[i].cpu())
        except Exception as exc:
            logger.error("Batch inference failed: %s", exc)
            for req in batch:
                if not req.future.done():
                    req.future.set_exception(exc)
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        finally:
            del inputs

    @torch.inference_mode()
    def _gpu_forward(self, inp: torch.Tensor) -> torch.Tensor:
        with torch.amp.autocast("cuda", enabled=self._device.type == "cuda"):
            return self._generator(inp)
