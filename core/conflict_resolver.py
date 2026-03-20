"""
Conflict Resolution Engine
=========================
Analyzes logical conflicts in code, writing, and workflows.

Use Cases:
- Programming errors detection
- Contradictory arguments in writing
- Workflow inefficiencies

Outputs:
- Problem identification
- Specific error locations
- Suggested corrections
"""
import re
import ast
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ConflictType(Enum):
    """Types of conflicts detected."""
    UNDEFINED_VARIABLE = "undefined_variable"
    TYPE_MISMATCH = "type_mismatch"
    SYNTAX_ERROR = "syntax_error"
    LOGIC_ERROR = "logic_error"
    CONTRADICTION = "contradiction"
    TAUTOLOGY = "tautology"
    INEFFICIENT_LOOP = "inefficient_loop"
    REDUNDANT_OPERATION = "redundant_operation"
    BLOCKING_WAIT = "blocking_wait"


class Severity(Enum):
    """Severity level."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Conflict:
    """Represents a detected conflict."""
    conflict_type: ConflictType
    severity: Severity
    title: str
    description: str
    line_number: Optional[int] = None
    suggestion: str = ""


class ConflictResolver:
    """
    Main conflict resolution engine.
    """
    
    def __init__(self):
        pass
    
    def analyze_code(self, code: str) -> List[Conflict]:
        """Analyze code for conflicts."""
        conflicts = []
        
        # Try Python AST analysis
        try:
            tree = ast.parse(code)
            conflicts.extend(self._analyze_ast(code, tree))
        except SyntaxError as e:
            conflicts.append(Conflict(
                conflict_type=ConflictType.SYNTAX_ERROR,
                severity=Severity.ERROR,
                title="Syntax Error",
                description=f"Syntax error at line {e.lineno}: {e.msg}",
                line_number=e.lineno,
                suggestion="Fix the syntax error to make the code valid.",
            ))
        
        # Pattern-based analysis
        conflicts.extend(self._analyze_patterns(code))
        
        return conflicts
    
    def _analyze_ast(self, code: str, tree: ast.AST) -> List[Conflict]:
        """Analyze Python AST."""
        conflicts = []
        defined_vars = set()
        used_vars = set()
        
        class VarCollector(ast.NodeVisitor):
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Load):
                    used_vars.add(node.id)
                elif isinstance(node.ctx, ast.Store):
                    defined_vars.add(node.id)
                self.generic_visit(node)
        
        collector = VarCollector()
        collector.visit(tree)
        
        # Find undefined variables
        undefined = used_vars - defined_vars
        builtins = {'True', 'False', 'None', 'print', 'len', 'range', 'int', 'str', 'list', 'dict'}
        for var in undefined:
            if var not in builtins:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.UNDEFINED_VARIABLE,
                    severity=Severity.ERROR,
                    title=f"Undefined Variable: {var}",
                    description=f"Variable '{var}' is used but never defined.",
                    suggestion=f"Define '{var}' before using it.",
                ))
        
        return conflicts
    
    def _analyze_patterns(self, code: str) -> List[Conflict]:
        """Pattern-based conflict detection."""
        conflicts = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Empty except
            if re.match(r'\s*except\s*:', line):
                conflicts.append(Conflict(
                    conflict_type=ConflictType.LOGIC_ERROR,
                    severity=Severity.WARNING,
                    title="Bare Except",
                    description=f"Line {i}: Empty except catches all exceptions.",
                    line_number=i,
                    suggestion="Specify exception type: except Exception as e:",
                ))
            
            # == None (should use 'is')
            if re.search(r'==\s*None', line):
                conflicts.append(Conflict(
                    conflict_type=ConflictType.LOGIC_ERROR,
                    severity=Severity.WARNING,
                    title="Equality with None",
                    description=f"Line {i}: Using '==' with None.",
                    line_number=i,
                    suggestion="Use 'is None' instead.",
                ))
            
            # Hardcoded password
            if re.search(r'password\s*=\s*["\']', line, re.IGNORECASE):
                conflicts.append(Conflict(
                    conflict_type=ConflictType.LOGIC_ERROR,
                    severity=Severity.CRITICAL,
                    title="Hardcoded Password",
                    description=f"Line {i}: Password appears hardcoded.",
                    line_number=i,
                    suggestion="Use environment variables for credentials.",
                ))
        
        # Nested loops
        nested_loops = re.findall(r'for\s+.*?:\s*\n\s*for\s+', code)
        if nested_loops:
            conflicts.append(Conflict(
                conflict_type=ConflictType.INEFFICIENT_LOOP,
                severity=Severity.WARNING,
                title="Nested Loop",
                description=f"Found {len(nested_loops)} nested loop(s).",
                suggestion="Consider using set operations for O(n) vs O(n²).",
            ))
        
        return conflicts
    
    def analyze_writing(self, text: str) -> List[Conflict]:
        """Analyze text for logical conflicts."""
        conflicts = []
        lines = text.split('\n')
        
        # Contradiction pairs
        contradiction_pairs = [
            (r'\bnever\b', r'\balways\b'),
            (r'\bimpossible\b', r'\bguaranteed\b'),
        ]
        
        for i, line in enumerate(lines, 1):
            for neg, pos in contradiction_pairs:
                if re.search(neg, line, re.IGNORECASE) and re.search(pos, line, re.IGNORECASE):
                    conflicts.append(Conflict(
                        conflict_type=ConflictType.CONTRADICTION,
                        severity=Severity.ERROR,
                        title="Contradiction",
                        description=f"Line {i}: Contains contradictory terms.",
                        line_number=i,
                        suggestion="Choose one position and remove contradiction.",
                    ))
        
        # Tautologies
        tautologies = [
            (r'\bfree gift\b', "Gifts are already free"),
            (r'\bpast history\b', "History is always past"),
        ]
        
        for pattern, desc in tautologies:
            if re.search(pattern, text, re.IGNORECASE):
                conflicts.append(Conflict(
                    conflict_type=ConflictType.TAUTOLOGY,
                    severity=Severity.WARNING,
                    title="Tautology",
                    description=desc,
                    suggestion="Remove redundant phrase.",
                ))
        
        return conflicts
    
    def analyze_workflow(self, workflow: str) -> List[Conflict]:
        """Analyze workflow for inefficiencies."""
        conflicts = []
        
        # Blocking waits
        if re.search(r'wait\s+\d+\s+seconds?', workflow, re.IGNORECASE):
            conflicts.append(Conflict(
                conflict_type=ConflictType.BLOCKING_WAIT,
                severity=Severity.WARNING,
                title="Blocking Wait",
                description="Found hardcoded wait.",
                suggestion="Use event-based triggers instead.",
            ))
        
        # Redundant operations
        operations = re.findall(r'(get|fetch|load|save)\s+\w+', workflow, re.IGNORECASE)
        seen = set()
        for op in operations:
            op_lower = op.lower()
            if op_lower in seen:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.REDUNDANT_OPERATION,
                    severity=Severity.WARNING,
                    title="Redundant Operation",
                    description=f"'{op}' may duplicate a previous operation.",
                    suggestion="Remove redundant operation.",
                ))
            seen.add(op_lower)
        
        return conflicts
    
    def analyze(self, content: str, content_type: str = "auto") -> Dict[str, Any]:
        """Full analysis."""
        if content_type == "auto":
            # Auto-detect
            if any(kw in content for kw in ['def ', 'class ', 'import ', 'print(']):
                content_type = "code"
            elif any(kw in content for kw in ['step ', 'process ', 'workflow']):
                content_type = "workflow"
            else:
                content_type = "writing"
        
        if content_type == "code":
            conflicts = self.analyze_code(content)
        elif content_type == "writing":
            conflicts = self.analyze_writing(content)
        else:
            conflicts = self.analyze_workflow(content)
        
        return {
            "total_conflicts": len(conflicts),
            "conflicts": [
                {
                    "type": c.conflict_type.value,
                    "severity": c.severity.value,
                    "title": c.title,
                    "description": c.description,
                    "line": c.line_number,
                    "suggestion": c.suggestion,
                }
                for c in conflicts
            ],
        }


def quick_check(content: str) -> str:
    """Quick conflict check."""
    resolver = ConflictResolver()
    result = analyzer.analyze(content)
    
    if result["total_conflicts"] == 0:
        return "No conflicts detected."
    
    lines = [f"Found {result['total_conflicts']} issue(s):"]
    for c in result["conflicts"][:5]:
        lines.append(f"• {c['title']}: {c['description']}")
    
    return "\n".join(lines)


# Export
analyzer = ConflictResolver()
__all__ = ["ConflictResolver", "ConflictType", "Severity", "Conflict", "quick_check"]
