# PR Review Negotiation Environment — V2 Learnings

This document summarizes the critical challenges identified during V1 development and the specific architectural improvements implemented in V2 to satisfy the Hackathon's OpenEnv Benchmark requirements.

## 🏁 Critical Learnings & Problems Identified

### 1. The "Surface vs. Root" Problem
*   **The Problem**: Many AI agents provide generic feedback like "This code has a bug" or "Fix the syntax." In V1, these agents would pass simply by identifying the location of the error.
*   **V2 Fix**: We implemented a **Root-Cause Grader**. Agents now get penalized (-0.05) if they only describe the symptom and are only rewarded (+0.25) if they identify the underlying logic flaw or security vector.

### 2. The "Fake Fix" Deception
*   **The Problem**: In iterative negotiation, a developer (author) might push a cosmetic "fix" (e.g., adding `.strip()` to a SQL injection) that looks correct but leaves the vulnerability active.
*   **V2 Fix**: Added specific `false_fix_keywords` detection. V2 agents are now tested on their ability to resist "social engineering" from the author and persist with the review until a genuine parameterized fix is provided.

### 3. Escalate vs. Request Changes
*   **The Problem**: Critical security failures (like hardcoded JWT secrets) are often treated as normal "Request Changes" items, wasting precious time.
*   **V2 Fix**: Implemented **Escalation Logic**. V2 requires the agent to correctly identify High-Severity breaches and transition the decision to `escalate`, rewarding immediate reporting over standard iterative feedback.

### 4. State Persistence & UI Synchronization
*   **The Problem**: Frontend state inconsistently mapped to the backend's "done" flag, leading to "nothing visible" errors when reviews concluded.
*   **V2 Fix**: Moved to a **Stateless Component Architecture** driven entirely by the `PRObservation` returned from the API, ensuring the UI 1:1 reflects the environment's internal truth.

## 🏆 Hackathon Compliance Improvements
- **OpenEnv 0.2.1 Schema**: V2 uses strictly validated Pydantic models for every endpoint.
- **Root-Level `inference.py`**: Automated benchmarks can now locate and execute the agent's reasoning loop directly.
- **Docker SDK SDK for Hugging Face**: Containerized deployment on port 7860 with an Nginx reverse proxy for high availability.
