# get_relations.py
# 专门用于从已提取的实体中抽取关系三元组

import argparse
import json
import jsonlines
import logging
import os
import re
import ahocorasick
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence

from prompts import Prompts, Triple
from llm_model import VLLMModel
from tqdm import tqdm
from ac_automaton import ACEntityMatcher

class RelationExtractor:
    """
    Relation extractor using LLM and structured output parsing.
    Input: jsonl file with text chunks and existing entities.
    Output: triples for knowledge graph construction.
    """
    
    def __init__(self, log_dir: str = "logs", log_level: int = logging.INFO, entities_file: str="./kg_output/entities_kb.json"):
        self.model = VLLMModel().get_local_model()
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self._setup_logger(log_level)
        
        self.prompt, self.parser = Prompts.get_relation_extraction_prompt()
        self.extraction_chain: RunnableSequence = self.prompt | self.model
        
        self.entity_matcher = ACEntityMatcher(entities_file=entities_file)
        
        
    def _setup_logger(self, level: int):
        log_file = os.path.join(self.log_dir, "relation_extraction.log")
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
    
    def _cleaned_parser(self, raw_output: str, chunk_id: str) -> List[Dict[str, Any]]:
        """
        Clean and parse raw LLM output to extract triples only.
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
                debug_file = os.path.join(debug_dir, f"relation_chunk_{chunk_id}_error.json")
                
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                
                self.logger.error(f"JSON decoding error after fixes: {e2}")
                self.logger.error(f"Problematic JSON saved to: {debug_file}")
                return []
            
        if not isinstance(data, dict):
            raise ValueError("Parsed data is not a dict.")
        
        # 3. Validate triples only
        triples = []
        
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
                
        return triples
    
    def extract_relations_from_range(
        self,
        input_file: str,
        entities_file: str,
        output_dir: Optional[str] = None,
        start_index: int = 0,
        end_index: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract triples from a specified range of chunks using pre-extracted entities.
        
        Args:
            input_file (str): Path to the input JSONL file with text chunks.
            entities_file (str): Path to the JSON file with pre-extracted entities.
            output_dir (Optional[str]): Directory to save the extracted triples.
            start_index (int): Starting chunk index (inclusive).
            end_index (Optional[int]): Ending chunk index (exclusive).
        """
        
        self.logger.info(f"Loading chunks from {input_file}")
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file {input_file} does not exist.")
            
        self.logger.info(f"Loading entities from {entities_file}")
        if not os.path.exists(entities_file):
            raise FileNotFoundError(f"Entities file {entities_file} does not exist.")
        
        # 加载预提取的实体
        with open(entities_file, "r", encoding="utf-8") as f:
            entities_data = json.load(f)
        
        # 创建实体字典以便快速查找
        entity_dict = {entity["entity_name"]: entity for entity in entities_data}
        self.logger.info(f"Loaded {len(entity_dict)} entities for relation extraction")
        
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
            return []
        
        actual_end_index = start_index + len(chunks) - 1
        self.logger.info(f"Processing chunks from index {start_index} to {actual_end_index} (total: {len(chunks)} chunks)")
        
        # 初始化结果存储
        triple_kb: List[Dict[str, Any]] = []
        
        # 处理chunks
        for index_in_range, chunk in enumerate(tqdm(chunks, desc=f"Processing chunks {start_index}-{actual_end_index} for relations", unit="chunk")):
            global_index = start_index + index_in_range
            content = chunk.get("chunk_content", "").strip()
            meta_data = chunk.get("metadata", global_index)
            source = chunk.get("source", "")
            
            if not content:
                self.logger.warning(f"Chunk {global_index} is empty, skipping.")
                continue
                
            try:
                entities_data = self.entity_matcher.match_entities(content)
                self.logger.info(f"Chunk {global_index} matched {len(entities_data)} entities.")
                
                raw_output = self.extraction_chain.invoke(
                    {"text": content, "chunk_id": meta_data, "entities": entities_data}
                )
                
                cleaned_triples = self._cleaned_parser(raw_output.content, str(meta_data))
                self.logger.info(f"Chunk {global_index} extracted {len(cleaned_triples)} triples.")
                
                # 收集三元组
                triple_kb.extend(cleaned_triples)
                
                # 保存中间结果
                if output_dir:
                    os.makedirs(output_dir, exist_ok=True)
                    current_triples_file = os.path.join(output_dir, f"triples_{start_index}_{global_index}.json")
                    
                    with open(current_triples_file, "w", encoding="utf-8") as f:
                        json.dump(triple_kb, f, ensure_ascii=False, indent=4)
                        
                    # 删除上一个保存的文件
                    if previous_triples_file and os.path.exists(previous_triples_file):
                        os.remove(previous_triples_file)
                        self.logger.debug(f"Removed previous triples file: {previous_triples_file}")
                    
                    # 更新previous文件名
                    previous_triples_file = current_triples_file
                    self.logger.debug(f"Saved current results to {current_triples_file}")
                
            except Exception as e:
                self.logger.error(f"Error processing chunk {global_index}: {e}")
                continue
        
        self.logger.info(f"Extracted total {len(triple_kb)} triples from chunks {start_index}-{actual_end_index}.")
        
        # 保存结果，文件名包含处理的chunk范围
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            triples_file = os.path.join(output_dir, f"triples_{start_index}_{actual_end_index}.json")
            
            with open(triples_file, "w", encoding="utf-8") as f:
                json.dump(triple_kb, f, ensure_ascii=False, indent=4)
        
        return triple_kb

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract relations (triples) from text chunks using pre-extracted entities')
    parser.add_argument('--start', type=int, default=0, help='Start chunk index (inclusive)')
    parser.add_argument('--end', type=int, default=1, help='End chunk index (exclusive)')
    parser.add_argument('--input_file', type=str, default="./chunks_output/relation_chunks.jsonl", 
                       help='Input JSONL file path')
    parser.add_argument('--entities_file', type=str, default="./kg_output/entities_kb.json",
                       help='Path to pre-extracted entities JSON file')
    parser.add_argument('--output_dir', type=str, default="./triplets_output", 
                       help='Output directory path')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for processing')
    
    args = parser.parse_args()
    
    extractor = RelationExtractor(log_level=logging.INFO, entities_file=args.entities_file)

    # 如果没有指定end参数，则处理从start开始的batch-size个chunks
    if args.end is None:
        args.end = args.start + args.batch_size
    
    triples = extractor.extract_relations_from_range(
        input_file=args.input_file,
        entities_file=args.entities_file,
        output_dir=args.output_dir,
        start_index=args.start,
        end_index=args.end
    )
    
    extractor.logger.info(f"Relation extraction completed for chunks {args.start}-{args.end-1}.")
    extractor.logger.info(f"Extracted {len(triples)} triples.")