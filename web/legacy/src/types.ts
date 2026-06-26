// ═══════════════════════════════════════════════════════════════════════
//  TYPE DEFINITIONS — Self-Evolving AI Math Tutor
// ═══════════════════════════════════════════════════════════════════════

export interface Problem {
    id: string;
    title: string;
    statement: string;   // human-readable prompt
    latex: string;       // formula/expression to render
    difficulty: string;  // "easy" | "medium" | "hard"
    topic: string;
}

export interface SocraticMessage {
    role: "tutor" | "user" | "system";
    content: string;
    type?: string;
}

export interface SocraticResponse {
    hint_level: number;
    messages: SocraticMessage[];
    can_reveal_more: boolean;
    topic: string;
    problem_type: string;
    latex: string;
    guardrail_active: boolean;
    verification_status: string;
}

export interface ProblemClassification {
    type: string;
    has_variable: boolean;
    variables: string[];
    is_equation: boolean;
    complexity: string;
    topic: string;
}

export interface PolicyStatus {
    checked: boolean;
    allowed: boolean;
    active_policies: number;
}

export interface BlendingContext {
    strategic_intent: {
        goal: string;
        method: string;
        constraint: string;
    };
    architectural_boundaries: {
        socratic_constraint_active: boolean;
        direct_answer_forbidden: boolean;
    };
}

export interface MathResponse {
    session_id: string;
    original: string;
    latex?: string;
    classification?: ProblemClassification;
    socratic?: SocraticResponse;
    blending_context?: BlendingContext;
    policy_status?: PolicyStatus;
    verification_status?: string;
    // Legacy
    solution?: string;
    result?: string;
    steps?: string[];
    type?: string;
}

export interface HintResponse {
    session_id: string;
    hint_level: number;
    socratic: SocraticResponse;
    verification_status: string;
}

export interface ArchitectureComponent {
    id: string;
    name: string;
    type: string;
    purpose: string;
    status: string;
}

export interface ArchitectureLayer {
    id: string;
    name: string;
    type: string;
    purpose: string;
    status: string;
    components: ArchitectureComponent[];
}

export interface ArchitectureAgent {
    id: string;
    name: string;
    role: string;
    function: string;
}

export interface ArchitectureTree {
    id: string;
    name: string;
    version: string;
    type: string;
    layers: ArchitectureLayer[];
    agents: ArchitectureAgent[];
}

export interface PolicyRule {
    name: string;
    description: string;
    penalty: number;
    type: string;
}

export interface PoliciesResponse {
    framework: string;
    policies: PolicyRule[];
    penalty_threshold: number;
    constraint: string;
}

export interface SessionData {
    id: string;
    created_at: string;
    conversation: Array<{
        role: string;
        content: string;
        hint_level: number | null;
        timestamp: string;
    }>;
    total_interactions: number;
    struggle_patterns: any[];
    successful_strategies: any[];
    socratic_compliance: number;
}
