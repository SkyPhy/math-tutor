This step-by-step design plan integrates the interactive drawing capabilities of **p5.js** with the symbolic reasoning of **SymPy** and the pedagogical intelligence of modern AI tutors like **Khanmigo**. The goal is to move from a child’s freehand drawing to a structured animation that reflects the "process of thinking."

### **Step 1: Foundational Monorepo and Tech Stack Setup**

To maintain type safety and seamless communication between the frontend and the AI brain, start with a **monorepo architecture** using **Turborepo** or **pnpm workspaces**.

* **Frontend**: React (for UI management) \+ **p5.js** (in Instance Mode) for the drawing canvas and animation engine.

* **Backend**: **FastAPI** (Python) to leverage math libraries like **SymPy** and handle LLM requests asynchronously.  
* **Data Bridge**: Use **Mathpix v3/strokes API** to convert digital ink into LaTeX. This is superior to image-based OCR because it captures the temporal order of strokes, which helps the AI understand the child's writing process.

### **Step 2: Build the "Magic" Drawing Interface**

Children need an interface that is immediate and reactive.

* **Stroke Management**: Implement a Stroke class in p5.js to capture $(x, y)$ coordinate pairs, pressure, and timestamps. Use a **Command Pattern** to build a robust "undo/redo" system, which is essential for learning by trial and error.  
* **Visual Style**: Use the **p5.animS** or **handanim** libraries to give the digital ink a "hand-drawn" aesthetic (hatching and scribbles). This reduces the "perfection anxiety" children often feel with rigid software.

* **UI Primitives**: Use **p5.touchgui** for large, easily tappable buttons and sliders, ensuring the interface is usable on tablets.

### **Step 3: Implement the Symbolic Logic Grounding**

To prevent the AI from "hallucinating" math facts, grounding in a deterministic engine is mandatory.

* **Symbolic Verification**: Send the LaTeX from Mathpix to your FastAPI backend. Use **SymPy** to parse the expression and check for algebraic equivalence.

* **Misconception Detection**: Use the **MalAlgoPy** framework to compare the student's solution path against a library of 2,586 known "malgorithms" (e.g., distribution errors like $a(b+c) \= ab+c$).

* **Knowledge Graph Profiling**: Build a **Math Knowledge Graph** where nodes are topics (e.g., "Adding Fractions") and edges are prerequisites. Overlay student performance on this graph using **Bayesian Knowledge Tracing (BKT)** to track their mastery levels.

### **Step 4: Design the Socratic AI "Brain"**

Configure the AI to act as a guide rather than an answer key, following the **Khanmigo model**.

* **Socratic Prompting**: Instruct the LLM (GPT-4o or Gemini 1.5 Pro) to "think behind the scenes" by writing out all possible ways a student might have arrived at their answer.  
* **Clue Generation**: Use **Chain-of-Thought (CoT)** prompts to generate hints. If the child makes a distribution error, the AI should not say "You forgot to multiply $c$," but rather ask, "What happens to everything inside the parentheses when we multiply by $a$?".  
* **Multimodal Context**: Generate **textual descriptions of all graphs and drawings** so the LLM can "see" what the child is drawing and provide contextually relevant advice.

### **Step 5: Generative Animation Pipeline**

This is the core differentiator: turning a drawing into an explanatory story.

* **Reasoning-to-Animation**: When a child is stuck, the AI generates a multi-step "thinking path." Use a **Stepwise Correction (StepCo)** pipeline to verify each reasoning step before animating it.

* **MObject Rendering**: Translate these steps into **p5.teach.js** commands. For example, if the logic is "subtract 5 from both sides," p5.teach.js creates a "Math Object" (MObject) of the number 5 and uses moveTo() to slide it across the equals sign while changing its color or sign.

* **Dynamic Graphing**: Use **Math.js** to evaluate functions in real-time and render a mathematically accurate graph on a separate p5.js layer, allowing the child to see their sketch "snap" into a precise visualization.

### **Step 6: Deployment and Compliance Safety**

Deployment must prioritize the privacy of minors.

* **Dockerization**: Package the FastAPI backend with all its heavy dependencies (SymPy, LaTeX, FFmpeg) into **Docker containers** for consistent deployment.

* **COPPA Compliance**: Implement **Verifiable Parental Consent** during onboarding. Ensure all student data is processed in-memory or de-identified before being sent to the LLM.  
* **Retention Policy**: Set an automated schedule to delete student work after one school year unless otherwise requested by a parent.

### **Phase-by-Phase Roadmap Summary**

| Phase | Duration | Objective | Key Tools |
| :---- | :---- | :---- | :---- |
| **Phase 1** | 2-3 Weeks | Basic p5.js drawing canvas with undo/redo. | p5.js, React, p5.animS |
| **Phase 2** | 3-4 Weeks | Integration with Mathpix and SymPy backend. | FastAPI, Mathpix API, SymPy |
| **Phase 3** | 4-5 Weeks | Socratic LLM agent with misconception modeling. | GPT-4o, MalAlgoPy, BKT |
| **Phase 4** | 3-4 Weeks | Generative animation from reasoning steps. | p5.teach.js, Anime.js |
| **Phase 5** | 2 Weeks | COPPA compliance and cloud deployment. | Docker, AWS/Vercel |

By following this sequence, the software evolves from a simple digital whiteboard into an **Intelligent Tutoring System (ITS)** that can truly see and understand how a child thinks about math.

