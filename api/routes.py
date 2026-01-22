"""API路由定义"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field, validator

from agents.orchestrator import get_orchestrator
from shared.schemas import DiscoverResponse, VerifyResponse, VerificationData
from shared.constants import Discipline, RelationType, AgentConfig
from shared.error_codes import ErrorCode, get_error_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent接口"])


# ==================== 请求模型定义 ====================

class DiscoverRequest(BaseModel):
    """概念挖掘请求"""
    concept: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="核心概念词",
        example="熵"
    )
    disciplines: Optional[List[str]] = Field(
        default=None,
        description="目标学科列表",
        example=["数学", "物理", "信息论"]
    )
    depth: int = Field(
        default=AgentConfig.DEFAULT_DEPTH,
        ge=1,
        le=3,
        description="挖掘深度",
        example=2
    )
    max_concepts: int = Field(
        default=AgentConfig.DEFAULT_MAX_CONCEPTS,
        ge=10,
        le=100,
        description="最大概念数",
        example=30
    )
    enable_verification: bool = Field(
        default=True,
        description="是否启用知识校验",
        example=True
    )
    
    @validator('disciplines')
    def validate_disciplines(cls, v):
        """验证学科列表"""
        if v is None:
            return None
        
        # 检查是否全部为空字符串
        if all(not d.strip() for d in v):
            raise ValueError("学科列表不能全部为空")
        
        # 允许任意学科名称（包括细分学科如"信息论"），由Agent内部处理
        # 但保留标准学科的推荐提示
        non_standard = [d for d in v if d not in Discipline.ALL]
        if non_standard:
            logger.debug(f"使用非标准学科: {non_standard}，推荐使用: {Discipline.ALL}")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "concept": "熵",
                "disciplines": ["数学", "物理", "信息论", "机器学习"],
                "depth": 2,
                "max_concepts": 30,
                "enable_verification": True
            }
        }


class VerifyRequest(BaseModel):
    """概念验证请求"""
    concept_a: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="概念A",
        example="熵"
    )
    concept_b: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="概念B",
        example="信息增益"
    )
    claimed_relation: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="声称的关联描述",
        example="信息增益基于熵的概念"
    )
    strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="声称的关联强度",
        example=0.8
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "concept_a": "熵",
                "concept_b": "信息增益",
                "claimed_relation": "信息增益基于熵的概念，用于度量信息的期望减少量",
                "strength": 0.8
            }
        }


class ExpandRequest(BaseModel):
    """图谱扩展请求"""
    node_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="要扩展的节点ID",
        example="entropy_xinxilun"
    )
    existing_graph: dict = Field(
        ...,
        description="现有图谱数据",
        example={
            "nodes": [{"id": "entropy_xinxilun", "label": "熵"}],
            "edges": []
        }
    )
    disciplines: Optional[List[str]] = Field(
        default=None,
        description="限定扩展的学科",
        example=["计算机", "数学"]
    )
    max_new_nodes: int = Field(
        default=10,
        ge=1,
        le=50,
        description="最多新增节点数",
        example=10
    )
    
    @validator('disciplines')
    def validate_disciplines(cls, v):
        """验证学科列表"""
        if v is None:
            return None
        
        invalid_disciplines = [d for d in v if d not in Discipline.ALL]
        if invalid_disciplines:
            raise ValueError(f"无效的学科: {invalid_disciplines}")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "entropy_xinxilun",
                "existing_graph": {
                    "nodes": [
                        {
                            "id": "entropy_xinxilun",
                            "label": "熵",
                            "discipline": "信息论",
                            "definition": "信息的不确定性度量",
                            "credibility": 0.95
                        }
                    ],
                    "edges": []
                },
                "disciplines": ["计算机", "数学"],
                "max_new_nodes": 10
            }
        }


# ==================== API接口实现 ====================

@router.post(
    "/discover",
    response_model=DiscoverResponse,
    summary="概念挖掘接口",
    description="在多个学科领域自动发现与核心概念相关的跨学科概念",
    response_description="包含节点、边和元数据的知识图谱"
)
async def discover_concepts(request: DiscoverRequest = Body(...)):
    """
    概念挖掘接口
    
    执行完整的跨学科概念挖掘流程：
    1. 在指定学科中搜索相关概念
    2. 验证概念关联的准确性（可选）
    3. 构建知识图谱并返回
    
    Args:
        request: 挖掘请求参数
        
    Returns:
        DiscoverResponse: 包含图谱数据的响应
        
    Raises:
        HTTPException: 当处理失败时
    """
    try:
        logger.info(f"📥 Discover request: concept={request.concept}, depth={request.depth}")
        
        # 获取编排器
        orchestrator = get_orchestrator()
        
        # 执行挖掘
        response = await orchestrator.discover(
            concept=request.concept,
            disciplines=request.disciplines,
            depth=request.depth,
            max_concepts=request.max_concepts,
            enable_verification=request.enable_verification
        )
        
        logger.info(
            f"✅ Discover complete: {response.data.metadata.total_nodes if response.data else 0} nodes, "
            f"{response.data.metadata.total_edges if response.data else 0} edges"
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "error_code": ErrorCode.VALIDATION_ERROR,
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"❌ Discovery failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": ErrorCode.LLM_API_ERROR,
                "message": get_error_message(ErrorCode.LLM_API_ERROR),
                "details": str(e)
            }
        )


@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="概念验证接口",
    description="验证两个概念之间的关联是否真实可靠",
    response_description="包含可信度评分和证据的验证结果"
)
async def verify_concept_relation(request: VerifyRequest = Body(...)):
    """
    概念验证接口
    
    验证两个概念之间的关联关系：
    1. 通过多源数据验证关联的真实性
    2. 计算可信度评分
    3. 提供证据链接
    
    Args:
        request: 验证请求参数
        
    Returns:
        VerifyResponse: 包含验证结果的响应
        
    Raises:
        HTTPException: 当验证失败时
    """
    try:
        logger.info(
            f"📥 Verify request: {request.concept_a} <-> {request.concept_b}"
        )
        
        # 获取编排器
        orchestrator = get_orchestrator()
        
        # 执行验证
        result = await orchestrator.verify(
            concept_a=request.concept_a,
            concept_b=request.concept_b,
            claimed_relation=request.claimed_relation,
            strength=request.strength
        )
        
        if result["status"] == "error":
            logger.warning(f"⚠️ Verification failed: {result.get('message')}")
            raise HTTPException(
                status_code=400,
                detail={
                    "status": "error",
                    "error_code": result.get("error_code", ErrorCode.VERIFICATION_FAILED),
                    "message": result.get("message")
                }
            )
        
        # 构建响应
        verification_data = result["data"]
        
        # 转换evidence格式
        evidence_list = []
        for ev in verification_data.get("evidence", []):
            # 兼容不同的evidence格式
            if isinstance(ev, dict):
                # 从Evidence对象的to_dict()输出转换为API Schema格式
                source_type = ev.get("source_type", "Unknown")
                source_name = ev.get("source_name", "")
                
                # 构造source字段：source_type (source_name)
                if source_name:
                    source = f"{source_type} ({source_name})"
                else:
                    source = source_type
                
                evidence_list.append({
                    "source": source,
                    "url": ev.get("url") or "",  # None转为空字符串
                    "snippet": ev.get("content", "")[:500]  # 限制长度
                })
        
        response = VerifyResponse(
            status="success",
            request_id=result.get("request_id"),
            data=VerificationData(
                credibility_score=verification_data.get("credibility_score", 0.0),
                is_valid=verification_data.get("is_valid", False),
                evidence=evidence_list,
                warnings=verification_data.get("warnings", [])
            )
        )
        
        logger.info(
            f"✅ Verify complete: credibility={response.data.credibility_score:.2f}, "
            f"valid={response.data.is_valid}"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": ErrorCode.VERIFICATION_FAILED,
                "message": get_error_message(ErrorCode.VERIFICATION_FAILED),
                "details": str(e)
            }
        )


@router.post(
    "/expand",
    response_model=dict,
    summary="图谱扩展接口",
    description="扩展现有图谱中的指定节点，发现更多相关概念",
    response_description="包含新增节点和边的扩展图谱"
)
async def expand_graph(request: ExpandRequest = Body(...)):
    """
    图谱扩展接口
    
    扩展现有图谱中的指定节点：
    1. 发现该节点的相关概念
    2. 验证新概念的可靠性
    3. 将新节点和边添加到现有图谱
    
    Args:
        request: 扩展请求参数
        
    Returns:
        dict: 扩展后的完整图谱
        
    Raises:
        HTTPException: 当扩展失败时
    """
    try:
        logger.info(f"📥 Expand request: node_id={request.node_id}")
        
        # 获取编排器
        orchestrator = get_orchestrator()
        
        # 执行扩展
        expanded_graph = await orchestrator.expand(
            node_id=request.node_id,
            existing_graph=request.existing_graph,
            disciplines=request.disciplines,
            max_new_nodes=request.max_new_nodes
        )
        
        new_nodes_count = len(expanded_graph.get("nodes", [])) - len(
            request.existing_graph.get("nodes", [])
        )
        
        logger.info(f"✅ Expand complete: {new_nodes_count} new nodes added")
        
        return {
            "status": "success",
            "data": expanded_graph
        }
        
    except ValueError as e:
        logger.error(f"❌ Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "error_code": ErrorCode.CONCEPT_NOT_FOUND,
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"❌ Expansion failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error_code": ErrorCode.LLM_API_ERROR,
                "message": get_error_message(ErrorCode.LLM_API_ERROR),
                "details": str(e)
            }
        )


# ==================== 辅助接口 ====================

@router.get(
    "/disciplines",
    summary="获取支持的学科列表",
    description="返回系统支持的所有学科类别"
)
async def get_disciplines():
    """获取支持的学科列表"""
    return {
        "status": "success",
        "data": {
            "disciplines": Discipline.ALL,
            "colors": Discipline.COLORS
        }
    }


@router.get(
    "/relations",
    summary="获取关系类型列表",
    description="返回系统支持的所有关系类型"
)
async def get_relation_types():
    """获取关系类型列表"""
    return {
        "status": "success",
        "data": {
            "types": RelationType.ALL,
            "descriptions": RelationType.DESCRIPTIONS
        }
    }
