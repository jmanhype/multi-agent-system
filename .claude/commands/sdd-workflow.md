---
description: Execute the complete Specification-Driven Development workflow from constitution to implementation
allowed-tools: Bash, Read, Write, Edit, MultiEdit
---

Execute the full SDD workflow for: $ARGUMENTS

**Workflow Steps:**

1. **Constitution Phase** (if not exists)
   - Run /constitution to establish foundational principles
   - Wait for user confirmation before proceeding

2. **Specification Phase**
   - Run /specify $ARGUMENTS to create feature specification
   - Generate spec.md with user stories, requirements, and acceptance criteria

3. **Clarification Phase**
   - Run /clarify to resolve ambiguities through targeted questions
   - Update spec.md with clarified requirements (max 5 questions)

4. **Planning Phase**
   - Run /plan to generate implementation design
   - Create research.md, data-model.md, contracts/, quickstart.md

5. **Task Generation Phase**
   - Run /tasks to create executable task breakdown
   - Generate dependency-ordered tasks with parallel execution markers

6. **Implementation Phase**
   - Run /implement to execute all tasks following TDD approach
   - Track progress and validate completion

**Gate Checks:**
- Constitution must exist before specification
- Clarifications must resolve before planning
- Plan artifacts must be complete before task generation
- All tasks must be defined before implementation

**Error Handling:**
- If any phase fails, halt workflow and report error
- Suggest corrective action before resuming
- Allow user to skip phases explicitly if needed

**Completion Report:**
- Branch name and feature ID
- Generated artifacts and file paths
- Test coverage and validation status
- Suggested next steps (review, testing, deployment)