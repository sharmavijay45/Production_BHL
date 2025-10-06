#!/usr/bin/env python3
"""
Explainability Module - Structured Reasoning and Decision Tracking
=================================================================

Provides structured explainability JSON for agent decisions, reasoning traces,
and decision justification for alerts, scores, and recommendations.
"""

import uuid
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from utils.logger import get_logger

logger = get_logger(__name__)

class ReasoningType(Enum):
    """Types of reasoning steps"""
    ANALYSIS = "analysis"
    INFERENCE = "inference"
    COMPARISON = "comparison"
    CLASSIFICATION = "classification"
    RECOMMENDATION = "recommendation"
    VALIDATION = "validation"
    ESCALATION = "escalation"

class ConfidenceLevel(Enum):
    """Confidence levels for decisions"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class DecisionType(Enum):
    """Types of decisions"""
    ROUTING = "routing"
    CLASSIFICATION = "classification"
    SCORING = "scoring"
    ALERTING = "alerting"
    ESCALATION = "escalation"
    RECOMMENDATION = "recommendation"

@dataclass
class ReasoningStep:
    """Individual reasoning step"""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int = 0
    reasoning_type: ReasoningType = ReasoningType.ANALYSIS
    description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "reasoning_type": self.reasoning_type.value,
            "description": self.description,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "assumptions": self.assumptions,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class Decision:
    """Decision with justification"""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_type: DecisionType = DecisionType.CLASSIFICATION
    decision: str = ""
    confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    justification: str = ""
    alternatives_considered: List[Dict[str, Any]] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    mitigating_factors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
            "decision": self.decision,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "justification": self.justification,
            "alternatives_considered": self.alternatives_considered,
            "risk_factors": self.risk_factors,
            "mitigating_factors": self.mitigating_factors,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class ExplainabilityTrace:
    """Complete explainability trace"""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    query: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    reasoning_steps: List[ReasoningStep] = field(default_factory=list)
    final_decision: Optional[Decision] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "query": self.query,
            "context": self.context,
            "reasoning_steps": [step.to_dict() for step in self.reasoning_steps],
            "final_decision": self.final_decision.to_dict() if self.final_decision else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_steps": len(self.reasoning_steps),
            "average_confidence": self._calculate_average_confidence()
        }
    
    def _calculate_average_confidence(self) -> float:
        """Calculate average confidence across all steps"""
        if not self.reasoning_steps:
            return 0.0
        
        total_confidence = sum(step.confidence for step in self.reasoning_steps)
        return total_confidence / len(self.reasoning_steps)

class ExplainabilityEngine:
    """Engine for generating structured explainability"""
    
    def __init__(self):
        self.engine_name = "ExplainabilityEngine"
        self.version = "1.0.0"
        
        # Storage for traces
        self.traces: Dict[str, ExplainabilityTrace] = {}
        
        logger.info("✅ Explainability Engine initialized")
    
    def create_trace(self, agent_name: str, query: str, context: Dict[str, Any] = None) -> str:
        """Create new explainability trace"""
        trace = ExplainabilityTrace(
            agent_name=agent_name,
            query=query,
            context=context or {}
        )
        
        self.traces[trace.trace_id] = trace
        
        logger.info(f"📊 Created explainability trace: {trace.trace_id}")
        return trace.trace_id
    
    def add_reasoning_step(self, trace_id: str, step_data: Dict[str, Any]) -> bool:
        """Add reasoning step to trace"""
        try:
            if trace_id not in self.traces:
                logger.error(f"❌ Trace {trace_id} not found")
                return False
            
            trace = self.traces[trace_id]
            
            step = ReasoningStep(
                step_number=len(trace.reasoning_steps) + 1,
                reasoning_type=ReasoningType(step_data.get("reasoning_type", "analysis")),
                description=step_data.get("description", ""),
                input_data=step_data.get("input_data", {}),
                output_data=step_data.get("output_data", {}),
                confidence=step_data.get("confidence", 0.0),
                evidence=step_data.get("evidence", []),
                assumptions=step_data.get("assumptions", [])
            )
            
            trace.reasoning_steps.append(step)
            
            logger.info(f"📝 Added reasoning step {step.step_number} to trace {trace_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add reasoning step: {str(e)}")
            return False
    
    def add_decision(self, trace_id: str, decision_data: Dict[str, Any]) -> bool:
        """Add final decision to trace"""
        try:
            if trace_id not in self.traces:
                logger.error(f"❌ Trace {trace_id} not found")
                return False
            
            trace = self.traces[trace_id]
            
            decision = Decision(
                decision_type=DecisionType(decision_data.get("decision_type", "classification")),
                decision=decision_data.get("decision", ""),
                confidence=decision_data.get("confidence", 0.0),
                confidence_level=self._map_confidence_to_level(decision_data.get("confidence", 0.0)),
                justification=decision_data.get("justification", ""),
                alternatives_considered=decision_data.get("alternatives_considered", []),
                risk_factors=decision_data.get("risk_factors", []),
                mitigating_factors=decision_data.get("mitigating_factors", [])
            )
            
            trace.final_decision = decision
            trace.completed_at = datetime.utcnow()
            
            logger.info(f"✅ Added final decision to trace {trace_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add decision: {str(e)}")
            return False
    
    def _map_confidence_to_level(self, confidence: float) -> ConfidenceLevel:
        """Map confidence score to level"""
        if confidence >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.7:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get explainability trace"""
        trace = self.traces.get(trace_id)
        return trace.to_dict() if trace else None
    
    def get_traces_by_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        """Get traces by agent"""
        return [
            trace.to_dict() 
            for trace in self.traces.values() 
            if trace.agent_name == agent_name
        ]
    
    def generate_explanation_summary(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Generate human-readable explanation summary"""
        trace = self.traces.get(trace_id)
        if not trace:
            return None
        
        try:
            # Build reasoning chain
            reasoning_chain = []
            for step in trace.reasoning_steps:
                reasoning_chain.append({
                    "step": step.step_number,
                    "action": step.reasoning_type.value,
                    "description": step.description,
                    "confidence": step.confidence,
                    "key_evidence": step.evidence[:3] if step.evidence else []
                })
            
            # Build decision summary
            decision_summary = None
            if trace.final_decision:
                decision_summary = {
                    "decision": trace.final_decision.decision,
                    "confidence": trace.final_decision.confidence,
                    "confidence_level": trace.final_decision.confidence_level.value,
                    "justification": trace.final_decision.justification,
                    "key_risks": trace.final_decision.risk_factors[:3] if trace.final_decision.risk_factors else [],
                    "alternatives": len(trace.final_decision.alternatives_considered)
                }
            
            return {
                "trace_id": trace_id,
                "agent": trace.agent_name,
                "query": trace.query,
                "reasoning_chain": reasoning_chain,
                "decision_summary": decision_summary,
                "overall_confidence": trace._calculate_average_confidence(),
                "total_reasoning_steps": len(trace.reasoning_steps),
                "processing_time_seconds": (
                    (trace.completed_at - trace.created_at).total_seconds() 
                    if trace.completed_at else None
                ),
                "explanation_generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate explanation summary: {str(e)}")
            return None
    
    def create_alert_explanation(self, alert_data: Dict[str, Any], 
                               reasoning_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create structured explanation for alerts"""
        trace_id = self.create_trace("AlertSystem", alert_data.get("description", "Alert generated"))
        
        # Add reasoning steps
        for step_data in reasoning_steps:
            self.add_reasoning_step(trace_id, step_data)
        
        # Add decision
        decision_data = {
            "decision_type": "alerting",
            "decision": f"Generate {alert_data.get('priority', 'medium')} priority alert",
            "confidence": alert_data.get("confidence", 0.8),
            "justification": alert_data.get("justification", "Alert criteria met"),
            "risk_factors": alert_data.get("risk_factors", []),
            "mitigating_factors": alert_data.get("mitigating_factors", [])
        }
        self.add_decision(trace_id, decision_data)
        
        return {
            "alert_explanation": self.get_trace(trace_id),
            "summary": self.generate_explanation_summary(trace_id)
        }
    
    def create_scoring_explanation(self, score_data: Dict[str, Any], 
                                 factors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create structured explanation for scoring decisions"""
        trace_id = self.create_trace("ScoringSystem", f"Score calculation: {score_data.get('score', 0)}")
        
        # Add factor analysis steps
        for i, factor in enumerate(factors, 1):
            step_data = {
                "reasoning_type": "analysis",
                "description": f"Factor {i}: {factor.get('name', 'Unknown')}",
                "input_data": {"factor_value": factor.get("value", 0)},
                "output_data": {"weighted_score": factor.get("weighted_score", 0)},
                "confidence": factor.get("confidence", 0.5),
                "evidence": factor.get("evidence", [])
            }
            self.add_reasoning_step(trace_id, step_data)
        
        # Add final scoring decision
        decision_data = {
            "decision_type": "scoring",
            "decision": f"Final score: {score_data.get('score', 0)}",
            "confidence": score_data.get("confidence", 0.7),
            "justification": score_data.get("justification", "Score calculated from weighted factors"),
            "alternatives_considered": score_data.get("alternative_scores", [])
        }
        self.add_decision(trace_id, decision_data)
        
        return {
            "scoring_explanation": self.get_trace(trace_id),
            "summary": self.generate_explanation_summary(trace_id)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get explainability statistics"""
        total_traces = len(self.traces)
        
        if total_traces == 0:
            return {
                "total_traces": 0,
                "statistics": {},
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Count by agent
        agent_counts = {}
        confidence_levels = []
        reasoning_step_counts = []
        
        for trace in self.traces.values():
            # Agent counts
            agent_counts[trace.agent_name] = agent_counts.get(trace.agent_name, 0) + 1
            
            # Confidence levels
            avg_confidence = trace._calculate_average_confidence()
            confidence_levels.append(avg_confidence)
            
            # Reasoning step counts
            reasoning_step_counts.append(len(trace.reasoning_steps))
        
        return {
            "total_traces": total_traces,
            "agent_breakdown": agent_counts,
            "average_confidence": sum(confidence_levels) / len(confidence_levels),
            "average_reasoning_steps": sum(reasoning_step_counts) / len(reasoning_step_counts),
            "completed_traces": len([t for t in self.traces.values() if t.completed_at]),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for explainability engine"""
        return {
            "engine": self.engine_name,
            "version": self.version,
            "status": "healthy",
            "total_traces": len(self.traces),
            "timestamp": datetime.utcnow().isoformat()
        }

# Global explainability engine instance
explainability_engine = ExplainabilityEngine()

def get_explainability_engine() -> ExplainabilityEngine:
    """Get global explainability engine instance"""
    return explainability_engine

# Convenience functions
def create_explanation_trace(agent_name: str, query: str, context: Dict[str, Any] = None) -> str:
    """Create new explanation trace"""
    return explainability_engine.create_trace(agent_name, query, context)

def add_reasoning_step(trace_id: str, reasoning_type: str, description: str, 
                      input_data: Dict[str, Any] = None, output_data: Dict[str, Any] = None,
                      confidence: float = 0.0, evidence: List[str] = None) -> bool:
    """Add reasoning step to trace"""
    step_data = {
        "reasoning_type": reasoning_type,
        "description": description,
        "input_data": input_data or {},
        "output_data": output_data or {},
        "confidence": confidence,
        "evidence": evidence or []
    }
    return explainability_engine.add_reasoning_step(trace_id, step_data)

def add_final_decision(trace_id: str, decision_type: str, decision: str,
                      confidence: float = 0.0, justification: str = "",
                      alternatives: List[Dict[str, Any]] = None,
                      risk_factors: List[str] = None) -> bool:
    """Add final decision to trace"""
    decision_data = {
        "decision_type": decision_type,
        "decision": decision,
        "confidence": confidence,
        "justification": justification,
        "alternatives_considered": alternatives or [],
        "risk_factors": risk_factors or []
    }
    return explainability_engine.add_decision(trace_id, decision_data)

def get_explanation(trace_id: str) -> Optional[Dict[str, Any]]:
    """Get complete explanation"""
    return explainability_engine.get_trace(trace_id)

def get_explanation_summary(trace_id: str) -> Optional[Dict[str, Any]]:
    """Get human-readable explanation summary"""
    return explainability_engine.generate_explanation_summary(trace_id)
