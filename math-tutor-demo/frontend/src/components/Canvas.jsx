import React, { useState } from 'react';
import Sketch from 'react-p5';

const CanvasComponents = ({ onAnalyze }) => {
    const [strokes, setStrokes] = useState([]);
    const [currentStroke, setCurrentStroke] = useState([]);
    const [isDrawing, setIsDrawing] = useState(false);

    const setup = (p5, canvasParentRef) => {
        p5.createCanvas(800, 600).parent(canvasParentRef);
        p5.background(255);
        p5.stroke(0);
        p5.strokeWeight(4);
        p5.noFill();
    };

    const draw = (p5) => {
        // If we wanted to animate the strokes being drawn or smooth them, we'd do it here.
        // For now, p5 handles immediate mode drawing in mouseDragged.

        // However, to implementing "undo", we might want to redraw everything from `strokes` state each frame
        // But for performance in this simple demo, we'll just draw on top.

        // Let's implement a redraw loop logic for better control:
        p5.background(255);

        // Draw all completed strokes
        p5.stroke(0);
        p5.strokeWeight(4);
        p5.noFill();

        for (let stroke of strokes) {
            p5.beginShape();
            for (let pt of stroke) {
                p5.vertex(pt.x, pt.y);
            }
            p5.endShape();
        }

        // Draw current stroke
        if (currentStroke.length > 0) {
            p5.stroke(50, 50, 200); // Blue tint for active stroke
            p5.beginShape();
            for (let pt of currentStroke) {
                p5.vertex(pt.x, pt.y);
            }
            p5.endShape();
        }
    };

    const mousePressed = (p5) => {
        // Check if mouse is inside canvas
        if (p5.mouseX > 0 && p5.mouseX < 800 && p5.mouseY > 0 && p5.mouseY < 600) {
            setIsDrawing(true);
            setCurrentStroke([{ x: p5.mouseX, y: p5.mouseY }]);
        }
    };

    const mouseDragged = (p5) => {
        if (isDrawing) {
            setCurrentStroke(prev => [...prev, { x: p5.mouseX, y: p5.mouseY }]);
        }
    };

    const mouseReleased = (p5) => {
        if (isDrawing) {
            setIsDrawing(false);
            setStrokes(prev => [...prev, currentStroke]);
            setCurrentStroke([]);
        }
    };

    const handleClear = () => {
        setStrokes([]);
        setCurrentStroke([]);
    };

    const handleUndo = () => {
        setStrokes(prev => prev.slice(0, -1));
    };

    return (
        <div className="canvas-wrapper">
            <div className="controls">
                <button onClick={handleUndo}>Undo</button>
                <button onClick={handleClear}>Clear</button>
            </div>
            <div className="sketch-container">
                <Sketch
                    setup={setup}
                    draw={draw}
                    mousePressed={mousePressed}
                    mouseDragged={mouseDragged}
                    mouseReleased={mouseReleased}
                />
            </div>
        </div>
    );
};

export default CanvasComponents;
