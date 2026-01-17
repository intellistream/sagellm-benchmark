# Benchmark Results

## Overall Statistics

- **Total Workloads**: 3
- **Total Requests**: 18
- **Successful**: 17
- **Failed**: 1

## Workload Details

| Workload | Requests | Errors | Avg TTFT (ms) | Throughput (tok/s) |
|----------|----------|--------|---------------|---------------------|
| short_input | 5 | 0 | 10.00 | 100.00 |
| long_input | 3 | 0 | 15.00 | 75.00 |
| stress_test | 10 | 1 | 12.00 | 90.00 |

## Detailed Metrics

### short_input

- **TTFT**: avg=10.00ms, p50=10.00ms, p95=10.00ms, p99=10.00ms
- **TBT**: avg=5.00ms
- **TPOT**: avg=5.00ms
- **Throughput**: avg=100.00 tok/s
- **Memory**: peak=1024 MB, avg=512.00 MB
- **Error Rate**: 0.00%
- **KV Cache**: 640 tokens, 81920 bytes
- **Prefix Hit Rate**: 0.00%
- **Evictions**: 0 (0.00ms)
- **Spec Accept Rate**: 0.00%

### long_input

- **TTFT**: avg=15.00ms, p50=15.00ms, p95=15.00ms, p99=15.00ms
- **TBT**: avg=8.00ms
- **TPOT**: avg=8.00ms
- **Throughput**: avg=75.00 tok/s
- **Memory**: peak=2048 MB, avg=1024.00 MB
- **Error Rate**: 0.00%
- **KV Cache**: 600 tokens, 76800 bytes
- **Prefix Hit Rate**: 0.00%
- **Evictions**: 0 (0.00ms)
- **Spec Accept Rate**: 0.00%

### stress_test

- **TTFT**: avg=12.00ms, p50=12.00ms, p95=18.00ms, p99=20.00ms
- **TBT**: avg=6.00ms
- **TPOT**: avg=6.00ms
- **Throughput**: avg=90.00 tok/s
- **Memory**: peak=4096 MB, avg=2048.00 MB
- **Error Rate**: 10.00%
- **KV Cache**: 2304 tokens, 294912 bytes
- **Prefix Hit Rate**: 0.00%
- **Evictions**: 2 (3.50ms)
- **Spec Accept Rate**: 0.00%

## Analysis

### Performance Summary

- **Best TTFT**: short_input (10.00ms)
- **Best Throughput**: short_input (100.00 tok/s)
- **Highest Memory**: stress_test (4096 MB)

### Reliability

- Overall success rate: 94.44% (17/18 requests)
- Stress test error rate: 10.00% (acceptable under pressure)

### Resource Usage

- Total KV cache usage: 3544 tokens (453632 bytes)
- Peak memory across all workloads: 4096 MB

## Conclusion

This benchmark run validates the Year 1 Demo Contract requirements:
- ✓ Short input workload completed successfully
- ✓ Long input workload completed successfully
- ✓ Stress test completed with expected error handling
- ✓ All required metrics collected and reported

The system demonstrates acceptable performance and reliability under the specified workloads.
