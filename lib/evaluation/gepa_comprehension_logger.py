#!/usr/bin/env python
"""
Gulf of Comprehension Bridge for GEPA Evaluations
Based on Three Gulfs Framework by Hamel Husain & Shreya Shankar

Provides comprehensive logging and analysis of GEPA evaluation traces
to understand WHY evaluations succeed or fail
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

class GEPAComprehensionLogger:
    """
    Systematic logging for GEPA evaluations following Three Gulfs Framework
    
    Key Principle: "You cannot vibe-check your way to understanding what's going on"
    Solution: Deep systematic data analysis of every evaluation
    """
    
    def __init__(self, log_dir: str = "data/gepa_logs/comprehension"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create structured logging files
        self.trace_file = self.log_dir / f"traces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        self.error_taxonomy_file = self.log_dir / "error_taxonomy.json"
        self.summary_file = self.log_dir / "evaluation_summary.csv"
        
        # Error taxonomy following Three Gulfs pattern
        self.error_taxonomy = {
            "specification_failures": [],  # Vague prompts, unclear instructions
            "generalization_failures": [], # Model can't apply to diverse inputs
            "comprehension_gaps": [],      # We don't understand what's happening
            "json_errors": [],             # Structural failures
            "validation_errors": [],       # Missing/incorrect fields
            "backtest_failures": [],       # Strategy execution issues
            "performance_issues": []       # Poor metrics but valid strategy
        }
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def log_evaluation(self, 
                      iteration: int,
                      market_context: str,
                      prediction: Any,
                      score: float,
                      feedback: str,
                      backtest_results: Optional[Dict] = None,
                      error_type: Optional[str] = None):
        """
        Log complete evaluation trace for later analysis
        
        Args:
            iteration: GEPA iteration number
            market_context: The input prompt/context
            prediction: The model's output (strategy + reasoning)
            score: The evaluation score (0.0 to 1.0)
            feedback: The feedback message
            backtest_results: Optional backtest metrics
            error_type: Classification of error if failed
        """
        
        trace = {
            "timestamp": datetime.now().isoformat(),
            "iteration": iteration,
            "score": score,
            "feedback": feedback,
            "error_type": error_type,
            
            # Full context - don't lose information
            "input": {
                "market_context": market_context,
                "context_length": len(market_context)
            },
            
            # Complete output
            "output": {
                "strategy": str(prediction.strategy) if hasattr(prediction, 'strategy') else str(prediction),
                "reasoning": str(prediction.reasoning) if hasattr(prediction, 'reasoning') else None,
                "output_length": len(str(prediction))
            },
            
            # Performance metrics if available
            "metrics": backtest_results if backtest_results else {},
            
            # Failure analysis
            "failure_analysis": self._analyze_failure(score, feedback, error_type)
        }
        
        # Write to JSONL for easy streaming analysis
        with open(self.trace_file, 'a') as f:
            f.write(json.dumps(trace) + '\n')
        
        # Update error taxonomy
        if score < 0.5:  # Consider as failure
            self._update_taxonomy(error_type, trace)
            
    def _analyze_failure(self, score: float, feedback: str, error_type: str) -> Dict:
        """
        Detailed failure analysis following Three Gulfs principles
        """
        analysis = {
            "is_failure": score < 0.5,
            "severity": self._classify_severity(score),
            "gulf_classification": self._identify_gulf(feedback, error_type),
            "actionable_insight": self._extract_actionable_insight(feedback)
        }
        
        return analysis
    
    def _classify_severity(self, score: float) -> str:
        """Classify error severity based on score"""
        if score == 0.0:
            return "critical"  # Complete failure
        elif score < 0.1:
            return "high"      # Major issues
        elif score < 0.5:
            return "medium"    # Significant problems
        else:
            return "low"       # Minor issues
    
    def _identify_gulf(self, feedback: str, error_type: str) -> str:
        """
        Identify which gulf this failure belongs to
        
        Gulf of Comprehension: We don't understand the failure
        Gulf of Specification: Unclear instructions to model
        Gulf of Generalization: Model can't handle this input type
        """
        
        feedback_lower = feedback.lower()
        
        # Specification failures
        if any(word in feedback_lower for word in ['missing', 'required', 'format', 'invalid']):
            return "specification"
        
        # Generalization failures  
        elif any(word in feedback_lower for word in ['failed', 'error', 'exception', 'unable']):
            return "generalization"
        
        # Comprehension gaps
        elif 'unknown' in feedback_lower or not error_type:
            return "comprehension"
        
        return "unclassified"
    
    def _extract_actionable_insight(self, feedback: str) -> str:
        """Extract the most actionable part of feedback"""
        # Look for specific recommendations in feedback
        if "Consider" in feedback:
            return feedback.split("Consider")[1].split(".")[0]
        elif "Try" in feedback:
            return feedback.split("Try")[1].split(".")[0]
        elif "needs" in feedback.lower():
            return feedback.split("needs")[1].split(".")[0]
        else:
            # Return first actionable sentence
            return feedback.split(".")[0]
    
    def _update_taxonomy(self, error_type: str, trace: Dict):
        """Update error taxonomy with new failure pattern"""
        
        category = error_type if error_type else "unknown"
        
        if category not in self.error_taxonomy:
            self.error_taxonomy[category] = []
        
        # Store pattern for analysis
        pattern = {
            "iteration": trace["iteration"],
            "score": trace["score"],
            "input_snippet": trace["input"]["market_context"][:200],
            "failure_reason": trace["failure_analysis"]["actionable_insight"],
            "gulf": trace["failure_analysis"]["gulf_classification"]
        }
        
        self.error_taxonomy[category].append(pattern)
        
        # Save taxonomy periodically
        if len(self.error_taxonomy[category]) % 5 == 0:
            self.save_taxonomy()
    
    def save_taxonomy(self):
        """Save error taxonomy to file"""
        with open(self.error_taxonomy_file, 'w') as f:
            json.dump(self.error_taxonomy, f, indent=2)
    
    def generate_comprehension_report(self) -> Dict:
        """
        Generate comprehensive report following Three Gulfs analysis
        
        Returns insights about:
        1. Most common failure modes
        2. Gulf distribution
        3. Actionable improvements
        """
        
        # Load all traces
        traces = []
        with open(self.trace_file, 'r') as f:
            for line in f:
                traces.append(json.loads(line))
        
        if not traces:
            return {"error": "No traces found"}
        
        df = pd.DataFrame(traces)
        
        report = {
            "overview": {
                "total_evaluations": len(df),
                "failure_rate": (df['score'] < 0.5).mean(),
                "average_score": df['score'].mean(),
                "score_distribution": df['score'].describe().to_dict()
            },
            
            "gulf_analysis": {
                "specification_failures": 0,
                "generalization_failures": 0,
                "comprehension_gaps": 0
            },
            
            "failure_patterns": {},
            "top_actionable_insights": [],
            "recommendations": []
        }
        
        # Analyze by gulf
        for _, row in df.iterrows():
            if row['failure_analysis']['is_failure']:
                gulf = row['failure_analysis']['gulf_classification']
                report['gulf_analysis'][f"{gulf}_failures"] += 1
        
        # Extract top failure patterns
        failures = df[df['score'] < 0.5]
        if len(failures) > 0:
            # Group by error type
            error_counts = failures['error_type'].value_counts()
            report['failure_patterns'] = error_counts.to_dict()
            
            # Top actionable insights
            insights = failures['failure_analysis'].apply(lambda x: x.get('actionable_insight', ''))
            report['top_actionable_insights'] = insights.value_counts().head(5).to_dict()
        
        # Generate recommendations based on Three Gulfs
        report['recommendations'] = self._generate_recommendations(report)
        
        # Save report
        report_file = self.log_dir / f"comprehension_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        
        recommendations = []
        
        # Based on gulf distribution
        gulf_analysis = report['gulf_analysis']
        total_failures = sum(gulf_analysis.values())
        
        if total_failures > 0:
            # Specification issues
            if gulf_analysis['specification_failures'] / total_failures > 0.4:
                recommendations.append(
                    "HIGH PRIORITY: Specification Gulf detected - "
                    "Refine prompt templates with explicit JSON schemas and examples"
                )
            
            # Generalization issues
            if gulf_analysis['generalization_failures'] / total_failures > 0.4:
                recommendations.append(
                    "HIGH PRIORITY: Generalization Gulf detected - "
                    "Consider task decomposition or adding retrieval for edge cases"
                )
            
            # Comprehension issues
            if gulf_analysis['comprehension_gaps'] / total_failures > 0.4:
                recommendations.append(
                    "HIGH PRIORITY: Comprehension Gulf detected - "
                    "Need deeper analysis of failure patterns with domain experts"
                )
        
        # Based on failure rate
        if report['overview']['failure_rate'] > 0.3:
            recommendations.append(
                "Consider systematic prompt refinement - current failure rate is too high"
            )
        
        # Based on score distribution
        if report['overview']['average_score'] < 0.6:
            recommendations.append(
                "System performing poorly overall - review entire evaluation pipeline"
            )
        
        return recommendations
    
    def display_summary(self):
        """Display summary of evaluations in terminal"""
        report = self.generate_comprehension_report()
        
        print("\n" + "="*80)
        print("GEPA COMPREHENSION ANALYSIS (Three Gulfs Framework)")
        print("="*80)
        
        print(f"\nOVERVIEW:")
        print(f"  Total Evaluations: {report['overview']['total_evaluations']}")
        print(f"  Failure Rate: {report['overview']['failure_rate']:.1%}")
        print(f"  Average Score: {report['overview']['average_score']:.3f}")
        
        print(f"\nGULF ANALYSIS:")
        for gulf, count in report['gulf_analysis'].items():
            print(f"  {gulf}: {count}")
        
        print(f"\nTOP FAILURE PATTERNS:")
        for pattern, count in report.get('failure_patterns', {}).items():
            print(f"  {pattern}: {count}")
        
        print(f"\nRECOMMENDATIONS:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        
        print("\n" + "="*80)


# Usage example
if __name__ == "__main__":
    logger = GEPAComprehensionLogger()
    
    # Example logging
    logger.log_evaluation(
        iteration=1,
        market_context="High volatility market with 10% daily swings",
        prediction={"strategy": "{...}", "reasoning": "..."},
        score=0.05,
        feedback="JSON parsing failed: missing required fields",
        error_type="json_error"
    )
    
    # Generate report
    logger.display_summary()