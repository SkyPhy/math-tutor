export interface Step {
    description: string;
}

export interface MathResponse {
    original: string;
    latex: string;
    solution?: string;
    result?: string;
    steps: string[];
    type: string;
}

export interface CanvasStroke {
    x: number;
    y: number;
}
