import re
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, JsonOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional

# =========================
# 1.Use Pydantic model to define structured output
# =========================

# ===========(1)Entity Extraction==============
class Entity(BaseModel):
    entity_name: str = Field(description="实体的标准名称，使用原文术语，避免同义词或缩写")
    type: str = Field(description="实体类型，包括但不限于 '工具', '材料', '焊接工艺', '装配流程', '部件' 等")
    domain_relevance: str = Field(description="实体的领域相关性，取值为 'domain_specific' 或 'general'")
    summary: str = Field(description="详细说明实体的功能、作用、结构特点、使用条件等信息（如有），基于原文内容")
    chunk_id: str = Field(description="文本块的序号符")
    
class EntityList(BaseModel):
    entities: List[Entity] = Field(description="从文本中抽取到的实体列表")

class Triple(BaseModel):
    subject: str = Field(description="三元组的主体实体名称")
    relation: str = Field(description="三元组的关系类型，如'包含','使用','属于','作用于'等")
    object: str = Field(description="三元组的客体实体名称")
    chunk_id: str = Field(description="文本块的序号符")
    
class Relation(BaseModel):
    triples: List[Triple] = Field(description="从文本中抽取到的关系三元组列表")

class EntityWithTriples(BaseModel):
    entities: List[Entity] = Field(description="从文本中抽取到的实体列表")
    triples: List[Triple] = Field(description="从文本中抽取到的三元组列表")


class QwenSafeJsonParser(PydanticOutputParser):
    def parse(self, text: str) -> dict:
        # 移除 <think> 标签
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        cleaned = cleaned.strip()
        # 移除可能的 Markdown 代码块
        if cleaned.startswith("```"):
            cleaned = re.split(r"```(?:json)?", cleaned)[-1].rstrip("` \n")
        return super().parse(cleaned)

class QwenSafeJsonParserWithTriples(QwenSafeJsonParser):
    def parse(self, text: str) -> dict:
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        cleaned = cleaned.strip()
        if cleaned.startswith("```"):
            cleaned = re.split(r"```(?:json)?", cleaned)[-1].rstrip("` \n")
        return super().parse(cleaned)      

# =========================
# 2.Construct PromptTemplate with outputParser
# ========================= 

def _make_entity_extraction_prompt() -> tuple[PromptTemplate, QwenSafeJsonParser]:
    parser = QwenSafeJsonParser(pydantic_object=EntityList)
    
    entity_template = """
    你是一名船舶制造与设计领域的资深知识工程师。请严格从以下文本中抽取出**与船舶设计、建造、工艺、材料、装配、检验、设备、标准等直接相关的实体**。

    ### 抽取原则
    1. 尽可能抽取领域强相关实体，例如：
    - 部件：舭龙骨、舷侧外板、肋骨、舱口围板
    - 工艺：单面焊双面成形、分段建造法、密性试验、壳舾涂一体化
    - 材料：高强度钢、耐腐蚀涂层
    - 设备：液压千斤顶、数控等离子切割机
    - 标准/机构：中国船级社（CCS）、DNV规范（仅当涉及技术要求时）
    
    2. 每个实体为一个字典，键包括五个参数：entity_name, type, domain_relevance, summary, chunk_id。
    其中domain_relevance取值为：
    "domain_specific":船舶建造、涂装等相关工程专业实体；
    "general":表示通用实体，如“船舶”这类词汇，或者“作者信息”、“国家信息”等较为粗粒度的实体；
    
    3. 每个实体的 summary 必须：
    - **严格基于原文上下文**，不得自行编造或泛化；
    - **尽可能详实、具体**，包含其功能、作用、结构特点、使用条件等原文提及的信息；
    - 若原文未说明作用，则 summary 可为“原文中提及的[类型]”，但优先使用原文描述。
    
    4. 每个实体的表述尽可能准确，如“龙骨”和“龙骨组成”这两个实体，请使用“龙骨”作为实体，“龙骨组成”作为其描述，不要拆分成两个实体

    5. 对于类似以下内容，明确为general类型的实体，并且根据是否与船舶制造设计工艺强相关决定是否抽取
    - 具体技术含义的通用词（如“公司”“方法”“过程”）
    - 类似作者、出版社、章节标题、版本信息（如“第7版”）
    - 类似泛化地理名词（如“日本”“欧洲”），除非文本明确说明其与船舶技术相关（如“日本JIS标准”）
   
    ### 正确示例
    {{
        [
            {{
                "entity_name": "舭龙骨",
                "type": "材料部件",
                "domain_relevance": "domain_specific",
                "summary": "安装在船底舭部的纵向构件，用于提高船舶横摇阻尼，减少摇摆幅度。",
                "chunk_id": "11"
            }},
            {{
                "entity_name": "单面焊双面成形",
                "type": "工艺流程",
                "domain_relevance": "domain_specific",
                "summary": "一种焊接工艺，仅从钢板单侧施焊，即可在背面形成均匀成形的焊缝，常用于船体密性结构。",
                "chunk_id": "24"  
            }}   
        ]

    }}

    请按照示例格式严格输出为json文件。现在处理以下文本（chunk_id: {chunk_id}）：{text} /no think
    """.strip()   
    prompt = PromptTemplate(
        template=entity_template,
        input_variables=["text", "chunk_id"],
        partial_variables={"format_instructions":parser.get_format_instructions()}
    )
    
    return prompt, parser

def _make_relation_extraction_prompt() -> tuple[PromptTemplate, QwenSafeJsonParser]:
    parser = QwenSafeJsonParser(pydantic_object=Relation)
    relation_template = """
    你是一名船舶制造领域的知识工程师。请从给定的船舶设计建造相关文本中抽取出所有**实体间的关系三元组**, 其中实体尽量从下面的列表中选择：{entities}。
    
    ## 抽取规则是：
    1. **领域聚焦**：只抽取与船舶设计、建造、工艺直接相关的实体
    2. **实体具体**：确保实体都是具体且有明确含义的专有名词
    3. **关系准确**：严格符合关系定义，不确定时舍弃该三元组
    4. **避免泛化**：不抽取定义性、常识性陈述
    5. **价值导向**：确保三元组能提供有价值的领域知识

    ## 你需要抽取的关系用如下英文单词表示：
    ### 核心层级关系
    - **contains** (整体包含部分) 示例：船体结构 contains 外板
    - **part_of** (部分属于整体) 示例：舵系统 part_of 操纵系统  
    - **belongs_to** (下位概念属于上位概念) 示例：散货船 belongs_to 商船
    
    ### 设计过程关系
    - **precedes** (阶段先后顺序) 示例：放样 precedes 号料
    - **inputs** (设计输入依赖) 示例：结构设计 inputs 总体布置图
    - **outputs** (设计输出成果) 示例：线型设计 outputs 型线图
    - **refines** (设计细化关系) 示例：生产设计 refines 详细设计

    ### 工艺技术关系
    - **uses** (主体使用工具材料) 示例：装配工 uses 定位夹具, 焊接 uses 焊条
    - **applied_to** (方法工艺应用于场景) 示例：单面焊双面成形 applied_to 钢板拼接
    - **acts_on** (工艺操作作用于对象) 示例：焊接 acts_on 钢板, 切割 acts_on 型材
    - **improves** (技术改进效果) 示例：激光焊接 improves 焊接质量
    - **replaces** (技术替代关系) 示例：机器人焊接 replaces 手工焊接
    - **enables** (技术支持关系) 示例：CAD软件 enables 三维设计

    ### 结构性能关系
    - **has** (主体拥有属性特征) 示例：船体 has 结构强度
    - **affects** (因素影响关系) 示例：结构重量 affects 船舶稳性
    - **determines** (参数决定关系) 示例：主尺度 determines 载重量
    - **constrained_by** (约束限制关系) 示例：船宽 constrained_by 航道条件
    - **connects_to** (部件连接关系) 示例：甲板 connects_to 舷侧
    - **supports** (结构支撑关系) 示例：肋骨 supports 外板, 纵桁 supports 甲板

    ### 建造流程关系
    - **produces** (过程产生结果) 示例：分段制作 produces 船体分段
    - **located_at** (实体位于位置) 示例：舾装 located_at 船台, 涂装 located_at 涂装车间
    - **assembles_into** (组装成关系) 示例：零件 assembles_into 分段, 分段 assembles_into 总段
    - **prepares_for** (准备工作关系) 示例：钢材预处理 prepares_for 零件加工
    - **tests_with** (测试验证关系) 示例：密性试验 tests_with 压力检测
    
    ## 负面示例（避免抽取）
    - "企业 uses 先进技术"（过于泛化）
    - "方法 applied_to 过程"（实体不具体）
    - "技术 improves 效率"（缺乏具体性）

    ## 输出格式要求
    请以JSON格式输出结果，里面包括一个"triples"字段，该字段是一个列表，列表中的元素是三元组，三元组结构如下：
    {{
        [
            {{
                "subject": "商船",
                "relation": "has",
                "object": "排水量",
                "chunk_id": [{chunk_id}]
            }}
        ]
    }}
    
    {format_instructions}
    提供的知识文档为：{text} /no think
    """.strip()
    
    prompt = PromptTemplate(
        template=relation_template,
        input_variables=["text", "chunk_id", "entities"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    return prompt, parser
    
def _make_triple_extraction_prompt() -> tuple[PromptTemplate, QwenSafeJsonParserWithTriples]:
    parser = QwenSafeJsonParserWithTriples(pydantic_object=EntityWithTriples)
    triple_template = """
    你是一名船舶制造领域的知识工程师。请从以下文本中抽取出所有**重要实体**和**实体间的关系三元组**。

    实体可以是任何在船舶制造领域中有意义的对象、概念、过程或角色，包括但不限于：
    - 工具设备：如千斤顶、风动角向砂轮等
    - 材料部件：如钢板、焊缝等
    - 工艺流程：如钢板拼接、定位焊、单面焊双面成形等
    - 操作步骤：具体的操作方法或步骤
    - 装配阶段：整体装配的不同阶段
    - 人员角色：参与制造过程的各种角色
    - 质量标准：衡量产品质量的标准或规范
    - 安全措施：生产过程中需要注意的安全要点
    
    关系类型（使用英文标识符）及正确使用示例：
    - "contains"：整体 contains 部分（如：船舶设计 contains 概念设计）
    - "belongs_to"：下位概念 belongs_to 上位概念（如：散货船 belongs_to 商船）
    - "uses"：主体 uses 工具/材料（如：工人 uses 焊接设备）
    - "has"：主体 has 属性/特征（如：商船 has 排水量）
    - "applied_to"：方法/工艺 applied_to 场景（如：单面焊双面成形 applied_to 钢板拼接）
    - "acts_on"：工艺/操作 acts_on 对象（如：焊接 acts_on 钢板）
    - "located_at"：实体 located_at 位置（如：舾装 located_at 船台）
    - "produces"：过程 produces 结果（如：船舶建造 produces 商船）
    - "part_of"：部分 part_of 整体（如：概念设计 part_of 船舶设计）

    输出要求：
    1. 先提取实体，包括：entity_name, type, summary, chunk_id
    2. 再提取三元组：subject, predicate, object, chunk_id
    3. 严格按照JSON格式输出，不要额外文字
    4. 关系方向必须符合语义逻辑

    正确示例：
    {{
        "entities": [
            {{
                "entity_name": "商船", 
                "type": "船舶类型", 
                "summary": "用于商业运输的船舶。", 
                "chunk_id": "{chunk_id}"
            }}
        ],
        "triples": [
            {{
                "subject": "商船",
                "predicate": "has",
                "object": "排水量",
                "chunk_id": "{chunk_id}"
            }}
        ]
    }} 
    {format_instructions}
    
    现在处理以下文本(chunk_id: {chunk_id})：{text} /no think
    """.strip()
    
    prompt = PromptTemplate(
        template=triple_template,
        input_variables=["text", "chunk_id"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    return prompt, parser


# =========================
# 3. Unified Access Interface: Prompts Namespace Class
# ========================= 

class Prompts:
    """A collection of prompt templates and parsers for various tasks."""

    @staticmethod
    def get_entity_extraction_prompt() -> tuple[PromptTemplate, QwenSafeJsonParser]:
        """Prompt and parser for entity extraction task."""
        return _make_entity_extraction_prompt()
    
    @staticmethod
    def get_relation_extraction_prompt() -> tuple[PromptTemplate, QwenSafeJsonParser]:
        """Prompt and parser for relation extraction task."""
        return _make_relation_extraction_prompt()
    
    @staticmethod
    def get_triple_extraction_prompt() -> tuple[PromptTemplate, QwenSafeJsonParserWithTriples]:
        """Prompt and parser for entity and triple extraction task."""
        return _make_triple_extraction_prompt()

    