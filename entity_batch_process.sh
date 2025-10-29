#!/bin/bash

# batch_process.sh - 分批处理chunks的脚本

# 配置参数
INPUT_FILE="./chunks_output/chunks.jsonl"
OUTPUT_DIR="./entities_output"
BATCH_SIZE=20
START_INDEX=0

# 获取总chunk数
echo "Getting total number of chunks..."
TOTAL_CHUNKS=$(wc -l < "$INPUT_FILE")
echo "Total chunks: $TOTAL_CHUNKS"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 计算需要处理的批次数
TOTAL_BATCHES=$(( (TOTAL_CHUNKS + BATCH_SIZE - 1) / BATCH_SIZE ))
echo "Total batches to process: $TOTAL_BATCHES"

# 分批处理
batch_num=1
for ((start=$START_INDEX; start<TOTAL_CHUNKS; start+=BATCH_SIZE)); do
    end=$((start + BATCH_SIZE))
    if [ $end -gt $TOTAL_CHUNKS ]; then
        end=$TOTAL_CHUNKS
    fi
    
    echo "========================================"
    echo "Processing batch $batch_num of $TOTAL_BATCHES"
    echo "Chunks: $start to $((end-1))"
    echo "========================================"
    
    # 运行Python脚本
    python get_entities.py --start $start --end $end --input_file "$INPUT_FILE" --output_dir "$OUTPUT_DIR"
    
    if [ $? -eq 0 ]; then
        echo "✓ Batch $batch_num completed successfully"
    else
        echo "✗ Error in batch $batch_num"
        echo "Continuing with next batch..."
    fi
    
    batch_num=$((batch_num + 1))
    
    # 添加延迟避免过载
    sleep 2
done

echo "========================================"
echo "Batch processing completed!"
echo "Results saved to: $OUTPUT_DIR"
echo "========================================"