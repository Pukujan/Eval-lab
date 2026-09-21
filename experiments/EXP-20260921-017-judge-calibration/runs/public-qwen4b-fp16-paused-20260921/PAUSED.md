# Paused pre-optimization checkpoint

This directory contains an interrupted, pre-optimization Qwen 4B public run.
It produced `182/648` raw predictions with the unquantized float16 runtime,
4,096-token cap, and no quantization metadata. It must not be resumed or merged
with the later 4-bit run because that would mix runtime configurations.

The run was paused after the user reported excessive GPU memory use. The
authoritative optimized run uses a separate output directory with 4-bit NF4
double quantization, float16 compute, a 2,048-token cap, and a 0.8 per-process
CUDA memory fraction.
