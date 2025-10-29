# 创建一个新的 triple_extractor.py 文件
import argparse
import json
import jsonlines
import logging
import os
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

from prompts import Prompts, Entity, Triple
from llm_model import VLLMModel
from tqdm import tqdm

class TripleExtractor:
    """
    Entity and triple extractor using LLM and structured output parsing.
    Input: jsonl file with text chunks.
    Output: entities and triples for knowledge graph construction.
    """
    
    def __init__(self, log_dir: str = "logs", log_level: int = logging.INFO):
        self.model = VLLMModel().get_local_model()
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self._setup_logger(log_level)
        
        self.prompt, self.parser = Prompts.get_triple_extraction_prompt()
        self.extraction_chain: RunnableSequence = self.prompt | self.model
        
    def _setup_logger(self, level: int):
        log_file = os.path.join(self.log_dir, "triple_extraction.log")
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler()
            ],
            force=True
        )
        self.logger = logging.getLogger(__name__)
    
    def _validate_and_fix_json(self, text: str) -> str:
        """验证并尝试修复 JSON 字符串"""
        fixes = [
            (r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16))),
            (r'\\([^"\\/bfnrtu])', r'\1'),
            (r'\\u([0-9a-fA-F]{0,3}[^0-9a-fA-F])', r'\\\\u\1'),
        ]
        
        fixed_text = text
        for pattern, replacement in fixes:
            if callable(replacement):
                fixed_text = re.sub(pattern, replacement, fixed_text)
            else:
                fixed_text = re.sub(pattern, replacement, fixed_text)
        
        return fixed_text
    
    def _cleaned_parser(self, raw_output: str, chunk_id: str) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Clean and parse raw LLM output to extract entities and triples.
        """
        # 1. Clean <think> and Markdown
        cleaned = re.sub(r"<think>.*?</think>", "", raw_output, flags=re.DOTALL)
        cleaned = re.sub(r"```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"```\s*$", "", cleaned)
        cleaned = cleaned.strip()
        
        if not cleaned:
            raise ValueError("Cleaned output is empty.")
        
        # 2. 尝试修复 JSON
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            self.logger.warning(f"First JSON parse failed for chunk {chunk_id}, attempting fixes...")
            cleaned = self._validate_and_fix_json(cleaned)
            
            try:
                data = json.loads(cleaned)
                self.logger.info(f"JSON fix successful for chunk {chunk_id}")
            except json.JSONDecodeError as e2:
                debug_dir = "debug_output"
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, f"chunk_{chunk_id}_error.json")
                
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                
                self.logger.error(f"JSON decoding error after fixes: {e2}")
                self.logger.error(f"Problematic JSON saved to: {debug_file}")
                return [], []
            
        if not isinstance(data, dict):
            raise ValueError("Parsed data is not a dict.")
        
        # 3. Validate entities and triples
        entities = []
        triples = []
        
        # 处理实体
        for item in data.get("entities", []):
            if not isinstance(item, dict):
                continue
            item["chunk_id"] = str(chunk_id)
            try:
                ent = Entity(**item)
                entities.append(ent.model_dump())
            except Exception as e:
                continue
        
        # 处理三元组
        for item in data.get("triples", []):
            if not isinstance(item, dict):
                continue
            item["chunk_id"] = str(chunk_id)
            try:
                tri = Triple(**item)
                triples.append(tri.model_dump())
            except Exception as e:
                continue
                
        return entities, triples
        
    def extract_entities_and_triples(
        self,
        input_file: str,
        output_dir: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract entities and triples from text chunks in the input JSONL file.
        
        Args:
            input_file (str): Path to the input JSONL file with text chunks.
            output_dir (Optional[str]): Directory to save the extracted entities and triples.
        """
        
        self.logger.info(f"Loading chunks from {input_file}")
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file {input_file} does not exist.")
        
        entity_kb: Dict[str, Dict[str, Any]] = {}
        triple_kb: List[Dict[str, Any]] = []
        
        with jsonlines.open(input_file, mode='r') as reader:
            chunks = list(reader)
        
        # 使用 tqdm 添加进度条
        for index, chunk in enumerate(tqdm(chunks, desc="Processing chunks", unit="chunk")):
            content = chunk.get("chunk_content", "").strip()
            meta_data = chunk.get("metadata", -1)
            source = chunk.get("source", "")
            
            if not content:
                self.logger.warning(f"Chunk {index} is empty, skipping.")
                continue
                
            raw_output = self.extraction_chain.invoke(
                {"text": content, "chunk_id": meta_data, "format_instructions": self.parser.get_format_instructions()}
            )
            
            cleaned_entities, cleaned_triples = self._cleaned_parser(raw_output.content, str(meta_data))
            self.logger.info(f"Chunk {index} extracted {len(cleaned_entities)} entities and {len(cleaned_triples)} triples.")
            
            # 处理实体
            for ent in cleaned_entities:
                key = ent["entity_name"]
                if key in entity_kb:
                    if ent["type"] not in entity_kb[key]["type"]:
                        entity_kb[key]["type"].append(ent["type"])
                    old_summary = entity_kb[key]["summary"]
                    new_summary = ent["summary"]
                    if old_summary != new_summary:
                        entity_kb[key]["summary"] = f"{old_summary} | {new_summary}".strip()
                    if meta_data not in entity_kb[key]["chunk_ids"]:
                        entity_kb[key]["chunk_ids"].append(meta_data)
                else:
                    entity_kb[key] = {
                        "entity_name": ent["entity_name"],
                        "type": [ent["type"]],
                        "summary": ent["summary"],
                        "chunk_ids": [meta_data],
                    }
            
            # 收集三元组
            triple_kb.extend(cleaned_triples)
            
            # 每处理完一个 chunk 就保存当前状态
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                entities_file = os.path.join(output_dir, f"entities_{index}.json")
                triples_file = os.path.join(output_dir, f"triples_{index}.json")
                
                current_entities = list(entity_kb.values())
                current_triples = list(triple_kb.values())
                
                with open(entities_file, "w", encoding="utf-8") as f:
                    json.dump(current_entities, f, ensure_ascii=False, indent=4)
                    
                with open(triples_file, "w", encoding="utf-8") as f:
                    json.dump(current_triples, f, ensure_ascii=False, indent=4)
        
        final_entities = list(entity_kb.values())
        final_triples = list(triple_kb.values())
        self.logger.info(f"Extracted total {len(final_entities)} unique entities and {len(triple_kb)} triples.")
        
        # 保存最终结果
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            final_entities_file = os.path.join(output_dir, "final_entities.json")
            final_triples_file = os.path.join(output_dir, "final_triples.json")
            
            with open(final_entities_file, "w", encoding="utf-8") as f:
                json.dump(final_entities, f, ensure_ascii=False, indent=4)
                
            with open(final_triples_file, "w", encoding="utf-8") as f:
                json.dump(triple_kb, f, ensure_ascii=False, indent=4)
        
        return final_entities, triple_kb
    
    # 在 TripleExtractor 类中添加以下方法

    def extract_entities_and_triples_range(
        self,
        input_file: str,
        output_dir: Optional[str] = None,
        start_index: int = 0,
        end_index: Optional[int] = None
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract entities and triples from a specified range of chunks in the input JSONL file.
        
        Args:
            input_file (str): Path to the input JSONL file with text chunks.
            output_dir (Optional[str]): Directory to save the extracted entities and triples.
            start_index (int): Starting chunk index (inclusive).
            end_index (Optional[int]): Ending chunk index (exclusive).
        """
        
        self.logger.info(f"Loading chunks from {input_file}")
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file {input_file} does not exist.")
        
        previous_entities_file = None
        previous_triples_file = None
        
        # 读取指定范围的chunks
        chunks = []
        with jsonlines.open(input_file, mode='r') as reader:
            for i, chunk in enumerate(reader):
                if i >= start_index:
                    if end_index is None or i < end_index:
                        chunks.append(chunk)
                    elif i >= end_index:
                        break
        
        if not chunks:
            self.logger.warning(f"No chunks found in range [{start_index}:{end_index}]")
            return [], []
        
        actual_end_index = start_index + len(chunks) - 1
        self.logger.info(f"Processing chunks from index {start_index} to {actual_end_index} (total: {len(chunks)} chunks)")
        
        # 初始化结果存储
        entity_kb: Dict[str, Dict[str, Any]] = {}
        triple_kb: List[Dict[str, Any]] = []
        
        # 处理chunks
        for index_in_range, chunk in enumerate(tqdm(chunks, desc=f"Processing chunks {start_index}-{actual_end_index}", unit="chunk")):
            global_index = start_index + index_in_range
            content = chunk.get("chunk_content", "").strip()
            meta_data = chunk.get("metadata", global_index)
            source = chunk.get("source", "")
            
            if not content:
                self.logger.warning(f"Chunk {global_index} is empty, skipping.")
                continue
                
            try:
                raw_output = self.extraction_chain.invoke(
                    {"text": content, "chunk_id": meta_data}
                )
                
                cleaned_entities, cleaned_triples = self._cleaned_parser(raw_output.content, str(meta_data))
                self.logger.info(f"Chunk {global_index} extracted {len(cleaned_entities)} entities and {len(cleaned_triples)} triples.")
                
                # 处理实体
                for ent in cleaned_entities:
                    key = ent["entity_name"]
                    if key in entity_kb:
                        if ent["type"] not in entity_kb[key]["type"]:
                            entity_kb[key]["type"].append(ent["type"])
                        old_summary = entity_kb[key]["summary"]
                        new_summary = ent["summary"]
                        if old_summary != new_summary:
                            entity_kb[key]["summary"] = f"{old_summary} | {new_summary}".strip()
                        if meta_data not in entity_kb[key]["chunk_ids"]:
                            entity_kb[key]["chunk_ids"].append(meta_data)
                    else:
                        entity_kb[key] = {
                            "entity_name": ent["entity_name"],
                            "type": [ent["type"]],
                            "summary": ent["summary"],
                            "chunk_ids": [meta_data],
                        }
                
                # 收集三元组
                triple_kb.extend(cleaned_triples)
                
                    
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    # 文件名格式：entities_起始索引_当前索引.json
                    current_entities_file = os.path.join(output_dir, f"entities_{start_index}_{global_index}.json")
                    current_triples_file = os.path.join(output_dir, f"triples_{start_index}_{global_index}.json")
                    
                    current_entities = list(entity_kb.values())
                    current_triples = triple_kb[:]  # 创建副本
                    
                    with open(current_entities_file, "w", encoding="utf-8") as f:
                        json.dump(current_entities, f, ensure_ascii=False, indent=4)
                        
                    with open(current_triples_file, "w", encoding="utf-8") as f:
                        json.dump(current_triples, f, ensure_ascii=False, indent=4)
                        
                    # 删除上一个保存的文件
                    if previous_entities_file and os.path.exists(previous_entities_file):
                        os.remove(previous_entities_file)
                        self.logger.debug(f"Removed previous entities file: {previous_entities_file}")
                    if previous_triples_file and os.path.exists(previous_triples_file):
                        os.remove(previous_triples_file)
                        self.logger.debug(f"Removed previous triples file: {previous_triples_file}")
                    
                    # 更新previous文件名
                    previous_entities_file = current_entities_file
                    previous_triples_file = current_triples_file
                    self.logger.debug(f"Saved current results to {current_entities_file} and {current_triples_file}")
                
            except Exception as e:
                self.logger.error(f"Error processing chunk {global_index}: {e}")
                continue
        
        final_entities = list(entity_kb.values())
        self.logger.info(f"Extracted total {len(final_entities)} unique entities and {len(triple_kb)} triples from chunks {start_index}-{actual_end_index}.")
        
        # 保存结果，文件名包含处理的chunk范围
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            entities_file = os.path.join(output_dir, f"entities_{start_index}_{actual_end_index}.json")
            triples_file = os.path.join(output_dir, f"triples_{start_index}_{actual_end_index}.json")
            
            # 保存实体
            with open(entities_file, "w", encoding="utf-8") as f:
                json.dump(final_entities, f, ensure_ascii=False, indent=4)
                
            # 保存三元组
            with open(triples_file, "w", encoding="utf-8") as f:
                json.dump(triple_kb, f, ensure_ascii=False, indent=4)
        
        return final_entities, triple_kb

    # 添加一个辅助方法用于获取文件总行数
    def get_total_chunks(self, input_file: str) -> int:
        """
        Get the total number of chunks in the input file.
        
        Args:
            input_file (str): Path to the input JSONL file.
            
        Returns:
            int: Total number of chunks.
        """
        count = 0
        with jsonlines.open(input_file, mode='r') as reader:
            for _ in reader:
                count += 1
        return count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract entities and triples from text chunks')
    parser.add_argument('--start', type=int, default=156, help='Start chunk index (inclusive)')
    parser.add_argument('--end', type=int, default=157, help='End chunk index (exclusive)')
    parser.add_argument('--input_file', type=str, default="./chunks_output/chunks.jsonl", 
                       help='Input JSONL file path')
    parser.add_argument('--output_dir', type=str, default="./kg_output", 
                       help='Output directory path')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
    
    args = parser.parse_args()
    
    extractor = TripleExtractor(log_level=logging.INFO)

    extractor = TripleExtractor(log_level=logging.INFO)

    # 如果没有指定end参数，则处理从start开始的batch-size个chunks
    if args.end is None:
        args.end = args.start + args.batch_size
    
    entities, triples = extractor.extract_entities_and_triples_range(
        input_file=args.input_file,
        output_dir=args.output_dir,
        start_index=args.start,
        end_index=args.end
    )
    
    extractor.logger.info(f"Entity and triple extraction completed for chunks {args.start}-{args.end-1}.")
    extractor.logger.info(f"Extracted {len(entities)} entities and {len(triples)} triples.")